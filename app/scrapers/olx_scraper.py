import requests
from bs4 import BeautifulSoup
import time
import logging
import re # For cleaning text, extracting numbers
import json # For parsing JSON-like data if found
from datetime import datetime # Import datetime

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- Selenium setup (optional, only if needed for phone numbers) ---
USE_SELENIUM_FOR_OLX_PHONES = True # Set to False if direct scraping works or to skip
SELENIUM_DRIVER = None

if USE_SELENIUM_FOR_OLX_PHONES:
    try:
        from selenium import webdriver
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        from selenium.webdriver.chrome.service import Service as ChromeService
        from webdriver_manager.chrome import ChromeDriverManager
        from selenium.webdriver.chrome.options import Options
        
        # Setup Chrome options
        chrome_options = Options()
        chrome_options.add_argument("--headless")  # Run headless
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.212 Safari/537.36")

        # Initialize WebDriver
        # Using webdriver_manager to handle driver download and path
        # service = ChromeService(ChromeDriverManager().install())
        # SELENIUM_DRIVER = webdriver.Chrome(service=service, options=chrome_options)
        # logging.info("Selenium WebDriver initialized for OLX.")

    except ImportError:
        logging.warning("Selenium or WebDriver Manager not installed. Phone number scraping on OLX might be limited.")
        USE_SELENIUM_FOR_OLX_PHONES = False
    except Exception as e:
        logging.error(f"Error initializing Selenium WebDriver for OLX: {e}")
        USE_SELENIUM_FOR_OLX_PHONES = False
# --- End Selenium Setup ---


# Standard headers to mimic a browser
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.212 Safari/537.36',
    'Accept-Language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
    'Accept-Encoding': 'gzip, deflate, br',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
    'Connection': 'keep-alive'
}

def get_phone_number_olx_selenium(ad_url):
    """
    Uses Selenium to open an ad page, click the 'show phone' button, and retrieve the number.
    This function is a placeholder and needs to be robustly implemented.
    It should manage its own WebDriver instance or use a shared one carefully.
    """
    if not USE_SELENIUM_FOR_OLX_PHONES or SELENIUM_DRIVER is None:
        logging.info(f"Skipping Selenium phone retrieval for {ad_url} as Selenium is not enabled/initialized.")
        return None

    # For now, let's assume a global driver is managed if this function is called.
    # A better approach would be to initialize driver here or pass it.
    # This is a simplified placeholder.
    
    # Placeholder: Actual Selenium interaction would go here.
    # SELENIUM_DRIVER.get(ad_url)
    # try:
    #     # Example: Find button by part of its class or data-cy attribute
    #     phone_button_xpath = "//button[contains(@data-cy, 'phone-number-button') or contains(@class, 'contact-button')]" # Adjust selector
    #     WebDriverWait(SELENIUM_DRIVER, 10).until(
    #         EC.element_to_be_clickable((By.XPATH, phone_button_xpath))
    #     ).click()
    #     time.sleep(2) # Wait for number to load
        
    #     # Example: Find phone number element
    #     phone_element_xpath = "//div[contains(@data-cy, 'phone-number-text') or contains(@class, 'phone-text')]" # Adjust selector
    #     phone_number = WebDriverWait(SELENIUM_DRIVER, 5).until(
    #         EC.visibility_of_element_located((By.XPATH, phone_element_xpath))
    #     ).text
    #     return phone_number.strip()
    # except Exception as e:
    #     logging.error(f"Selenium error fetching phone for {ad_url}: {e}")
    #     return None
    logging.warning(f"Selenium phone retrieval for OLX ({ad_url}) is a placeholder and not fully implemented.")
    return "НУЖНА_SELENIUM_РЕАЛИЗАЦИЯ_OLX" # Placeholder


def parse_olx_ad_page(ad_url, update_callback=None): # Added update_callback
    """
    Parses a single OLX ad page to extract details.
    """
    # Initial log message for the ad page
    log_prefix = f"OLX Ad ({ad_url.split('-ID')[-1].split('.')[0] if '-ID' in ad_url else ad_url[-15:]})"
    if update_callback:
        update_callback({"log_message": f"{log_prefix}: Начало парсинга..."})
    
    logging.info(f"Scraping OLX ad page: {ad_url}")
    try:
        response = requests.get(ad_url, headers=HEADERS, timeout=15)
        response.raise_for_status()
        time.sleep(1) 
    except requests.RequestException as e:
        logging.error(f"{log_prefix}: Ошибка загрузки страницы: {e}", exc_info=True)
        if update_callback: update_callback({"log_message": f"[ОШИБКА] {log_prefix}: Не удалось загрузить страницу: {e}", "error_occurred": True})
        return None

    soup = BeautifulSoup(response.content, 'html.parser')
    ad_data = {'link': ad_url, 'source': 'OLX.kz'} # Changed source_url to link

    try:
        # Title
        title_tag = soup.find('h1', {'data-cy': 'ad_title'})
        ad_data['name'] = title_tag.get_text(strip=True) if title_tag else None
        if not ad_data['name'] and update_callback:
            update_callback({"log_message": f"[ПРЕДУПРЕЖДЕНИЕ] {log_prefix}: Заголовок не найден."})

        # Price
        price_tag = soup.find('div', {'data-testid': 'ad-price-container'})
        price_text_tag = price_tag.find('h3') if price_tag else None
        if price_text_tag:
            price_text = price_text_tag.get_text(strip=True)
            price_cleaned = re.sub(r'[^\d]', '', price_text)
            try:
                ad_data['price'] = float(price_cleaned) if price_cleaned.isdigit() else None # Store as float
            except ValueError:
                ad_data['price'] = None
                logging.warning(f"{log_prefix}: Не удалось преобразовать цену '{price_cleaned}' во float.")
        else:
            ad_data['price'] = None
            if update_callback: update_callback({"log_message": f"[ПРЕДУПРЕЖДЕНИЕ] {log_prefix}: Цена не найдена."})
        
        # Address & Street (OLX often has one location string)
        location_tag = soup.find('p', class_=re.compile(r'location-|address-|css-\w+-TextLocation'))
        full_address = location_tag.get_text(strip=True) if location_tag else None
        ad_data['address'] = full_address
        # Attempt to extract street (this is highly heuristic for OLX)
        if full_address:
            # Assuming street might be before first comma if city is included, or if it's a main part.
            ad_data['street'] = full_address.split(',')[0].strip() # Very basic assumption
        else:
            ad_data['street'] = None
        # d_kv (house/apt number) is usually part of address, hard to parse reliably without more structure

        # Description
        description_tag = soup.find('div', {'data-cy': 'ad_description'})
        ad_data['description'] = description_tag.get_text(separator='\n', strip=True) if description_tag else None

        # External ID
        match = re.search(r'-ID([a-zA-Z0-9]+)\.html', ad_url)
        ad_data['external_id'] = match.group(1) if match else None
        if not ad_data['external_id']:
            logging.warning(f"{log_prefix}: External ID не найден в URL {ad_url}.")
        
        # Image Data (fetch binary content)
        ad_data['scraped_images_data'] = []
        gallery_image_tags = soup.select('div.swiper-zoom-container img, div.photo-item img, img. શોધો') # Common OLX patterns
        if not gallery_image_tags: gallery_image_tags = soup.select('div[data-cy="adPhotos-swiper"] img')


        for img_tag in gallery_image_tags[:5]: # Limit to 5 images
            img_url = img_tag.get('src')
            if img_url and img_url.startswith('http') and not img_url.startswith('data:image'): # Ensure it's a fetchable URL
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


        # Details: Area, Floor, Total Floors, Year, etc.
        # Initialize all new fields to None
        fields_to_init = ['area', 'floor', 'total_floors', 'year', 'layout', 'condition', 
                          'cat', 'status', 'm', 's', 's_kh', 'blkn', 'p', 'd_kv']
        for f_key in fields_to_init: ad_data[f_key] = None

        # OLX details are often in <p> tags with structure "Label: Value" or similar text nodes
        # Example: <p class="css-b5m1rv er34gjf0">Тип дома: Кирпичный</p>
        # Or in a list: <li class="css-1r0si1e"><span>Общая площадь</span><span>60 м²</span></li>
        detail_tags = soup.select('ul[data-testid="advert-properties"] li p, p.css-b5m1rv') # More generic
        
        details_text_map = {}
        for tag in detail_tags:
            text = tag.get_text(separator=": ", strip=True)
            if ":" in text:
                key, value = text.split(":", 1)
                details_text_map[key.strip().lower()] = value.strip()
        
        # Populate fields from details_text_map
        if 'общая площадь' in details_text_map or 'площадь' in details_text_map: # OLX often uses 'Общая площадь'
            area_str = details_text_map.get('общая площадь', details_text_map.get('площадь'))
            area_match = re.search(r'(\d[\d\s.,]*)\s*м', area_str) if area_str else None
            if area_match: ad_data['area'] = float(area_match.group(1).replace(' ', '').replace(',', '.'))
        
        if 'этаж' in details_text_map:
            floor_str = details_text_map['этаж']
            floor_parts = floor_str.split('/')
            if floor_parts[0].strip().isdigit(): ad_data['floor'] = int(floor_parts[0].strip())
            if len(floor_parts) > 1 and floor_parts[1].strip().isdigit(): ad_data['total_floors'] = int(floor_parts[1].strip())

        if 'год постройки' in details_text_map or 'год выпуска' in details_text_map:
            year_str = details_text_map.get('год постройки', details_text_map.get('год выпуска'))
            year_match = re.search(r'(\d{4})', year_str) if year_str else None
            if year_match: ad_data['year'] = year_match.group(1) # Year is String
        
        if 'тип дома' in details_text_map: ad_data['m'] = details_text_map['тип дома'] # Material
        if 'планировка' in details_text_map: ad_data['layout'] = details_text_map['планировка']
        if 'состояние' in details_text_map: ad_data['condition'] = details_text_map['состояние']
        if 'категория' in details_text_map: ad_data['cat'] = details_text_map['категория'] # Hypothetical
        if 'статус' in details_text_map: ad_data['status'] = details_text_map['статус'] # Hypothetical
        if 'балкон' in details_text_map: ad_data['blkn'] = details_text_map['балкон']
        # Other fields like 's', 's_kh', 'p', 'd_kv' are harder to map without specific examples from OLX


        ad_data['seller_phone'] = get_phone_number_olx_selenium(ad_url) 
        ad_data['last_scraped_at'] = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S') # Corrected usage
        
        if not ad_data.get('name') and not ad_data.get('description'): 
            logging.warning(f"{log_prefix}: Ни название, ни описание не найдены. Пропуск объявления.")
            if update_callback: update_callback({"log_message": f"[ПРЕДУПРЕЖДЕНИЕ] {log_prefix}: Название и описание не найдены, объявление пропущено.", "error_occurred": True})
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


def scrape_olx(base_url, num_pages_to_scrape=1, update_callback=None):
    """
    Scrapes OLX.kz for property listings.
    """
    all_properties = []
    
    """
    Scrapes OLX.kz for property listings.
    """
    all_properties = []
    
    # Selenium Driver Initialization (if needed, managed by run_parsing_task or per-call)
    # For this function, we assume SELENIUM_DRIVER is either None or a valid driver instance
    # if phone scraping via Selenium is enabled. The actual initialization happens in run_parsing_task.
    
    if USE_SELENIUM_FOR_OLX_PHONES and SELENIUM_DRIVER is None:
        # This case should ideally be handled by the caller (e.g. run_parsing_task)
        # or a local instance should be created and quit here.
        # For now, if called directly and SELENIUM_DRIVER is None, it will skip selenium part.
        logging.warning("OLX Scraper: Selenium use is enabled but no global driver found. Phone numbers might be missed if Selenium is required.")
        if update_callback:
            update_callback({"log_message": "[ПРЕДУПРЕЖДЕНИЕ] OLX: Selenium включен, но драйвер не инициализирован глобально. Телефоны могут быть пропущены."})


    for page_num in range(1, num_pages_to_scrape + 1):
        page_url = base_url # Default for page 1
        if page_num > 1:
            # Ensure correct pagination URL construction for OLX
            if "?" in base_url and "search%5Bfilter_enum_tipsobstvennosti%5D%5B0%5D=ot_hozyaina" in base_url : # typical OLX structure
                 page_url = f"{base_url}&page={page_num}"
            else: # Fallback if base_url is simpler
                 page_url = f"{base_url}?page={page_num}"
        
        current_task_message = f"OLX: Загрузка страницы {page_num} из {num_pages_to_scrape}..."
        # Progress: 0-50% for scraping part.
        # Calculate progress based on current page relative to total pages to scrape for this source.
        scraper_progress = int(((page_num -1) / num_pages_to_scrape) * 50) 
        if update_callback:
            update_callback({"current_task": current_task_message, "log_message": current_task_message, "progress_percent": scraper_progress })
        logging.info(current_task_message)

        try:
            response = requests.get(page_url, headers=HEADERS, timeout=20)
            response.raise_for_status()
            time.sleep(2) 
        except requests.RequestException as e:
            logging.error(f"OLX: Ошибка загрузки страницы {page_url}: {e}", exc_info=True)
            if update_callback:
                update_callback({"log_message": f"[ОШИБКА] OLX: Не удалось загрузить страницу: {page_url}. Ошибка: {e}", "error_occurred": True})
            continue 

        soup = BeautifulSoup(response.content, 'html.parser')
        
        ad_card_selector = 'div[data-cy="l-card"]' 
        ad_cards = soup.select(ad_card_selector)
        
        if not ad_cards:
            log_msg_no_ads = f"OLX: Не найдено карточек объявлений на странице {page_url} (селектор: '{ad_card_selector}')."
            logging.warning(log_msg_no_ads)
            if update_callback: update_callback({"log_message": log_msg_no_ads, "error_occurred": page_num == 1}) # Error if first page has no ads
            if page_num > 1 : 
                 logging.info(f"OLX: Предположительно конец результатов на стр. {page_num}.")
                 if update_callback: update_callback({"log_message": f"OLX: Предположительно конец результатов на стр. {page_num}."})
                 break 
            # continue # If first page and no ads, something is wrong or no ads at all.

        num_cards_on_page = len(ad_cards)
        logging.info(f"OLX: Найдено {num_cards_on_page} карточек на стр. {page_num}.")
        if update_callback: update_callback({"log_message": f"OLX: Найдено {num_cards_on_page} карточек на стр. {page_num}."})

        for card_idx, card in enumerate(ad_cards):
            ad_url_path = None # Initialize here for error logging
            try:
                ad_link_tag = card.find('a', href=True)
                if ad_link_tag and ad_link_tag['href']:
                    ad_url_path = ad_link_tag['href']
                    ad_url_full = ad_url_path if ad_url_path.startswith('http') else f"https://www.olx.kz{ad_url_path}"
                    
                    if "/obyavlenie/" not in ad_url_full: # OLX ad links typically contain this
                        logging.debug(f"OLX: Пропуск нерелевантной ссылки: {ad_url_full}") # Debug as this can be common
                        if update_callback: update_callback({"log_message": f"OLX: Пропуск (не объявление): {ad_url_full[:70]}..."})
                        continue
                    
                    # Update progress for each item within the page
                    item_progress_within_page = int(((card_idx + 1) / num_cards_on_page) * (1/num_pages_to_scrape) * 50) if num_cards_on_page > 0 else 0
                    current_overall_progress = scraper_progress + item_progress_within_page
                    
                    if update_callback:
                        update_callback({
                            "current_task": f"OLX: Стр. {page_num}, объявление {card_idx+1}/{num_cards_on_page}",
                            "progress_percent": min(current_overall_progress, 50) # Cap at 50 for scraping phase
                        })
                    
                    property_data = parse_olx_ad_page(ad_url_full, update_callback=update_callback) 
                    if property_data:
                        all_properties.append(property_data)
                else:
                    logging.warning("OLX: Найдена карточка без ссылки.")
                    if update_callback: update_callback({"log_message": "[ПРЕДУПРЕЖДЕНИЕ] OLX: Найдена карточка без ссылки."})
            except Exception as e_card:
                logging.error(f"OLX: Ошибка обработки карточки (URL path: {ad_url_path if ad_url_path else 'N/A'}): {e_card}", exc_info=True)
                if update_callback: update_callback({"log_message": f"[ОШИBКА] OLX: Ошибка обработки карточки: {e_card}", "error_occurred": True})
                # Continue to the next card
        
        log_msg_page_finish = f"OLX: Завершена страница {page_num}. Собрано объявлений с этой страницы: {len(ad_cards) if ad_cards else 0}. Всего успешно собрано: {len(all_properties)}"
        if update_callback:
            update_callback({"log_message": log_msg_page_finish})
        logging.info(log_msg_page_finish)

        if page_num < num_pages_to_scrape: # If there are more pages to scrape
             time.sleep(3) # Longer delay between main listing pages

    if update_callback:
        update_callback({"current_task": "Сбор данных с OLX.kz завершен.", "progress_percent": 50}) 
    
    # Selenium driver should be managed by the calling task (run_parsing_task)
    # if USE_SELENIUM_FOR_OLX_PHONES and SELENIUM_DRIVER is not None:
    #     try:
    #         SELENIUM_DRIVER.quit()
    #         SELENIUM_DRIVER = None 
    #         logging.info("Selenium WebDriver shut down for OLX.")
    #     except Exception as e:
    #         logging.error(f"Error shutting down Selenium WebDriver for OLX: {e}")
            
    return all_properties

if __name__ == '__main__':
    # Example Usage:
    olx_url_main = "https://www.olx.kz/nedvizhimost/prodazha-kvartiry/petropavlovsk/?search%5Bfilter_enum_tipsobstvennosti%5D%5B0%5D=ot_hozyaina"
    logging.info(f"Starting OLX scraper for URL: {olx_url_main}")
    
    # For testing, you might want to disable Selenium phone fetching initially
    # USE_SELENIUM_FOR_OLX_PHONES = False
    
    # Example callback for standalone testing
    def _test_callback(status):
        print(f"OLX_TEST_CALLBACK: {status}")

    scraped_data_olx = scrape_olx(olx_url_main, num_pages_to_scrape=1, update_callback=_test_callback)
    
    if scraped_data_olx:
        logging.info(f"Successfully scraped {len(scraped_data_olx)} properties from OLX.")
        # Print details of the first few properties for verification
        for i, prop_item in enumerate(scraped_data_olx[:2]):
            print(f"\n--- OLX Property {i+1} ---")
            for key_item, value_item in prop_item.items():
                print(f"{key_item}: {value_item}")
    else:
        logging.warning("No data scraped from OLX.")

    # if SELENIUM_DRIVER: 
    #     SELENIUM_DRIVER.quit()
    #     SELENIUM_DRIVER = None
