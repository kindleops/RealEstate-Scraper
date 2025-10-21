from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    NoSuchElementException,
    StaleElementReferenceException,
    TimeoutException,
)
import time

def scroll_and_scrape_properties(driver, max_scrolls=25, wait_time=1.25):
    """
    Scrolls through DealMachine's sidebar and scrapes all visible property cards
    with full hierarchical parsing (address, owner, status tags, estimated value, etc.).
    Returns a list of property dictionaries.
    """

    print("🌀 Scrolling and scraping property cards...")

    # Main property wrapper in sidebar
    property_selector = "//div[contains(@class,'deal-scroll')]//div[contains(@class,'deal-wrapper') or contains(@class,'property-card')]"
    properties = []

    # Wait for first batch of cards
    try:
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.XPATH, property_selector))
        )
        print("✅ Property cards detected in sidebar")
    except TimeoutException:
        print("⚠️ No property cards found — skipping.")
        return properties

    last_count = 0
    for scroll_index in range(max_scrolls):
        cards = driver.find_elements(By.XPATH, property_selector)
        print(f"📍 Found {len(cards)} cards after scroll {scroll_index + 1}")

        for idx, card in enumerate(cards, 1):
            try:
                # Try scraping child layers instead of raw text
                address = extract_address(card)
                owner = extract_owner(card)
                value = extract_value(card)
                tags = extract_tags(card)

                # Fallback if not found via elements
                if not address or not value or not owner:
                    raw_text = card.text.strip()
                    if raw_text:
                        address = address or extract_address_from_text(raw_text)
                        owner = owner or extract_owner_from_text(raw_text)
                        value = value or extract_value_from_text(raw_text)
                        tags = tags or extract_tags_from_text(raw_text)

                if address:
                    properties.append({
                        "Property Address": address.strip(),
                        "Owner Name": (owner or "Unknown").strip(),
                        "Status": ", ".join(tags) if tags else "",
                        "Estimated Value": value.strip() if value else "",
                    })

            except (NoSuchElementException, StaleElementReferenceException) as e:
                print(f"⚠️ Skipped card #{idx} due to DOM update: {type(e).__name__}")
                continue

        # Scroll sidebar to load more cards
        driver.execute_script("""
            const sidebar = document.querySelector('.deal-scroll');
            if (sidebar) sidebar.scrollBy(0, sidebar.scrollHeight);
        """)
        time.sleep(wait_time)

        # Stop when no new cards load
        if len(cards) == last_count:
            print("🔚 Reached end of sidebar — no new cards.")
            break
        last_count = len(cards)

    # Cleanup
    valid_props = [p for p in properties if isinstance(p, dict) and p.get("Property Address")]
    print(f"✅ Total scraped: {len(valid_props)} properties")
    if valid_props:
        print(f"🧠 Sample scraped record: {valid_props[0]}")
    else:
        print("⚠️ No valid property data extracted.")
    return valid_props


# ==============================================================
# 🧩 Layered Extraction Helpers
# ==============================================================

def extract_address(card):
    try:
        addr_el = card.find_element(By.XPATH, ".//*[contains(@class, 'address') or contains(text(), ', ')]")
        return addr_el.text.strip()
    except NoSuchElementException:
        return ""

def extract_owner(card):
    try:
        owner_el = card.find_element(By.XPATH, ".//*[contains(@class, 'owner') or contains(text(), 'LLC') or contains(text(), 'Trust')]")
        return owner_el.text.strip()
    except NoSuchElementException:
        return ""

def extract_value(card):
    try:
        val_el = card.find_element(By.XPATH, ".//*[contains(text(), '$') or contains(text(), 'Est.') or contains(text(), 'Value')]")
        return val_el.text.strip()
    except NoSuchElementException:
        return ""

def extract_tags(card):
    tags = []
    tag_elements = card.find_elements(By.XPATH, ".//*[contains(@class,'chip') or contains(@class,'tag') or contains(@class,'badge')]")
    for t in tag_elements:
        txt = t.text.strip()
        if txt:
            tags.append(txt)
    return tags


# ==============================================================
# 🧠 Text Parsing Fallbacks
# ==============================================================

def extract_address_from_text(text):
    for line in text.split("\n"):
        lower = line.lower()
        if ("," in line and any(state in lower for state in ["fl", "tx", "ca", "ny", "az", "nv", "il"])) or any(
            s in lower for s in ["st", "ave", "rd", "dr", "blvd", "ln", "court"]
        ):
            return line
    return ""

def extract_owner_from_text(text):
    for line in text.split("\n"):
        if any(x in line for x in ["LLC", "Trust", "Inc", "Corp", "Properties", "Estates"]) or (len(line.split()) <= 3 and line.istitle()):
            return line
    return ""

def extract_value_from_text(text):
    for line in text.split("\n"):
        if "$" in line or "est." in line.lower() or "value" in line.lower():
            return line
    return ""

def extract_tags_from_text(text):
    tags = []
    for line in text.split("\n"):
        if any(tag in line.lower() for tag in ["vacant", "absentee", "lead", "owner occ", "high equity", "rental"]):
            tags.append(line)
    return tags
