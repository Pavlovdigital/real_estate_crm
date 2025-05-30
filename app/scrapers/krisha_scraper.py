import requests
from bs4 import BeautifulSoup
import time
import logging
import re # For cleaning text, extracting numbers
import json # For parsing JSON-like data if found
from datetime import datetime # Import datetime

# Configure logging (could share with OLX or have its own)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- Selenium setup (optional, only if needed for phone numbers on Krisha) ---
USE_SELENIUM_FOR_KRISHA_PHONES = True # Set to False if direct scraping works or to skip
SELENIUM_DRIVER_KRISHA = None

if USE_SELENIUM_FOR_KRISHA_PHONES:
    try:
        from selenium import webdriver
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        from selenium.webdriver.chrome.service import Service as ChromeService
        from webdriver_manager.chrome import ChromeDriverManager
        from selenium.webdriver.chrome.options import Options
        
        chrome_options_krisha = Options()
        chrome_options_krisha.add_argument("--headless")
        chrome_options_krisha.add_argument("--no-sandbox")
        chrome_options_krisha.add_argument("--disable-dev-shm-usage")
        chrome_options_krisha.add_argument("--disable-gpu")
        chrome_options_krisha.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
        
        # Placeholder for global driver init - to be refined for actual use
        # service_krisha = ChromeService(ChromeDriverManager().install())
        # SELENIUM_DRIVER_KRISHA = webdriver.Chrome(service=service_krisha, options=chrome_options_krisha)
        # logging.info("Selenium WebDriver initialized for Krisha.")

    except ImportError:
        logging.warning("Selenium or WebDriver Manager not installed. Phone number scraping on Krisha might be limited.")
        USE_SELENIUM_FOR_KRISHA_PHONES = False
    except Exception as e:
        logging.error(f"Error initializing Selenium WebDriver for Krisha: {e}")
        USE_SELENIUM_FOR_KRISHA_PHONES = False
# --- End Selenium Setup ---

HEADERS_KRISHA = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Accept-Language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
    'Connection': 'keep-alive'
}


def get_phone_number_krisha_selenium(ad_url):
    """
    Uses Selenium to open a Krisha.kz ad page, click the 'show phone' button, and retrieve the number.
    Placeholder - needs robust implementation.
    """
    if not USE_SELENIUM_FOR_KRISHA_PHONES or SELENIUM_DRIVER_KRISHA is None:
        logging.info(f"Skipping Selenium phone retrieval for Krisha {ad_url} as Selenium is not enabled/initialized.")
        return None

    # Placeholder for actual Selenium interaction
    # SELENIUM_DRIVER_KRISHA.get(ad_url)
    # try:
    #     # Example: Krisha might use a class like 'show-phone' or an ID
    #     phone_button_selector = "button.show-phones" # Adjust selector
    #     WebDriverWait(SELENIUM_DRIVER_KRISHA, 10).until(
    #         EC.element_to_be_clickable((By.CSS_SELECTOR, phone_button_selector))
    #     ).click()
    #     time.sleep(2) 
        
    #     phone_element_selector = "div.offer__contacts-phones strong" # Adjust selector
    #     phone_number = WebDriverWait(SELENIUM_DRIVER_KRISHA, 5).until(
    #         EC.visibility_of_element_located((By.CSS_SELECTOR, phone_element_selector))
    #     ).text
    #     return phone_number.strip()
    # except Exception as e:
    #     logging.error(f"Selenium error fetching phone for Krisha {ad_url}: {e}")
    #     return None
    logging.warning(f"Selenium phone retrieval for Krisha ({ad_url}) is a placeholder and not fully implemented.")
    return "НУЖНА_SELENIUM_РЕАЛИЗАЦИЯ_KRISHA" # Placeholder


def parse_krisha_ad_page(ad_url, update_callback=None): # Added update_callback
    """
    Parses a single Krisha.kz ad page to extract details.
    """
    log_prefix = f"Krisha Ad ({ad_url.split('/a/show/')[-1] if '/a/show/' in ad_url else ad_url[-15:]})"
    if update_callback:
        update_callback({"log_message": f"{log_prefix}: Начало парсинга..."})
    logging.info(f"Scraping Krisha ad page: {ad_url}")
    try:
        response = requests.get(ad_url, headers=HEADERS_KRISHA, timeout=15)
        response.raise_for_status()
        time.sleep(1) 
    except requests.RequestException as e:
        logging.error(f"{log_prefix}: Ошибка загрузки страницы: {e}", exc_info=True)
        if update_callback: update_callback({"log_message": f"[ОШИБКА] {log_prefix}: Не удалось загрузить страницу: {e}", "error_occurred": True})
        return None

    soup = BeautifulSoup(response.content, 'html.parser')
    ad_data = {'link': ad_url, 'source': 'Krisha.kz'}

    try:
        # Title
        title_tag = soup.find('h1', class_=re.compile(r'offer__advert-title|a-title__text'))
        ad_data['name'] = title_tag.get_text(strip=True) if title_tag else None
        if not ad_data['name'] and update_callback:
             update_callback({"log_message": f"[ПРЕДУПРЕЖДЕНИЕ] {log_prefix}: Заголовок не найден."})

        # Price
        price_tag = soup.find('div', class_=re.compile(r'offer__price'))
        if price_tag:
            price_text = price_tag.get_text(strip=True) 
            price_cleaned = re.sub(r'[^\d]', '', price_text) 
            try:
                ad_data['price'] = float(price_cleaned) if price_cleaned.isdigit() else None
            except ValueError:
                ad_data['price'] = None
                logging.warning(f"{log_prefix}: Не удалось преобразовать цену '{price_cleaned}' во float.")
        else:
            ad_data['price'] = None
            if update_callback: update_callback({"log_message": f"[ПРЕДУПРЕЖДЕНИЕ] {log_prefix}: Цена не найдена."})
        
        # Address, Street, District, d_kv
        address_full_tag = soup.find('div', class_=re.compile(r'offer__location'))
        full_address = address_full_tag.get_text(separator=', ', strip=True) if address_full_tag else None
        ad_data['address'] = full_address
        ad_data['street'] = None # Often part of address, specific parsing needed
        ad_data['d_kv'] = None   # House/Apt number, also part of address
        if full_address:
            parts = [p.strip() for p in full_address.split(',')]
            if len(parts) > 1: # Assuming city is first, then street/district
                 ad_data['street'] = parts[1] # This is a guess
            district_match = re.search(r'р-н\s([\w\s-]+)', full_address)
            ad_data['district'] = district_match.group(1).strip() if district_match else None
        if not ad_data['address'] and update_callback:
             update_callback({"log_message": f"[ПРЕДУПРЕЖДЕНИЕ] {log_prefix}: Адрес не найден."})


        # Description
        description_tag = soup.find('div', class_=re.compile(r'offer__description'))
        ad_data['description'] = description_tag.get_text(separator='\n', strip=True) if description_tag else None

        # External ID
        match = re.search(r'/a/show/(\d+)', ad_url)
        ad_data['external_id'] = match.group(1) if match else None
        if not ad_data['external_id']:
             logging.warning(f"{log_prefix}: External ID не найден в URL {ad_url}")
        
        # Image Data
        ad_data['scraped_images_data'] = []
        gallery_tags = soup.select('div.gallery__main img, div.gallery__preview-item') 
        for img_container in gallery_tags[:5]: # Limit to 5 images
            img_tag = img_container.find('img') if img_container.name == 'div' else img_container
            img_url = None
            if img_tag:
                img_url = img_tag.get('data-src') or img_tag.get('src')
            
            if img_url and img_url.startswith('http') and not img_url.startswith('data:image'):
                try:
                    if update_callback: update_callback({"log_message": f"{log_prefix}: Загрузка изображения {img_url[:50]}..."})
                    img_response = requests.get(img_url, timeout=10, stream=True)
                    img_response.raise_for_status()
                    image_binary_content = img_response.content
                    mimetype = img_response.headers.get('Content-Type', 'application/octet-stream')
                    filename = os.path.basename(urlparse(img_url).path) or f"{ad_data['external_id']}_{uuid4().hex[:4]}.jpg"
                    
                    ad_data['scraped_images_data'].append({
                        'filename': secure_filename(filename),
                        'mimetype': mimetype,
                        'data': image_binary_content
                    })
                    logging.info(f"{log_prefix}: Изображение {img_url} успешно загружено ({len(image_binary_content)} байт).")
                except requests.RequestException as img_req_e:
                    logging.error(f"{log_prefix}: Ошибка загрузки изображения {img_url}: {img_req_e}", exc_info=True)
                    if update_callback: update_callback({"log_message": f"[ОШИБКА] {log_prefix}: Не удалось загрузить изображение {img_url[:50]}: {img_req_e}", "error_occurred": True})
                except Exception as img_e_other:
                    logging.error(f"{log_prefix}: Другая ошибка при обработке изображения {img_url}: {img_e_other}", exc_info=True)
                    if update_callback: update_callback({"log_message": f"[ОШИБКА] {log_prefix}: Ошибка обработки изображения {img_url[:50]}: {img_e_other}", "error_occurred": True})


        # Initialize all new and existing fields
        fields_to_init = ['area', 'floor', 'total_floors', 'year', 'layout', 'condition', 
                          'cat', 'status', 'm', 's', 's_kh', 'blkn', 'p']
        for f_key in fields_to_init: ad_data[f_key] = None
        
        info_items = soup.find_all('div', class_='offer__info-item')
        if not info_items: logging.warning(f"{log_prefix}: Блок с деталями 'offer__info-item' не найден.")

        for item in info_items:
            data_name_tag = item.get('data-name')
            divs = item.find_all('div')
            if len(divs) == 2:
                key_text = divs[0].get_text(strip=True).lower()
                value_text = divs[1].get_text(strip=True)

                if data_name_tag == 'live.square' or data_name_tag == 'total-square' or 'площадь общая' in key_text:
                    area_match = re.search(r'(\d[\d\s.,]*)\s*м', value_text)
                    if area_match: ad_data['area'] = float(area_match.group(1).replace(' ', '').replace(',', '.'))
                elif data_name_tag == 'flat.floor' or 'этаж' in key_text:
                    floor_parts = value_text.split(' из ')
                    if floor_parts[0].strip().isdigit(): ad_data['floor'] = int(floor_parts[0].strip())
                    if len(floor_parts) > 1 and floor_parts[1].strip().isdigit(): ad_data['total_floors'] = int(floor_parts[1].strip())
                elif data_name_tag == 'house.year' or 'год постройки' in key_text:
                    year_match = re.search(r'(\d{4})', value_text)
                    if year_match: ad_data['year'] = year_match.group(1) # year is String
                elif 'планировка' in key_text: ad_data['layout'] = value_text
                elif 'состояние квартиры' in key_text or 'состояние' in key_text or 'ремонт' in key_text : ad_data['condition'] = value_text
                elif 'тип строения' in key_text or 'материал стен' in key_text: ad_data['m'] = value_text # Material
                elif 'жилая площадь' in key_text: ad_data['s'] = value_text # Secondary area 's'
                elif 'площадь кухни' in key_text: ad_data['s_kh'] = value_text
                elif 'балкон' in key_text: ad_data['blkn'] = value_text
                # 'p' (position/corner), 'cat' (category), 'status', 'd_kv' are harder to map reliably from Krisha's typical structure without specific examples
            else:
                logging.debug(f"{log_prefix}: Неожиданная структура в info_item (data-name: {data_name_tag}): {item.get_text(strip=True)}")

        ad_data['seller_phone'] = get_phone_number_krisha_selenium(ad_url)
        ad_data['last_scraped_at'] = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
        
        if not ad_data.get('name') and not ad_data.get('description'):
            logging.warning(f"{log_prefix}: Ни название, ни описание не найдены. Пропуск объявления Krisha.")
            if update_callback: update_callback({"log_message": f"[ПРЕДУПРЕЖДЕНИЕ] {log_prefix}: Название и описание не найдены (Krisha), объявление пропущено.", "error_occurred": True})
            return None

        log_msg_success = f"{log_prefix}: Успешно разобрано: {ad_data.get('name', 'N/A') if ad_data.get('name') else ad_data.get('description', 'N/A')[:50]}"
        logging.info(log_msg_success)
        if update_callback: update_callback({"log_message": log_msg_success})
        return ad_data

    except Exception as e:
        logging.error(f"{log_prefix}: Ошибка при разборе деталей объявления: {e}", exc_info=True)
        if update_callback:
            update_callback({"log_message": f"[ОШИБКА] {log_prefix}: Ошибка разбора деталей: {e}", "error_occurred": True})
        return None


def scrape_krisha(base_url, num_pages_to_scrape=1, update_callback=None):
    """
    Scrapes Krisha.kz for property listings.
    """
    all_properties = []

    global SELENIUM_DRIVER_KRISHA
    if USE_SELENIUM_FOR_KRISHA_PHONES and SELENIUM_DRIVER_KRISHA is None:
        try:
            logging.info("Initializing Selenium WebDriver for Krisha scraping session...")
            service_krisha = ChromeService(ChromeDriverManager().install())
            SELENIUM_DRIVER_KRISHA = webdriver.Chrome(service=service_krisha, options=chrome_options_krisha if 'chrome_options_krisha' in globals() else None)
            logging.info("Selenium WebDriver initialized successfully for Krisha.")
        except Exception as e:
            logging.error(f"Failed to initialize Selenium WebDriver for Krisha: {e}. Phone numbers might not be scraped.")
            global USE_SELENIUM_FOR_KRISHA_PHONES_TEMP_DISABLE
    """
    Scrapes Krisha.kz for property listings.
    """
    all_properties = []

    if USE_SELENIUM_FOR_KRISHA_PHONES and SELENIUM_DRIVER_KRISHA is None:
        logging.warning("Krisha Scraper: Selenium use is enabled but no global driver found. Phone numbers might be missed.")
        if update_callback:
            update_callback({"log_message": "[ПРЕДУПРЕЖДЕНИЕ] Krisha: Selenium включен, но драйвер не инициализирован глобально. Телефоны могут быть пропущены."})


    for page_num in range(1, num_pages_to_scrape + 1):
        page_url = base_url 
        if page_num > 1: # Krisha pagination uses &page=
            page_url = f"{base_url}&page={page_num}"
        
        current_task_message = f"Krisha.kz: Загрузка страницы {page_num} из {num_pages_to_scrape}..."
        scraper_progress = int(((page_num -1) / num_pages_to_scrape) * 50)
        if update_callback:
            update_callback({"current_task": current_task_message, "log_message": current_task_message, "progress_percent": scraper_progress })
        logging.info(current_task_message)

        try:
            response = requests.get(page_url, headers=HEADERS_KRISHA, timeout=20)
            response.raise_for_status()
            time.sleep(2) 
        except requests.RequestException as e:
            logging.error(f"Krisha.kz: Ошибка загрузки страницы {page_url}: {e}", exc_info=True)
            if update_callback:
                update_callback({"log_message": f"[ОШИБКА] Krisha.kz: Не удалось загрузить страницу: {page_url}. Ошибка: {e}", "error_occurred": True})
            continue

        soup = BeautifulSoup(response.content, 'html.parser')
        
        ad_card_selector = 'div.a-card.a-storage-item' 
        ad_cards = soup.select(ad_card_selector)

        if not ad_cards:
            log_msg_no_ads = f"Krisha.kz: Не найдено карточек объявлений на странице {page_url} (селектор: '{ad_card_selector}')."
            logging.warning(log_msg_no_ads)
            if soup.find(text=re.compile(r"Попробуйте изменить параметры поиска|ничего не найдено", re.IGNORECASE)):
                 log_msg_no_ads += " (Возможно, нет объявлений по данному запросу или конец результатов)."
                 if update_callback: update_callback({"log_message": log_msg_no_ads})
                 break # Likely end of results or specific filter yields nothing
            if update_callback: update_callback({"log_message": log_msg_no_ads, "error_occurred": page_num == 1})
            if page_num > 1: break # Stop if not first page

        num_cards_on_page = len(ad_cards)
        logging.info(f"Krisha.kz: Найдено {num_cards_on_page} карточек на стр. {page_num}.")
        if update_callback: update_callback({"log_message": f"Krisha.kz: Найдено {num_cards_on_page} карточек на стр. {page_num}."})

        for card_idx, card in enumerate(ad_cards):
            ad_url_path = None
            try:
                ad_link_tag = card.find('a', class_='a-card__title', href=True)
                if ad_link_tag and ad_link_tag['href']:
                    ad_url_path = ad_link_tag['href']
                    ad_url_full = ad_url_path if ad_url_path.startswith('http') else f"https://krisha.kz{ad_url_path}"
                    
                    item_progress_within_page = int(((card_idx + 1) / num_cards_on_page) * (1/num_pages_to_scrape) * 50) if num_cards_on_page > 0 else 0
                    current_overall_progress = scraper_progress + item_progress_within_page

                    if update_callback:
                        update_callback({
                            "current_task": f"Krisha.kz: Стр. {page_num}, объявление {card_idx+1}/{num_cards_on_page}",
                            "progress_percent": min(current_overall_progress, 50)
                        })
                    property_data = parse_krisha_ad_page(ad_url_full, update_callback=update_callback) 
                    if property_data:
                        all_properties.append(property_data)
                else:
                    logging.warning("Krisha.kz: Найдена карточка без ссылки на объявление.")
                    if update_callback: update_callback({"log_message": "[ПРЕДУПРЕЖДЕНИЕ] Krisha.kz: Найдена карточка без ссылки."})
            except Exception as e_card:
                logging.error(f"Krisha.kz: Ошибка обработки карточки (URL path: {ad_url_path if ad_url_path else 'N/A'}): {e_card}", exc_info=True)
                if update_callback: update_callback({"log_message": f"[ОШИБКА] Krisha.kz: Ошибка обработки карточки: {e_card}", "error_occurred": True})
                continue # Skip to next card
        
        log_msg_page_finish = f"Krisha.kz: Завершена страница {page_num}. Собрано объявлений с этой страницы: {len(ad_cards) if ad_cards else 0}. Всего успешно собрано: {len(all_properties)}"
        if update_callback:
            update_callback({"log_message": log_msg_page_finish})
        logging.info(log_msg_page_finish)

        if page_num < num_pages_to_scrape:
            time.sleep(3)
            
    if update_callback:
        update_callback({"current_task": "Сбор данных с Krisha.kz завершен.", "progress_percent": 50})

    # Selenium driver management as in OLX scraper
    if USE_SELENIUM_FOR_KRISHA_PHONES and SELENIUM_DRIVER_KRISHA is not None:
        try:
            SELENIUM_DRIVER_KRISHA.quit()
            SELENIUM_DRIVER_KRISHA = None
            logging.info("Selenium WebDriver shut down for Krisha.")
        except Exception as e:
            logging.error(f"Error shutting down Selenium WebDriver for Krisha: {e}")

    return all_properties

if __name__ == '__main__':
    # Example Usage:
    krisha_url = "https://krisha.kz/prodazha/kvartiry/petropavlovsk/?das[who]=1" # From owner
    logging.info(f"Starting Krisha scraper for URL: {krisha_url}")
    
    # For testing, you might want to disable Selenium phone fetching
    # USE_SELENIUM_FOR_KRISHA_PHONES = False
    def _test_callback_krisha(status):
        print(f"KRISHA_TEST_CB: {status}")

    scraped_data_krisha = scrape_krisha(krisha_url, num_pages_to_scrape=1, update_callback=_test_callback_krisha)
    
    if scraped_data_krisha:
        logging.info(f"Successfully scraped {len(scraped_data_krisha)} properties from Krisha.kz.")
        for i, prop in enumerate(scraped_data_krisha[:2]): # Print first 2
            print(f"\n--- Krisha Property {i+1} ---")
            for key, value in prop.items():
                print(f"{key}: {value}")
    else:
        logging.warning("No data scraped from Krisha.kz.")
    
    # if SELENIUM_DRIVER_KRISHA:
    #     SELENIUM_DRIVER_KRISHA.quit()
    #     SELENIUM_DRIVER_KRISHA = None
