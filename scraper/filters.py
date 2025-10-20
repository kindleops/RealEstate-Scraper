
try:
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.common.exceptions import TimeoutException
except Exception:
    # Minimal fallbacks so linters/IDEs won't complain when selenium isn't installed.
    # These fallbacks are no-op/simplified and intended only to avoid import errors;
    # real selenium must be installed to run the scraper against a browser.
    class By:
        XPATH = 'xpath'
        CSS_SELECTOR = 'css selector'
        ID = 'id'
        NAME = 'name'
        TAG_NAME = 'tag name'
        CLASS_NAME = 'class name'
        LINK_TEXT = 'link text'
        PARTIAL_LINK_TEXT = 'partial link text'

    class TimeoutException(Exception):
        pass

    class WebDriverWait:
        def __init__(self, driver, timeout):
            self.driver = driver
            self.timeout = timeout

        def until(self, method):
            # Basic fallback: attempt once and raise TimeoutException to mimic behavior.
            result = method(self.driver)
            if result:
                return result
            raise TimeoutException()

    class EC:
        @staticmethod
        def element_to_be_clickable(locator):
            def _predicate(driver):
                # Fallback predicate always returns False to trigger TimeoutException if used.
                return False
            return _predicate

import time

def apply_quick_filters(driver, filters):
    print(f"🎯 Applying quick filters: {filters}")
    for label in filters:
        try:
            filter_button = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.XPATH, f"//button[contains(., '{label}')]"))
            )
            filter_button.click()
            print(f"✅ Applied quick filter: {label}")
            time.sleep(1)
        except TimeoutException:
            print(f"⚠️ Quick filter not found: {label}")

def open_advanced_filters(driver):
    try:
        more_button = WebDriverWait(driver, 5).until(
            EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'More')]"))
        )
        more_button.click()
        print("✅ Opened advanced filters panel")
        time.sleep(1)
        return True
    except TimeoutException:
        print("❌ Could not open advanced filters")
        return False

def apply_advanced_filters(driver, advanced_filters):
    if not open_advanced_filters(driver):
        return

    for label in advanced_filters:
        try:
            checkbox = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.XPATH, f"//label[contains(., '{label}')]"))
            )
            checkbox.click()
            print(f"✅ Enabled advanced filter: {label}")
            time.sleep(0.5)
        except TimeoutException:
            print(f"⚠️ Advanced filter not found: {label}")

    try:
        apply_btn = WebDriverWait(driver, 5).until(
            EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'Apply')]"))
        )
        apply_btn.click()
        print("✅ Applied all advanced filters")
    except TimeoutException:
        print("❌ Could not click 'Apply' for advanced filters")
