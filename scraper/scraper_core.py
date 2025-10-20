from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time

def scroll_and_scrape_properties(driver, max_scrolls=20):
    """
    Scrolls through the property sidebar and scrapes visible property cards.
    Returns a list of dictionaries with key property info.
    """

    print("🌀 Scrolling and scraping property cards...")

    property_selector = "//div[contains(@class,'deal-scroll')]//div[contains(@class,'deal-wrapper') or contains(@class,'property-card')]"
    properties = []

    # Wait for first cards to appear
    try:
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.XPATH, property_selector))
        )
        print("✅ Property cards detected in sidebar")
    except:
        print("⚠️ No property cards found initially, waiting...")
        time.sleep(5)

    last_count = 0
    for i in range(max_scrolls):
        cards = driver.find_elements(By.XPATH, property_selector)
        print(f"📍 Found {len(cards)} cards after scroll {i+1}")

        for card in cards:
            try:
                # Address
                address_el = card.find_element(By.XPATH, ".//*[contains(@class,'address') or contains(text(), ', FL') or contains(text(), ', CA') or contains(text(), ', TX')]")
                full_address = address_el.text.strip()

                # Owner name
                owner_el = None
                for path in [
                    ".//*[contains(@class,'owner')]",
                    ".//*[contains(text(), 'LLC')]",
                    ".//*[contains(text(), 'Trust')]"
                ]:
                    try:
                        owner_el = card.find_element(By.XPATH, path)
                        break
                    except:
                        continue
                owner_name = owner_el.text.strip() if owner_el else ""

                # Status or value
                status = ""
                try:
                    status_el = card.find_element(By.XPATH, ".//*[contains(@class,'status') or contains(text(),'Lead') or contains(text(),'Added')]")
                    status = status_el.text.strip()
                except:
                    pass

                # Estimated value or price
                value = ""
                try:
                    value_el = card.find_element(By.XPATH, ".//*[contains(text(), '$')]")
                    value = value_el.text.strip()
                except:
                    pass

                prop = {
                    "full_address": full_address,
                    "owner_name": owner_name,
                    "status": status,
                    "est_value": value
                }

                if prop not in properties:
                    properties.append(prop)

            except Exception:
                continue

        # Scroll down inside sidebar
        driver.execute_script("""
            const sidebar = document.querySelector('.deal-scroll');
            if (sidebar) sidebar.scrollBy(0, sidebar.scrollHeight);
        """)
        time.sleep(1.5)

        # Stop if no new cards load
        if len(cards) == last_count:
            print("🔚 Reached end of sidebar — no new cards.")
            break
        last_count = len(cards)

    print(f"✅ Total scraped: {len(properties)} properties")
    return properties