from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, ElementClickInterceptedException
import time

def search_zip(driver, zip_code):
    print(f"\n🔍 Searching ZIP: {zip_code}")
    zip_code = str(zip_code).strip()

    # Scroll to top for safety
    try:
        driver.execute_script("window.scrollTo(0, 0);")
    except:
        pass

    # Find search input
    search_input = None
    selectors = [
        '//input[contains(@placeholder, "Search")]',
        '//input[@type="search"]',
        '//input[@role="searchbox"]'
    ]
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

    # Type ZIP
    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", search_input)
    search_input.click()
    search_input.send_keys(Keys.CONTROL, 'a')
    search_input.send_keys(Keys.BACKSPACE)
    search_input.send_keys(zip_code)
    print(f"✏️ Typed ZIP {zip_code} into search field")

    # Wait for dropdown and try to click suggestion
    try:
        suggestion_xpath = f"//div[contains(@class,'autocomplete')]//*[contains(text(), '{zip_code}')]"
        suggestion = WebDriverWait(driver, 5).until(
            EC.element_to_be_clickable((By.XPATH, suggestion_xpath))
        )
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", suggestion)
        time.sleep(0.5)
        try:
            suggestion.click()
        except ElementClickInterceptedException:
            driver.execute_script("arguments[0].click();", suggestion)
        print(f"🖱️ Clicked suggestion for ZIP {zip_code}")
    except TimeoutException:
        print("⚠️ No suggestion dropdown visible, pressing Enter instead")
        search_input.send_keys(Keys.ENTER)

    # Wait for property list to load
    sidebar_selector = "//div[contains(@class, 'deal-scroll')]//div[contains(@class,'deal-wrapper') or contains(@class,'property-card')]"
    try:
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.XPATH, sidebar_selector))
        )
        print(f"✅ Properties loaded successfully for ZIP {zip_code}")
        return True
    except TimeoutException:
        print(f"⚠️ No property cards appeared for ZIP {zip_code}")
        driver.save_screenshot(f"no_results_{zip_code}.png")
        return False
