import os
import config
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import random
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
import logging
from webdriver_manager.chrome import ChromeDriverManager
from selenium.common.exceptions import StaleElementReferenceException
from config import HEADERS, PROXIES

os.environ['REQUESTS_CA_BUNDLE'] = config.certify

def initialize_driver(headers_list, proxy_list):
    logging.getLogger('selenium').setLevel(logging.ERROR)
    logging.getLogger('urllib3').setLevel(logging.ERROR)

    options = Options()
    options.page_load_strategy = 'eager'

    options.add_experimental_option('excludeSwitches', ['enable-logging'])
    options.add_argument('--log-level=3')
    options.add_argument("--disable-features=AudioServiceOutOfProcess")

    prefs = {
        "profile.default_content_settings.images": 2,
        "profile.managed_default_content_settings.images": 2,
        "javascript.enabled": True,
        "plugins.plugins_disabled": ["*"],
    }
    options.add_experimental_option("prefs", prefs)

    options.add_argument("--ignore-certificate-errors")
    options.add_argument("--ignore-ssl-errors")
    options.set_capability("acceptInsecureCerts", True)
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-webgl")
    options.add_argument("--disable-3d-apis")
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-software-rasterizer")
    options.add_argument("--headless=new")
    options.add_argument("--window-size=1920,1080")

    user_agent = random.choice(headers_list)['User-Agent']
    options.add_argument(f"user-agent={user_agent}")

    proxy = random.choice(proxy_list)
    if proxy:
        options.add_argument(f"--proxy-server={proxy}")

    log_path = os.devnull if os.name == 'posix' else 'NUL'
    service = Service(ChromeDriverManager().install(), log_output=log_path)

    driver = webdriver.Chrome(service=service, options=options)
    return driver

def scrape_url(driver, url, timeout=10):
    extracted = {}
    try:
        driver.get(url)
        for attempt in range(3):
            try:
                try:
                    h1 = WebDriverWait(driver, timeout).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, "h1"))
                    )
                    extracted["title"] = h1.text.strip()
                except:
                    extracted["title"] = driver.title.strip()

                ps = driver.find_elements(By.CSS_SELECTOR, "p")
                paragraph_texts = [p.text.strip() for p in ps if p.text.strip()]
                extracted["paragraphs"] = "\n\n".join(paragraph_texts)
                return extracted
            except StaleElementReferenceException:
                print(f"⚠️ Erreur de référence périmée. Nouvelle tentative {attempt + 1}/3...")
                continue
    except Exception as e:
        extracted["title"] = f"ERROR: {e}"
        extracted["paragraphs"] = f"ERROR: {e}"
    return extracted

def close_driver(driver):
    if driver:
        try:
            driver.quit()
        except Exception as e:
            print(f"❌ Erreur lors de la fermeture du driver : {e}")

def scrape_worker_threaded(task):
    driver = None
    url = task["url"]
    subquestion = task["subquestion"]
    try:
        print(f"🔗 Scraping démarré pour {url} (Sous-question : {subquestion})")

        driver = initialize_driver(HEADERS, PROXIES)

        data = scrape_url(driver, url)
        data["url"] = url
        data["subquestion"] = subquestion

        print(f"✅ Scraping terminé pour {url}")
        return data
    except Exception as e:
        print(f"❌ Erreur lors du scraping de {url} : {e}")
        return None
    finally:
        if driver:
            close_driver(driver)