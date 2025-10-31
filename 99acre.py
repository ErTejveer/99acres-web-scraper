import os
import re
import json
import time
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager

BASE_URL = "https://www.99acres.com/property-in-agra-ffid"

def setup_driver(headless=False):
    options = Options()
    if headless:
        options.add_argument("--headless=new")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--disable-notifications")
    options.add_argument("--start-maximized")
    options.add_argument("--no-sandbox")
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    return driver

def extract_properties_from_html(html):
    soup = BeautifulSoup(html, "html.parser")
    properties = []

    for tag in soup.find_all("script", {"type": "application/ld+json"}):
        try:
            data = json.loads(tag.string.strip())
            if isinstance(data, list):
                for d in data:
                    if "Apartment" in d.get("@type", "") or "Residence" in d.get("@type", ""):
                        properties.append(d)
            elif isinstance(data, dict):
                if "Apartment" in data.get("@type", "") or "Residence" in data.get("@type", ""):
                    properties.append(data)
        except Exception:
            continue
    return properties

def click_and_extract_contacts(driver):
    contact_numbers_set = set()
    buttons = driver.find_elements(By.XPATH, "//button[contains(., 'View Phone Number') or contains(., 'Call')]")
    print(f"📞 Found {len(buttons)} contact buttons. Attempting to reveal numbers...")

    for btn in buttons:
        try:
            driver.execute_script("arguments[0].scrollIntoView(true);", btn)
            time.sleep(1)
            btn.click()
            time.sleep(2)
        except Exception:
            continue

    phones = re.findall(r"(?:\+91[\-\s]?)?[6-9]\d{9}", driver.page_source)
    contact_numbers_set.update(phones)
    return list(contact_numbers_set)

def scrape_city(city_name, base_url):
    print(f"\n🌆 Starting scrape for {city_name} — {base_url}")
    driver = setup_driver(headless=False)
    city_data = {"city": city_name, "properties": [], "contacts": []}
    page = 1
    all_properties = []
    all_contacts = []

    try:
        while True:
            url = f"{base_url}?page={page}" if page > 1 else base_url
            print(f"\n🔄 Loading page {page} — {url}")
            driver.get(url)
            time.sleep(5)

            html = driver.page_source
            properties = extract_properties_from_html(html)

            if not properties:
                print(f"❌ No more properties found. Ending at page {page-1}.")
                break

            print(f"🏠 Found {len(properties)} properties on page {page}.")
            contacts = click_and_extract_contacts(driver)
            print(f"📱 Found {len(contacts)} contacts on page {page}.")

            # Combine data
            for idx, prop in enumerate(properties):
                prop["contact_numbers"] = [contacts[idx]] if idx < len(contacts) else []
                all_properties.append(prop)

            all_contacts.extend(contacts)
            page += 1
            time.sleep(3)  # Prevent rate-limiting

    finally:
        driver.quit()

    city_data["properties"] = all_properties
    city_data["contacts"] = list(set(all_contacts))
    print(f"✅ Done scraping {city_name}! Total properties: {len(all_properties)}")

    return city_data

if __name__ == "__main__":
    os.makedirs("output", exist_ok=True)
    all_data = []

    data = scrape_city("agra", BASE_URL)
    all_data.append(data)

    output_path = "output/agra_full_data.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(all_data, f, indent=4, ensure_ascii=False)

    print("\n🎉 All Agra property data scraped successfully!")
    print(f"📁 Saved to: {output_path}")