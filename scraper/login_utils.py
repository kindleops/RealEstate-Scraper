from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.action_chains import ActionChains
import os
import time
from dotenv import load_dotenv

# === Load environment variables ===
load_dotenv()
EMAIL = os.getenv("DEALMACHINE_EMAIL")
PASSWORD = os.getenv("DEALMACHINE_PASSWORD")
BRAVE_PATH = os.getenv("BRAVE_PATH", "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser")


def get_driver():
    """
    Launch a Brave-based Selenium WebDriver using the system ChromeDriver (v141+).
    Ensures smooth integration and no version mismatch.
    """
    print("🚀 Initializing Brave Selenium driver...")

    options = Options()
    options.binary_location = BRAVE_PATH
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--ignore-certificate-errors")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)

    # ✅ Use system ChromeDriver that matches Brave v141+
    driver_path = "/usr/local/bin/chromedriver"
    print(f"🔍 Using ChromeDriver from: {driver_path}")

    service = Service(driver_path)

    try:
        driver = webdriver.Chrome(service=service, options=options)
        driver.set_page_load_timeout(60)
        print("✅ Brave WebDriver initialized successfully")
        return driver
    except Exception as e:
        print(f"❌ Failed to initialize ChromeDriver: {e}")
        print("🧩 Tip: Ensure ChromeDriver v141+ is installed and linked via:")
        print("    brew install --cask chromedriver")
        print("    sudo ln -s /Applications/Chromedriver.app/Contents/MacOS/Chromedriver /usr/local/bin/chromedriver")
        raise


def login(driver):
    """Authenticate into DealMachine."""
    try:
        driver.get("https://app.dealmachine.com/login")
        print("[>] Opened DealMachine login page")
        time.sleep(2)

        # Email
        email_input = WebDriverWait(driver, 20).until(
            EC.visibility_of_element_located((By.XPATH, "//input[@placeholder='Email Address']"))
        )
        email_input.clear()
        email_input.send_keys(EMAIL)
        print("[+] Email entered")

        # Password
        password_input = WebDriverWait(driver, 10).until(
            EC.visibility_of_element_located((By.XPATH, "//input[@placeholder='Password']"))
        )
        password_input.clear()
        password_input.send_keys(PASSWORD)
        print("[+] Password entered")

        # Click “Continue With Email”
        login_button = WebDriverWait(driver, 15).until(
            EC.element_to_be_clickable((By.XPATH, "//div[text()='Continue With Email']"))
        )
        driver.execute_script("arguments[0].scrollIntoView(true);", login_button)
        time.sleep(0.5)
        try:
            login_button.click()
        except Exception:
            driver.execute_script("arguments[0].click();", login_button)
        print("[+] Clicked login button")

        # Wait for dashboard redirect
        WebDriverWait(driver, 25).until(
            lambda d: "login" not in d.current_url and "app.dealmachine.com" in d.current_url
        )
        print("[✅] Login successful")
        driver.save_screenshot("login_success.png")
        return True

    except TimeoutException:
        print("[!] Login timeout or error")
        driver.save_screenshot("login_error.png")
        return False