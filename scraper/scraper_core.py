from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time

def scroll_and_scrape_properties(driver, max_scrolls=30):
    """
    Scrolls through the property sidebar and scrapes visible property cards.
    Returns a clean list of dictionaries compatible with Airtable.
    """

    print("🌀 Scrolling and scraping property cards...")

    property_selector = "//div[contains(@class,'deal-scroll')]//div[contains(@class,'deal-wrapper') or contains(@class,'property-card')]"
    properties = []

    try:
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.XPATH, property_selector))
        )
        print("✅ Property cards detected in sidebar")
    except:
        print("⚠️ No property cards found initially.")
        return []

    last_count = 0
    for i in range(max_scrolls):
        cards = driver.find_elements(By.XPATH, property_selector)
        print(f"📍 Found {len(cards)} cards after scroll {i+1}")

        for card in cards:
            try:
                # Address
                try:
                    address_el = card.find_element(By.XPATH, ".//*[contains(@class,'address') or contains(text(), ', FL') or contains(text(), ', TX') or contains(text(), ', CA')]")
                    full_address = address_el.text.strip()
                except:
                    full_address = ""

                # Owner name
                owner_name = ""
                for path in [".//*[contains(@class,'owner')]", ".//*[contains(text(),'LLC')]", ".//*[contains(text(),'Trust')]"]:
                    try:
                        owner_name = card.find_element(By.XPATH, path).text.strip()
                        break
                    except:
                        continue

                # Status
                try:
                    status_el = card.find_element(By.XPATH, ".//*[contains(@class,'status') or contains(text(),'Lead') or contains(text(),'Added')]")
                    status = status_el.text.strip()
                except:
                    status = ""

                # Estimated value
                try:
                    value_el = card.find_element(By.XPATH, ".//*[contains(text(), '$')]")
                    est_value = value_el.text.strip()
                except:
                    est_value = ""

                # ✅ Clean structured record
                if full_address:
                    prop = {
                        "Property Address": full_address,
                        "Owner Name": owner_name or "Unknown",
                        "Status": status,
                        "Estimated Value": est_value
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

    # ✅ Final cleanup before returning
    valid_properties = [p for p in properties if isinstance(p, dict) and any(p.values())]
    if valid_properties:
        print(f"🧠 Sample scraped record: {valid_properties[0]}")
    else:
        print("⚠️ No valid property data scraped.")
    print(f"✅ Total scraped: {len(valid_properties)} valid properties")
    return valid_properties