import logging
import os
import re
import requests # Still needed if scrapers pass URLs for service to download (but they should pass binary now)
import json
from datetime import datetime
from urllib.parse import urlparse # For filename extraction if needed
from uuid import uuid4 # For filename generation if needed
import time 

from sqlalchemy.exc import SQLAlchemyError
from app import db
from app.models import Property, User, Role, PropertyImage # PropertyImage is key

# Scraper imports
from app.scrapers.olx_scraper import scrape_olx
from app.scrapers.krisha_scraper import scrape_krisha

logger = logging.getLogger(__name__)
# Basic logging config should be in app/__init__.py

# IMAGE_UPLOAD_SUBDIR is no longer needed if storing binary in DB
# IMAGE_UPLOAD_SUBDIR = 'uploads/property_images' 

# def _ensure_upload_dir(app_instance_path): ... (No longer needed for DB storage)
# def _download_image(...): ... (Scrapers will provide binary data directly)

def _clean_phone_number(phone_str):
    if not phone_str: return None
    cleaned = re.sub(r'\D', '', str(phone_str))
    if len(cleaned) == 11 and (cleaned.startswith('87') or cleaned.startswith('77')): return f"+7{cleaned[1:]}"
    if len(cleaned) == 10 and cleaned.startswith('7'): return f"+7{cleaned}"
    if cleaned.startswith('7') and len(cleaned) > 10: return f"+{cleaned}"
    if cleaned.isdigit(): return cleaned
    logger.warning(f"Не удалось нормализовать телефон: {phone_str}, используется как есть: {cleaned[:20]}")
    return cleaned[:20]

def process_scraped_data(scraped_properties, source_site_name, app_instance_path, update_callback=None):
    # app_instance_path might not be needed if not saving files locally anymore
    if not scraped_properties:
        logger.info("Нет данных для обработки.")
        if update_callback: update_callback({"log_message": "Нет данных для обработки.", "progress_percent": 100})
        return {"added": 0, "updated": 0, "errors": 0, "skipped": 0}

    default_admin_user = None
    try:
        default_admin_user = User.query.join(Role).filter(Role.name == 'Admin').first()
    except SQLAlchemyError as e:
        logger.error(f"Ошибка БД при поиске Admin пользователя: {e}", exc_info=True)
        if update_callback: update_callback({"log_message": f"[ОШИБКА БД] Не удалось найти Admin пользователя: {e}", "error_occurred": True})
        
    default_user_id = default_admin_user.id if default_admin_user else None
    if not default_user_id and update_callback:
        update_callback({"log_message": "[ПРЕДУПРЕЖДЕНИЕ] Admin пользователь не найден. Новые объявления будут без ID пользователя."})

    counts = {"added": 0, "updated": 0, "errors": 0, "skipped": 0}
    total_items = len(scraped_properties)

    property_fields_from_schema = [ # Fields expected from scraper, matching new Property model
        'name', 'address', 'cat', 'status', 'district', 'price', 'layout', # 'layout' kept from PropertyForm
        'floor', 'total_floors', 'area', 'm', 's', 's_kh', 'blkn', 'p', 
        'condition', 'seller_phone', 'street', 'd_kv', 'year', 
        'description', 'source', 'link', 'external_id'
    ]

    for i, prop_data in enumerate(scraped_properties):
        progress = 50 + int(((i + 1) / total_items) * 50) 
        item_name_short = str(prop_data.get('name', 'N/A'))[:30]
        item_id_short = str(prop_data.get('external_id', 'N/A'))

        if update_callback:
            update_callback({
                "current_task": f"Обработка {i+1}/{total_items}: {item_name_short}...",
                "progress_percent": progress,
                "log_message": f"Обработка данных для {source_site_name} ID: {item_id_short}"
            })

        if not prop_data.get('external_id') or not prop_data.get('link'):
            log_msg = f"Пропущено (нет external_id/link): {item_name_short}"
            logger.warning(log_msg)
            if update_callback: update_callback({"log_message": f"[ПРЕДУПРЕЖДЕНИЕ] {log_msg}"})
            counts["skipped"] += 1
            continue
        
        if not prop_data.get('name'): # Name is NOT NULL in Property model
            log_msg = f"Пропущено ID {item_id_short} ({source_site_name}): отсутствует обязательное поле 'name'."
            logger.warning(log_msg)
            if update_callback: update_callback({"log_message": f"[ПРЕДУПРЕЖДЕНИЕ] {log_msg}"})
            counts["skipped"] +=1
            continue
            
        try:
            existing_property = Property.query.filter_by(
                external_id=str(prop_data['external_id']),
                source=prop_data.get('source') 
            ).first()
            
            cleaned_phone = _clean_phone_number(prop_data.get('seller_phone'))
            
            attributes_to_update = {}
            for field in property_fields_from_schema:
                if field in prop_data:
                    attributes_to_update[field] = prop_data[field]
            
            # Type conversions for numeric fields
            for field in ['price', 'area']:
                if attributes_to_update.get(field) is not None:
                    try: attributes_to_update[field] = float(attributes_to_update[field])
                    except (ValueError, TypeError): attributes_to_update[field] = None
            
            for field in ['floor', 'total_floors']: # Year is string
                 if attributes_to_update.get(field) is not None:
                    try: attributes_to_update[field] = int(float(attributes_to_update[field]))
                    except (ValueError, TypeError): attributes_to_update[field] = None

            if existing_property:
                updated_fields_log = []
                for field, value in attributes_to_update.items():
                    if getattr(existing_property, field) != value:
                        setattr(existing_property, field, value)
                        updated_fields_log.append(field)
                
                if cleaned_phone and existing_property.seller_phone != cleaned_phone:
                    existing_property.seller_phone = cleaned_phone
                    updated_fields_log.append('seller_phone')

                existing_property.last_scraped_at = datetime.utcnow()
                
                # Image processing: delete old, add new from binary data
                if 'scraped_images_data' in prop_data and prop_data['scraped_images_data']:
                    for old_image in existing_property.images: db.session.delete(old_image) # Cascade handled by DB? No, do it manually.
                    if update_callback and existing_property.images.count() > 0: update_callback({"log_message": f"Удалены старые фото для ID {item_id_short}."})
                    
                    for image_dict in prop_data['scraped_images_data'][:10]: # Limit images
                        new_db_image = PropertyImage(
                            image_data=image_dict['data'],
                            filename=image_dict['filename'],
                            mimetype=image_dict['mimetype']
                        )
                        existing_property.images.append(new_db_image)
                    if update_callback: update_callback({"log_message": f"Добавлены/обновлены фото ({len(prop_data['scraped_images_data'])}) для ID {item_id_short}."})
                    if 'images' not in updated_fields_log: updated_fields_log.append('images')
                
                db.session.add(existing_property)
                counts["updated"] += 1
                log_msg = f"Обновлено: {existing_property.name} (ID {existing_property.id}). Поля: {', '.join(updated_fields_log) if updated_fields_log else 'нет изменений'}."
            else:
                new_property = Property(**attributes_to_update)
                new_property.seller_phone = cleaned_phone
                new_property.added_by_user_id = default_user_id
                new_property.last_scraped_at = datetime.utcnow() # Set for new records too
                
                if 'scraped_images_data' in prop_data and prop_data['scraped_images_data']:
                    for image_dict in prop_data['scraped_images_data'][:10]:
                        new_db_image = PropertyImage(
                            image_data=image_dict['data'],
                            filename=image_dict['filename'],
                            mimetype=image_dict['mimetype']
                        )
                        new_property.images.append(new_db_image)
                
                db.session.add(new_property)
                counts["added"] += 1
                log_msg = f"Добавлено новое: {new_property.name} (Ext. ID: {new_property.external_id})"
            
            logger.info(log_msg)
            if update_callback: update_callback({"log_message": log_msg})

        except SQLAlchemyError as e_db:
            counts["errors"] += 1
            log_msg = f"Ошибка БД при обработке {item_id_short}: {e_db}"
            logger.error(log_msg, exc_info=True)
            if update_callback: update_callback({"log_message": f"[ОШИБКА БД] {log_msg}", "error_occurred": True, "error_detail": str(e_db)})
            db.session.rollback()
        except Exception as e_item:
            counts["errors"] += 1
            log_msg = f"Неожиданная ошибка при обработке {item_id_short}: {e_item}"
            logger.error(log_msg, exc_info=True)
            if update_callback: update_callback({"log_message": f"[ОШИБКА] {log_msg}", "error_occurred": True, "error_detail": str(e_item)})
            db.session.rollback()
    
    try:
        db.session.commit()
        logger.info("Все успешные изменения сохранены в БД.")
        if update_callback: update_callback({"log_message": "Все успешные изменения сохранены в БД."})
    except SQLAlchemyError as e_commit:
        db.session.rollback()
        logger.error(f"Критическая ошибка при сохранении сессии в БД: {e_commit}", exc_info=True) 
        if update_callback: 
            update_callback({
                "log_message": f"[КРИТИЧЕСКАЯ ОШИБКА] Не удалось сохранить изменения в БД: {e_commit}. Все изменения этого пакета отменены.", 
                "error": f"Критическая ошибка БД: {str(e_commit)}", "complete": True 
            })
        counts["errors"] = total_items; counts["added"] = 0; counts["updated"] = 0
    except Exception as e_final_commit:
        db.session.rollback()
        logger.error(f"Неожиданная критическая ошибка при сохранении сессии в БД: {e_final_commit}", exc_info=True)
        if update_callback:
            update_callback({
                "log_message": f"[КРИТИЧЕСКАЯ ОШИБКА] Неизвестная ошибка сохранения в БД: {e_final_commit}. Все изменения этого пакета отменены.",
                "error": f"Неизвестная критическая ошибка БД: {str(e_final_commit)}", "complete": True
            })
        counts["errors"] = total_items; counts["added"] = 0; counts["updated"] = 0
    return counts

def run_parsing_task(flask_app, source_name, num_pages, base_url):
    with flask_app.app_context():
        from flask import session 

        def update_callback_for_session(status_update_dict):
            if 'parser_status' not in session or not isinstance(session.get('parser_status'), dict):
                session['parser_status'] = {"progress_percent": 0, "current_task": "Инициализация...", "log": [], "complete": False, "summary": None, "error": None}
            current_status = session['parser_status'].copy()
            if "log_message" in status_update_dict:
                log_entry = f"{datetime.now().strftime('%H:%M:%S')}: {status_update_dict['log_message']}"
                if status_update_dict.get("error_occurred"): log_entry = f"[ERROR] {log_entry}"
                current_status["log"] = current_status.get("log", []) + [log_entry]
                current_status["log"] = current_status["log"][-100:] 
            current_status.update({k: v for k, v in status_update_dict.items() if k != "log_message"})
            session['parser_status'] = current_status
            session.modified = True

        initial_status = {"progress_percent": 0, "current_task": f"Запуск парсера для {source_name}...", "log": [f"{datetime.now().strftime('%H:%M:%S')}: Парсинг {source_name} инициирован."], "complete": False, "summary": None, "error": None}
        session['parser_status'] = initial_status
        session.modified = True
        logger.info(f"Парсинг {source_name} запущен в фоновом потоке.")

        scraped_items = None; task_summary = None
        try:
            scraper_func = None
            if source_name == "OLX.kz": scraper_func = scrape_olx
            elif source_name == "Krisha.kz": scraper_func = scrape_krisha
            else: raise ValueError(f"Неизвестный источник: {source_name}")

            update_callback_for_session({"current_task": f"Сбор данных с {source_name}...", "progress_percent": 5, "log_message": f"Начало сбора данных с {source_name}."})
            scraped_items = scraper_func(base_url, num_pages, update_callback=update_callback_for_session)

            if scraped_items is None: raise Exception(f"Scraper for {source_name} вернул None. Проверьте логи парсера.")

            update_callback_for_session({"current_task": f"Обработка {len(scraped_items)} объявлений с {source_name}...", "progress_percent": 50, "log_message": f"Собрано {len(scraped_items)} объявлений. Начало обработки."})
            # Pass app_instance_path, although it's not used if images are binary
            task_summary = process_scraped_data(scraped_items, source_name, flask_app.instance_path, update_callback=update_callback_for_session)
            
            final_log_message = f"Завершено. Добавлено: {task_summary.get('added',0)}, Обновлено: {task_summary.get('updated',0)}, Ошибок: {task_summary.get('errors',0)}, Пропущено: {task_summary.get('skipped',0)}."
            final_status_update = {"complete": True, "summary": task_summary, "progress_percent": 100, "current_task": f"Парсинг {source_name} завершен.", "log_message": final_log_message}
            if task_summary.get("errors", 0) > 0 : final_status_update["error"] = f"Завершено с {task_summary.get('errors')} ошибками при обработке данных."

        except Exception as e:
            logger.error(f"Критическая ошибка в задаче парсинга для {source_name}: {e}", exc_info=True)
            final_status_update = {"complete": True, "error": f"Критическая ошибка: {str(e)}", "progress_percent": 100, "current_task": f"Критическая ошибка при парсинге {source_name}.", "log_message": f"Критическая ошибка: {str(e)}", "summary": task_summary if task_summary else {"added": 0, "updated": 0, "errors": "N/A", "skipped": "N/A"}}
        
        update_callback_for_session(final_status_update)
        logger.info(f"Парсинг {source_name} завершен. Итоговый статус: {session.get('parser_status')}")
        pass
