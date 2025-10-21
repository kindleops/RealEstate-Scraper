from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
from selenium.common.exceptions import NoSuchElementException, StaleElementReferenceException

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
                text = card.text.strip()
                if not text:
                    continue

                # Split lines for flexible pattern parsing
                lines = [line.strip() for line in text.split("\n") if line.strip()]

                full_address = ""
                owner_name = ""
                status = ""
                est_value = ""

                for line in lines:
                    lower = line.lower()

                    # --- Detect address ---
                    if ("," in line and any(state in lower for state in ["fl", "tx", "ca", "ny", "az", "nv", "il"])) or "street" in lower or "ave" in lower:
                        full_address = line

                    # --- Detect owner ---
                    elif any(x in line for x in ["LLC", "Trust", "Inc", "Corp", "Properties", "Estates"]) or (len(line.split()) <= 3 and line.istitle()):
                        owner_name = line

                    # --- Detect value ---
                    elif "$" in line or "est." in lower or "value" in lower:
                        est_value = line

                    # --- Detect status/tag ---
                    elif any(x in lower for x in ["lead", "added", "vacant", "absentee", "high equity", "owner occ"]):
                        status = line

                # Fallback extraction if fields remain empty
                if not full_address:
                    try:
                        address_el = card.find_element(By.XPATH, ".//*[contains(text(), ', ')]")
                        full_address = address_el.text.strip()
                    except NoSuchElementException:
                        pass

                prop = {
                    "full_address": full_address or None,
                    "owner_name": owner_name or None,
                    "status": status or None,
                    "est_value": est_value or None
                }

                # Filter out empties
                if any(prop.values()) and prop not in properties:
                    properties.append(prop)

            except (NoSuchElementException, StaleElementReferenceException):
                continue

        # Scroll sidebar to load more
        driver.execute_script("""
            const sidebar = document.querySelector('.deal-scroll');
            if (sidebar) sidebar.scrollBy(0, sidebar.scrollHeight);
        """)
        time.sleep(1.25)

        # Stop if no new cards load
        if len(cards) == last_count:
            print("🔚 Reached end of sidebar — no new cards.")
            break
        last_count = len(cards)

    print(f"✅ Total scraped: {len(properties)} properties")
    return properties