from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
import time

def search_zip(driver, zip_code):
    print(f"\n🔍 Searching ZIP: {zip_code}")
    zip_code = str(zip_code).strip()

    try:
        # Make sure we’re at the top of the page
        driver.execute_script("window.scrollTo(0, 0);")
        time.sleep(0.5)
    except:
        pass

    # Look for a visible search input
    selectors = [
        '//input[contains(@placeholder, "Search")]',
        '//input[@type="search"]',
        '//input[@role="searchbox"]',
        '//input[contains(@name, "search")]'
    ]
    search_input = None
    for selector in selectors:
        try:
            search_input = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, selector))
            )
            break
        except TimeoutException:
            continue

    if not search_input:
        print("❌ Search input not found.")
        return False

    # Clear and type ZIP
    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", search_input)
    search_input.click()
    search_input.send_keys(Keys.CONTROL, 'a')
    search_input.send_keys(Keys.BACKSPACE)
    search_input.send_keys(zip_code)
    print("✏️  ZIP typed into search field")
    time.sleep(0.8)

    # 🔍 Handle dropdown suggestion (DealMachine often shows “ZIP ###### - City”)
    try:
        suggestion = WebDriverWait(driver, 3).until(
            EC.element_to_be_clickable((By.XPATH, "//div[contains(@class, 'autocomplete') or contains(., '{}')]".format(zip_code)))
        )
        driver.execute_script("arguments[0].click();", suggestion)
        print("🖱️ Clicked ZIP suggestion dropdown")
    except TimeoutException:
        # Fallback: press Enter manually
        search_input.send_keys(Keys.ENTER)
        print("↩️ Pressed Enter to trigger search")

    # Wait for results to load
    sidebar_selector = "//div[contains(@class, 'deal-scroll')]//div[contains(@class, 'deal-wrapper') or contains(@class,'property-card')]"

    try:
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.XPATH, sidebar_selector))
        )
        print(f"✅ Properties loaded for ZIP {zip_code}")
        return True
    except TimeoutException:
        print(f"⚠️ No property cards appeared for ZIP {zip_code}")
        driver.save_screenshot(f"no_results_{zip_code}.png")
        return False
