from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, ElementClickInterceptedException
import time

def search_zip(driver, zip_code):
    print(f"\n🔍 Searching ZIP: {zip_code}")
    zip_code = str(zip_code).strip()

    def wait_for_overlay_to_clear():
        try:
            WebDriverWait(driver, 10).until_not(
                EC.presence_of_element_located((By.XPATH, "//div[contains(@style,'position: fixed') and contains(@style,'width: 100%')]"))
            )
            print("🧹 Overlay cleared, ready to click")
        except TimeoutException:
            print("⚠️ Overlay still visible, proceeding carefully")

    # Clear old searches
    try:
        clear_buttons = driver.find_elements(By.XPATH, "//button[contains(@aria-label,'clear') or contains(@class,'clear')]")
        for b in clear_buttons:
            driver.execute_script("arguments[0].click();", b)
            time.sleep(0.3)
    except Exception:
        pass

    # Scroll to top
    driver.execute_script("window.scrollTo(0, 0);")

    # Find search bar
    search_input = None
    for selector in [
        '//input[contains(@placeholder, "Search")]',
        '//input[@type="search"]',
        '//input[@role="searchbox"]'
    ]:
        try:
            search_input = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, selector))
            )
            break
        except TimeoutException:
            continue

    if not search_input:
        print("❌ Could not locate search input.")
        return False

    # Type ZIP
    wait_for_overlay_to_clear()
    driver.execute_script("arguments[0].scrollIntoView({block:'center'});", search_input)
    driver.execute_script("arguments[0].click();", search_input)
    time.sleep(0.3)
    search_input.send_keys(Keys.CONTROL, 'a')
    search_input.send_keys(Keys.BACKSPACE)
    search_input.send_keys(zip_code)
    print(f"✏️ Typed ZIP {zip_code}")

    # Try dropdown selection
    suggestion_xpath = f"//*[contains(text(), '{zip_code}') and (contains(@class,'autocomplete') or contains(@class,'menu') or name()='div')]"
    try:
        suggestion = WebDriverWait(driver, 3).until(
            EC.element_to_be_clickable((By.XPATH, suggestion_xpath))
        )
        driver.execute_script("arguments[0].scrollIntoView({block:'center'});", suggestion)
        time.sleep(0.3)
        try:
            suggestion.click()
        except ElementClickInterceptedException:
            driver.execute_script("arguments[0].click();", suggestion)
        print(f"🖱️ Clicked dropdown suggestion for {zip_code}")
    except TimeoutException:
        print("⚠️ No dropdown suggestion found — using arrow + enter fallback")
        search_input.send_keys(Keys.ARROW_DOWN)
        search_input.send_keys(Keys.ENTER)

    # Wait for overlay to vanish before reading properties
    wait_for_overlay_to_clear()

    # Wait for property sidebar
    sidebar_selector = "//div[contains(@class,'deal-scroll')]//div[contains(@class,'deal-wrapper') or contains(@class,'property-card')]"
    try:
        WebDriverWait(driver, 25).until(
            EC.presence_of_element_located((By.XPATH, sidebar_selector))
        )
        print(f"✅ Properties loaded for ZIP {zip_code}")
        return True
    except TimeoutException:
        print(f"⚠️ No property cards appeared for ZIP {zip_code}")
        driver.save_screenshot(f"no_results_{zip_code}.png")
        return False
