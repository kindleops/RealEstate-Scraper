"""
filters_engine.py
Elite-tier unified filter executor for DealMachine automation
"""

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, ElementClickInterceptedException
import time


# ---------------------------------------------
# 🎯 Core Quick Filter Logic
# ---------------------------------------------
def apply_quick_filters(driver, filters):
    print(f"🎯 Applying quick filters: {list(filters.keys()) if isinstance(filters, dict) else filters}")
    for label in filters:
        try:
            element = WebDriverWait(driver, 8).until(
                EC.element_to_be_clickable((By.XPATH, f"//*[contains(text(), '{label}')]"))
            )
            try:
                element.click()
            except ElementClickInterceptedException:
                driver.execute_script("arguments[0].click();", element)
            print(f"✅ Applied quick filter: {label}")
            time.sleep(0.5)
        except TimeoutException:
            print(f"⚠️ Quick filter not found: {label}")
            continue


# ---------------------------------------------
# ⚙️ Advanced Filter Panel Handling
# ---------------------------------------------
def open_advanced_filters(driver):
    """Attempt to open advanced filters panel."""
    try:
        more_button = WebDriverWait(driver, 6).until(
            EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'More')] | //div[contains(text(),'More')]"))
        )
        driver.execute_script("arguments[0].click();", more_button)
        print("✅ Advanced filters panel opened")
        time.sleep(1)
        return True
    except TimeoutException:
        print("❌ Could not open advanced filters")
        return False


# ---------------------------------------------
# 🧠 Apply Advanced Filters Dynamically
# ---------------------------------------------
def apply_advanced_filters(driver, advanced_filters):
    """Click all labels that match advanced filter names."""
    if not open_advanced_filters(driver):
        return

    for label, value in advanced_filters.items() if isinstance(advanced_filters, dict) else enumerate(advanced_filters):
        try:
            checkbox = WebDriverWait(driver, 6).until(
                EC.element_to_be_clickable((By.XPATH, f"//label[contains(., '{label}')]"))
            )
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", checkbox)
            driver.execute_script("arguments[0].click();", checkbox)
            print(f"✅ Enabled advanced filter: {label} = {value}")
            time.sleep(0.3)
        except TimeoutException:
            print(f"⚠️ Advanced filter not found: {label}")

    try:
        apply_btn = WebDriverWait(driver, 6).until(
            EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'Apply')]"))
        )
        driver.execute_script("arguments[0].click();", apply_btn)
        print("✅ Applied all advanced filters")
    except TimeoutException:
        print("❌ Could not click 'Apply' button")


# ---------------------------------------------
# 🚀 Unified Runner
# ---------------------------------------------
def run_filters(driver, filter_set):
    """Apply both quick and advanced filters in a unified flow."""
    if not filter_set:
        print("⚠️ No filters provided for this search.")
        return

    quick_keys = [k for k in filter_set.keys() if filter_set[k] is True] if isinstance(filter_set, dict) else filter_set

    print("🧭 Starting filter sequence...")
    apply_quick_filters(driver, quick_keys)
    apply_advanced_filters(driver, filter_set)
    print("✅ Completed filter sequence.")