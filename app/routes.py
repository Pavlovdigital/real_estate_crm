from flask import render_template, redirect, url_for, flash, request, abort, current_app, Response, send_from_directory
from app import app, db, login_manager
from app.forms import LoginForm, RegistrationForm, PropertyForm, PropertyImportForm, PropertyFilterForm
from app.models import User, Role, Property, PropertyHistory, PropertyImage # Ensured PropertyImage is imported
from flask_login import login_user, logout_user, current_user, login_required
from datetime import datetime
from sqlalchemy import inspect 
import pandas as pd
import os
from werkzeug.utils import secure_filename
import pdfkit 
from urllib.parse import urlparse # For PropertyForm image handling
from uuid import uuid4 # For PropertyForm image handling

@app.route('/')
@app.route('/index')
def index():
    return render_template('index.html', title='Главная')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = RegistrationForm()
    if form.validate_on_submit():
        user_role = Role.query.filter_by(name='User').first()
        if not user_role:
            flash('Ошибка: Роль пользователя не найдена. Обратитесь к администратору.', 'danger')
            return redirect(url_for('register'))
            
        user = User(username=form.username.data, email=form.email.data, role_id=user_role.id)
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        login_user(user)
        flash('Вы успешно зарегистрированы и вошли в систему!', 'success') 
        return redirect(url_for('dashboard'))
    return render_template('register.html', title='Регистрация', form=form)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and user.check_password(form.password.data):
            login_user(user, remember=form.remember.data)
            next_page = request.args.get('next')
            flash('Вы успешно вошли в систему.', 'success')
            return redirect(next_page) if next_page else redirect(url_for('dashboard'))
        else:
            flash('Неверный адрес электронной почты или пароль.', 'danger')
    return render_template('login.html', title='Вход', form=form)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Вы успешно вышли из системы.', 'info')
    return redirect(url_for('index'))

@app.route('/profile')
@login_required
def profile():
    return render_template('profile.html', title='Профиль')

@app.route('/dashboard')
@login_required
def dashboard():
    from app.models import Client # Delayed import if needed
    stats = {
        'num_properties': Property.query.count(), 
        'num_clients': Client.query.count(), 
        'num_deals': 0 # Placeholder for Deal model
    }
    return render_template('dashboard.html', title='Панель управления', stats=stats)

# Property Routes
@app.route('/properties')
@login_required
def list_properties():
    properties = Property.query.order_by(Property.created_at.desc()).all()
    return render_template('properties/properties.html', properties=properties, title='Объекты недвижимости')

@app.route('/properties/add', methods=['GET', 'POST'])
@login_required
def add_property():
    form = PropertyForm()
    if form.validate_on_submit():
        new_property_args = {
            'name': form.name.data, 'address': form.address.data, 'cat': form.cat.data,
            'status': form.status.data, 'district': form.district.data, 'price': form.price.data,
            'layout': form.layout.data, 'floor': form.floor.data, 'total_floors': form.total_floors.data,
            'area': form.area.data, 'm': form.m.data, 's': form.s.data, 's_kh': form.s_kh.data,
            'blkn': form.blkn.data, 'p': form.p.data, 'condition': form.condition.data,
            'seller_phone': form.seller_phone.data, 'street': form.street.data, 'd_kv': form.d_kv.data,
            'year': form.year.data, 'description': form.description.data, 'source': form.source.data,
            'link': form.link.data, 'external_id': form.external_id.data,
            'added_by_user_id': current_user.id
        }
        new_property = Property(**new_property_args)
        db.session.add(new_property)
        db.session.flush() # Get ID for new_property

        if form.photos.data: # This is now a TextAreaField with comma-separated URLs
            image_urls = [url.strip() for url in form.photos.data.split(',') if url.strip()]
            for img_url in image_urls[:10]: # Limit number of images
                try:
                    img_response = requests.get(img_url, timeout=10)
                    img_response.raise_for_status()
                    new_image_record = PropertyImage(
                        property_id=new_property.id, 
                        image_data=img_response.content, 
                        mimetype=img_response.headers.get('Content-Type', 'application/octet-stream'),
                        filename=os.path.basename(urlparse(img_url).path) or f"image_{uuid4().hex[:6]}"
                    )
                    db.session.add(new_image_record)
                    app.logger.info(f"Downloaded and queued image from URL: {img_url} for property {new_property.id}")
                except Exception as e:
                    app.logger.error(f"Could not download/store image {img_url} for property {new_property.id}: {e}", exc_info=True)
                    flash(f"Не удалось загрузить изображение: {img_url}", "warning")
        try:
            db.session.commit()
            flash('Объект успешно добавлен!', 'success')
            return redirect(url_for('list_properties'))
        except Exception as e_commit:
            db.session.rollback()
            app.logger.error(f"Error adding property: {e_commit}", exc_info=True)
            flash(f"Ошибка добавления объекта: {str(e_commit)}", "danger")

    return render_template('properties/property_form.html', title='Добавить объект', form=form, legend='Новый объект недвижимости')


@app.route('/properties/<int:property_id>')
@login_required
def view_property(property_id):
    property_item = Property.query.get_or_404(property_id)
    # Images will be accessed via property_item.images in the template
    return render_template('properties/property_detail.html', property=property_item, title=property_item.name)

@app.route('/properties/<int:property_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_property(property_id):
    property_to_edit = Property.query.get_or_404(property_id)
    if property_to_edit.added_by_user_id != current_user.id and (not current_user.role or current_user.role.name != 'Admin'):
        flash('У вас нет разрешения на редактирование этого объекта.', 'danger')
        abort(403) 
        
    form = PropertyForm(obj=property_to_edit)
    
    # For pre-filling the 'photos' TextAreaField with existing image URLs (if they were stored as such)
    # Since we are storing binary, this field is for adding *new* external URLs to be downloaded.
    # Existing images will be listed separately or managed differently.
    # For this iteration, form.uploaded_images.data will handle new image uploads.
    # Existing images are listed in the template with delete checkboxes.
    # No need to prefill form.photos.data as it was a TextArea for URLs.
    # form.uploaded_images (MultipleFileField) cannot be pre-filled with existing files.
    if request.method == 'GET':
        pass # Existing images are passed via 'property' object to the template

    original_values = {}
    tracked_fields = ['name', 'address', 'cat', 'status', 'district', 'price', 'layout', 'floor', 'total_floors', 'area', 'm', 's', 's_kh', 'blkn', 'p', 'condition', 'seller_phone', 'street', 'd_kv', 'year', 'description', 'source', 'link', 'external_id']
    
    # Capture original values from the object instance
    if request.method == 'POST': # Re-fetch for POST to compare against DB state prior to this POST
        fresh_property_to_edit = Property.query.get(property_id)
        for field in tracked_fields:
            original_values[field] = getattr(fresh_property_to_edit, field)
    else: # For GET
        for field in tracked_fields:
            original_values[field] = getattr(property_to_edit, field)

    if form.validate_on_submit():
        # Update property fields
        for field_name in tracked_fields:
            old_value = original_values.get(field_name)
            new_value_from_form = form[field_name].data
            
            current_db_field_type = type(getattr(property_to_edit, field_name))
            if current_db_field_type == float and new_value_from_form is not None:
                try: new_value_from_form = float(new_value_from_form)
                except (ValueError, TypeError): pass # Keep as string if not float, comparison will show diff
            elif current_db_field_type == int and new_value_from_form is not None:
                try: new_value_from_form = int(float(new_value_from_form))
                except (ValueError, TypeError): pass

            old_value_comp = str(old_value) if old_value is not None else ""
            new_value_comp = str(new_value_from_form) if new_value_from_form is not None else ""

            if old_value_comp != new_value_comp:
                history_record = PropertyHistory(
                    property_id=property_to_edit.id, user_id=current_user.id,
                    field_name=field_name, old_value=str(old_value), new_value=str(new_value_from_form)
                )
                db.session.add(history_record)
                app.logger.info(f"History: PropID {property_to_edit.id}, UserID {current_user.id}, Field: {field_name}, Old: '{old_value}', New: '{new_value_from_form}'")
            
            setattr(property_to_edit, field_name, new_value_from_form)

        # Handle 'photos' field (TextArea with comma-separated URLs)
        if form.photos.data: # If new URLs are provided in the textarea
            # Clear existing images associated with the property
            for existing_image in property_to_edit.images:
                db.session.delete(existing_image)
            app.logger.info(f"Cleared existing images for property ID {property_to_edit.id} due to new photo URL submission.")
            
            image_urls = [url.strip() for url in form.photos.data.split(',') if url.strip()]
            for img_url in image_urls[:10]: # Limit number of new images
                try:
                    img_response = requests.get(img_url, timeout=10)
                    img_response.raise_for_status()
                    new_image_record = PropertyImage(
                        property_id=property_to_edit.id, 
                        image_data=img_response.content, 
                        mimetype=img_response.headers.get('Content-Type', 'application/octet-stream'),
                        filename=os.path.basename(urlparse(img_url).path) or f"image_{uuid4().hex[:6]}"
                    )
                    db.session.add(new_image_record)
                    app.logger.info(f"Downloaded and queued new image from URL: {img_url} for property {property_to_edit.id}")
                except Exception as e:
                    app.logger.error(f"Could not download/store image {img_url} for property {property_to_edit.id}: {e}", exc_info=True)
                    flash(f"Не удалось загрузить изображение: {img_url}", "warning")
        
        try:
            db.session.commit()
            flash('Объект успешно обновлен! История изменений записана.', 'success')
            return redirect(url_for('view_property', property_id=property_to_edit.id))
        except Exception as e:
            db.session.rollback()
            app.logger.error(f"Ошибка обновления объекта {property_to_edit.name}: {e}", exc_info=True)
            flash(f"Ошибка обновления объекта: {str(e)}", "danger")
        
    return render_template('properties/property_form.html', title="Редактировать объект", form=form, legend=f'Редактирование: {property_to_edit.name}', property=property_to_edit)

@app.route('/properties/<int:property_id>/delete', methods=['POST'])
@login_required
def delete_property(property_id):
    property_to_delete = Property.query.get_or_404(property_id)
    if property_to_delete.added_by_user_id != current_user.id and (not current_user.role or current_user.role.name != 'Admin'):
        flash('У вас нет разрешения на удаление этого объекта.', 'danger')
        abort(403)
    
    db.session.delete(property_to_delete) # PropertyImages and PropertyHistory will be cascade-deleted
    db.session.commit()
    flash('Объект успешно удален.', 'success')
    return redirect(url_for('list_properties'))

@app.route('/properties/<int:property_id>/history')
@login_required
def property_history(property_id):
    property_item = Property.query.get_or_404(property_id)
    history_records = property_item.history_entries.order_by(PropertyHistory.timestamp.desc()).all() 
    return render_template(
        'properties/property_history.html', 
        title=f"История: {property_item.name}", 
        property=property_item, 
        history_records=history_records
    )

# Route to serve uploaded property images from the instance folder (OBSOLETE if images are in DB)
# UPLOAD_FOLDER_NAME = 'property_images' 
# @app.route('/uploads/property_images/<path:filename>')
# @login_required 
# def uploaded_property_image(filename):
#     base_upload_dir = os.path.join(current_app.instance_path, 'uploads')
#     return send_from_directory(base_upload_dir, filename)

# NEW Route to serve images directly from DB (PropertyImage.image_data)
@app.route('/property_image/<int:image_id>')
def serve_property_image(image_id):
    # Import PropertyImage here to avoid circular dependency if models imports routes, though less likely with blueprints
    # from app.models import PropertyImage 
    
    image_record = PropertyImage.query.get_or_404(image_id)
    
    if not image_record.image_data:
        app.logger.warning(f"No image data found for PropertyImage ID: {image_id}")
        abort(404)

    response = Response(image_record.image_data, mimetype=image_record.mimetype or 'application/octet-stream')
    response.headers['Cache-Control'] = 'public, max-age=604800' # Cache for 7 days
    # response.headers['Content-Disposition'] = f'inline; filename="{image_record.filename or "image.jpg"}"'
    return response

@app.route('/properties/filter', methods=['GET'])
@login_required
def filter_properties():
    form = PropertyFilterForm(request.args, meta={'csrf': False}) 

    distinct_districts = db.session.query(Property.district).distinct().filter(Property.district.isnot(None)).filter(Property.district != '').order_by(Property.district).all()
    form.district.choices = [('', 'Любой район')] + [(d[0], d[0]) for d in distinct_districts]
    distinct_conditions = db.session.query(Property.condition).distinct().filter(Property.condition.isnot(None)).filter(Property.condition != '').order_by(Property.condition).all()
    form.condition.choices = [('', 'Любое состояние')] + [(c[0], c[0]) for c in distinct_conditions]
    distinct_layouts = db.session.query(Property.layout).distinct().filter(Property.layout.isnot(None)).filter(Property.layout != '').order_by(Property.layout).all()
    form.layout.choices = [('', 'Любая планировка')] + [(l[0], l[0]) for l in distinct_layouts]
    distinct_cats = db.session.query(Property.cat).distinct().filter(Property.cat.isnot(None)).filter(Property.cat != '').order_by(Property.cat).all()
    form.cat.choices = [('', 'Любая категория')] + [(c[0], c[0]) for c in distinct_cats]
    distinct_statuses = db.session.query(Property.status).distinct().filter(Property.status.isnot(None)).filter(Property.status != '').order_by(Property.status).all()
    form.status.choices = [('', 'Любой статус')] + [(s[0], s[0]) for s in distinct_statuses]

    query = Property.query
    if form.min_price.data is not None: query = query.filter(Property.price >= form.min_price.data)
    if form.max_price.data is not None: query = query.filter(Property.price <= form.max_price.data)
    if form.district.data: query = query.filter(Property.district == form.district.data)
    if form.min_area.data is not None: query = query.filter(Property.area >= form.min_area.data)
    if form.max_area.data is not None: query = query.filter(Property.area <= form.max_area.data)
    if form.min_floor.data is not None: query = query.filter(Property.floor >= form.min_floor.data)
    if form.max_floor.data is not None: query = query.filter(Property.floor <= form.max_floor.data)
    if form.year_from.data: query = query.filter(Property.year >= form.year_from.data) 
    if form.year_to.data: query = query.filter(Property.year <= form.year_to.data)
    if form.condition.data: query = query.filter(Property.condition == form.condition.data)
    if form.layout.data: query = query.filter(Property.layout == form.layout.data)
    if form.cat.data: query = query.filter(Property.cat == form.cat.data)
    if form.status.data: query = query.filter(Property.status == form.status.data)
    if form.total_floors_min.data is not None: query = query.filter(Property.total_floors >= form.total_floors_min.data)
    if form.total_floors_max.data is not None: query = query.filter(Property.total_floors <= form.total_floors_max.data)

    filtered_properties = query.order_by(Property.created_at.desc()).all() 
    if request.args and not filtered_properties: flash('По вашему запросу объекты не найдены.', 'info')
    
    return render_template('properties/filter_properties.html', 
                           title="Фильтр объектов", form=form, properties=filtered_properties)

@app.route('/properties/export/pdf')
@login_required
def export_properties_pdf():
    try:
        properties = Property.query.order_by(Property.created_at.desc()).all()
        if not properties:
            flash("Нет объектов для экспорта в PDF.", "warning")
            return redirect(url_for('list_properties'))
        html_out = render_template('properties/pdf_export_template.html', properties=properties)
        options = { 'encoding': "UTF-8", 'margin-top': '0.75in', 'margin-right': '0.75in', 'margin-bottom': '0.75in', 'margin-left': '0.75in', 'no-outline': None, 'disable-smart-shrinking': ''}
        pdf_data = pdfkit.from_string(html_out, False, options=options)
        response = Response(pdf_data, mimetype='application/pdf')
        response.headers['Content-Disposition'] = 'attachment; filename=crm_properties_export.pdf'
        app.logger.info(f"User {current_user.username} exported properties to PDF.")
        return response
    except FileNotFoundError as e:
        app.logger.error(f"wkhtmltopdf not found. PDF export failed. Error: {e}", exc_info=True)
        flash("Ошибка экспорта PDF: Утилита wkhtmltopdf не найдена на сервере. Обратитесь к администратору.", "danger")
        return redirect(url_for('list_properties'))
    except Exception as e:
        app.logger.error(f"Ошибка при экспорте свойств в PDF: {e}", exc_info=True)
        flash(f"Произошла ошибка при генерации PDF: {str(e)}", "danger")
        return redirect(url_for('list_properties'))

from sqlalchemy import or_, func
from urllib.parse import urlparse
from uuid import uuid4
import requests # Added for Excel import image fetching, though might be already imported
import mimetypes # Added for Excel import image fetching
from werkzeug.utils import secure_filename # Added for Excel import image filename

TEMP_EXCEL_UPLOAD_FOLDER = 'uploads/temp_excel'

@app.route('/search') 
@login_required
def global_search_results():
    search_query = request.args.get('query', '').strip()
    property_results = []
    client_results = []
    if not search_query:
        flash("Пожалуйста, введите поисковый запрос.", "info")
    else:
        search_term = f"%{search_query.lower()}%"
        property_results = Property.query.filter(
            or_(
                func.lower(Property.name).like(search_term), func.lower(Property.address).like(search_term),
                func.lower(Property.district).like(search_term), func.lower(Property.description).like(search_term),
                func.lower(Property.street).like(search_term), func.lower(Property.cat).like(search_term),
                func.lower(Property.status).like(search_term) 
            )
        ).limit(20).all()
        client_results = Client.query.filter(
            or_(
                func.lower(Client.name).like(search_term), func.lower(Client.email).like(search_term),
                func.lower(Client.phone).like(search_term), func.lower(Client.notes).like(search_term)
            )
        ).limit(20).all()
        if not property_results and not client_results:
            flash("По вашему запросу ничего не найдено.", "info")
    return render_template('main/global_search_results.html', 
                           title=f"Результаты поиска: {search_query}", search_query=search_query,
                           property_results=property_results, client_results=client_results)

@app.route('/properties/import', methods=['GET', 'POST'])
@login_required
def import_properties():
    form = PropertyImportForm()
    if form.validate_on_submit():
        excel_file = form.excel_file.data
        filename = secure_filename(excel_file.filename)
        instance_path = current_app.instance_path
        temp_dir = os.path.join(instance_path, TEMP_EXCEL_UPLOAD_FOLDER)
        if not os.path.exists(temp_dir): os.makedirs(temp_dir)
        temp_file_path = os.path.join(temp_dir, filename)
        excel_file.save(temp_file_path)

        try:
            df = pd.read_excel(temp_file_path)
            added_count = 0; error_count = 0; skipped_count = 0
            col_map = {key.replace('_col',''): getattr(form, key).data for key in dir(form) if key.endswith('_col')}

            required_db_fields = ['name', 'price', 'area'] 
            missing_cols = [col_map[field] for field in required_db_fields if col_map[field] not in df.columns]
            if missing_cols:
                flash(f"Ошибка: Обязательные столбцы не найдены в Excel: {', '.join(missing_cols)}.", "danger")
                if os.path.exists(temp_file_path): os.remove(temp_file_path)
                return render_template('properties/import_form.html', title="Импорт объектов", form=form)

            for index, row in df.iterrows():
                try:
                    prop_data = {}
                    for model_field, excel_col_name in col_map.items():
                        if excel_col_name in df.columns and pd.notna(row[excel_col_name]):
                            prop_data[model_field] = row[excel_col_name]
                        else:
                            prop_data[model_field] = None 
                    
                    if not prop_data.get('name') or prop_data.get('price') is None or prop_data.get('area') is None:
                        app.logger.warning(f"Пропуск строки {index+2} Excel: отсутствуют Название, Цена или Площадь.")
                        skipped_count += 1
                        continue
                    
                    try: prop_data['price'] = float(prop_data['price']) if prop_data.get('price') is not None else None
                    except (ValueError, TypeError): prop_data['price'] = None; app.logger.warning(f"Строка {index+2}: Некорректная цена {row.get(col_map['price'])}")
                    
                    try: prop_data['area'] = float(prop_data['area']) if prop_data.get('area') is not None else None
                    except (ValueError, TypeError): prop_data['area'] = None; app.logger.warning(f"Строка {index+2}: Некорректная площадь {row.get(col_map['area'])}")

                    if prop_data.get('price') is None or prop_data.get('area') is None:
                        app.logger.warning(f"Пропуск строки {index+2} Excel: Цена или Площадь некорректны после конвертации.")
                        skipped_count += 1
                        continue

                    for int_field in ['floor', 'total_floors']: 
                        if prop_data.get(int_field) is not None:
                            try: prop_data[int_field] = int(float(prop_data[int_field]))
                            except (ValueError, TypeError): prop_data[int_field] = None; app.logger.warning(f"Строка {index+2}: Некорректное значение для {int_field}: {row.get(col_map.get(int_field))}")
                    
                    new_property_args = {k: v for k, v in prop_data.items() if hasattr(Property, k) and k not in ['photos', 'link', 'external_id', 'source']} 
                    new_property_args.update({
                        'added_by_user_id': current_user.id,
                        'source': prop_data.get('source') or "Excel Import", 
                        'link': prop_data.get('link'),
                        'external_id': str(prop_data.get('external_id')) if prop_data.get('external_id') else None
                    })
                    
                    new_prop_instance = Property(**new_property_args)
                    db.session.add(new_prop_instance)
                    # It's good to flush here if new_prop_instance.id is needed immediately, 
                    # but for appending to .images, it's not strictly necessary until commit.
                    # However, keeping it doesn't hurt and ensures ID is available if other logic needed it.
                    db.session.flush() 

                    if prop_data.get('photos') and isinstance(prop_data.get('photos'), str):
                        image_urls = [url.strip() for url in prop_data.get('photos').split(',') if url.strip()]
                        for img_url in image_urls[:10]: # Limit to 10 images
                            try:
                                response = requests.get(img_url.strip(), timeout=15) # Increased timeout slightly
                                response.raise_for_status()
                                image_binary_content = response.content
                                
                                parsed_url = urlparse(img_url.strip())
                                original_filename = os.path.basename(parsed_url.path)
                                # Use secure_filename and provide a better fallback name
                                filename = secure_filename(original_filename) if original_filename else f"image_{uuid4().hex[:8]}.jpg" 
                                if not os.path.splitext(filename)[1]: # ensure extension if secure_filename removed it or was not present
                                    filename += ".jpg" # default to jpg if no extension

                                server_mimetype = response.headers.get('Content-Type')
                                mimetype, _ = guess_type(filename) # Guess from filename first
                                if server_mimetype and server_mimetype != 'application/octet-stream':
                                    mimetype = server_mimetype # Prefer server's specific mimetype if available and not generic
                                
                                if not mimetype: # If still no mimetype, try to guess from URL or default
                                    mimetype, _ = guess_type(img_url.strip())
                                    if not mimetype:
                                        mimetype = 'application/octet-stream' # Ultimate fallback

                                if image_binary_content and mimetype and 'image' in mimetype.lower():
                                    new_db_image = PropertyImage(
                                        image_data=image_binary_content,
                                        filename=filename,
                                        mimetype=mimetype
                                    )
                                    new_prop_instance.images.append(new_db_image)
                                    # db.session.add(new_db_image) # Not strictly needed if appended to collection that is part of session
                                    app.logger.info(f"Строка {index+2}: Успешно обработано изображение с URL: {img_url} для объекта {new_prop_instance.name or 'ID ' + str(new_prop_instance.id)}")
                                else:
                                    app.logger.warning(f"Строка {index+2}: Не удалось обработать изображение с URL (неверные данные или mimetype): {img_url} для объекта {new_prop_instance.name or 'ID ' + str(new_prop_instance.id)}. Mimetype: {mimetype}")
                            
                            except requests.exceptions.RequestException as e_req:
                                app.logger.error(f"Строка {index+2}: Не удалось загрузить изображение с URL: {img_url} для объекта {new_prop_instance.name or 'ID ' + str(new_prop_instance.id)}. Ошибка сети: {e_req}")
                            except Exception as e_img_proc:
                                app.logger.error(f"Строка {index+2}: Неожиданная ошибка при обработке изображения {img_url} для {new_prop_instance.name or 'ID ' + str(new_prop_instance.id)}: {e_img_proc}", exc_info=True)
                    
                    added_count += 1
                except Exception as e_row:
                    error_count += 1
                    app.logger.error(f"Ошибка обработки строки {index+2} из Excel: {e_row}", exc_info=True)
                    db.session.rollback() 

            if error_count > 0:
                flash(f"Импорт завершен с {error_count} ошибками при обработке строк. {added_count} объектов успешно добавлено, {skipped_count} пропущено.", "warning")
            else:
                flash(f"Импорт успешно завершен. Добавлено объектов: {added_count}. Пропущено строк: {skipped_count}.", "success")
            
            db.session.commit()
        except Exception as e_file:
            db.session.rollback()
            app.logger.error(f"Ошибка при импорте файла Excel: {e_file}", exc_info=True)
            flash(f"Произошла ошибка при обработке файла: {str(e_file)}", "danger")
        finally:
            if os.path.exists(temp_file_path):
                try: os.remove(temp_file_path)
                except Exception as e_rm: app.logger.error(f"Не удалось удалить временный файл {temp_file_path}: {e_rm}")
                    
        return redirect(url_for('list_properties'))

    return render_template('properties/import_form.html', title="Импорт объектов из Excel", form=form)
