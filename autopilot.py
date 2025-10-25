# ============================================
# 🤖 DealMachine Autopilot — AI Market Executor
# ============================================

import time
from scraper.login_utils import get_driver, login
from scraper.zip_search import search_zip
from scraper.scraper_core import scroll_and_scrape_properties
from config.filters_engine import apply_quick_filters, apply_advanced_filters
from airtable_utils.router import batch_upload  # unified router
from config.zips import MARKETS  # all elite markets

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


def autopilot_run():
    print("🚀 Launching DealMachine Autopilot...\n")
    driver = get_driver()
    if not driver:
        print("❌ Failed to initialize driver.")
        return

    # 🔐 Login sequence
    if not login(driver):
        print("❌ Login failed.")
        driver.quit()
        return

    # 🌎 Iterate through all elite markets and ZIPs
    for market, zips in MARKETS.items():
        print(f"\n🌆 Starting Market: {market}")
        for zip_code in zips:
            print(f"\n===== Processing ZIP: {zip_code} =====")

            if not search_zip(driver, zip_code):
                print(f"[!] Skipping ZIP {zip_code} due to search failure")
                continue

            # 🎯 Apply Filters (you can expand this per market)
            quick_filters = ["Vacant", "High Equity", "Absentee"]
            advanced_filters = ["Pre-Foreclosure", "Probate"]

            # Apply quick filters
            if quick_filters:
                apply_quick_filters(driver, quick_filters)
                if len(quick_filters) > 1:
                    try:
                        match_button = WebDriverWait(driver, 5).until(
                            EC.element_to_be_clickable(
                                (By.XPATH, "//button[contains(., 'Apply All That Match')]")
                            )
                        )
                        match_button.click()
                        print("✅ Clicked 'Apply All That Match'")
                        time.sleep(1)
                    except Exception:
                        print("⚠️ 'Apply All That Match' button not found")

            # Apply advanced filters
            if advanced_filters:
                apply_advanced_filters(driver, advanced_filters)

            # 🧠 Scrape property data
            properties = scroll_and_scrape_properties(driver, source_zip=zip_code)

            if not properties:
                print(f"⚠️ No properties found for ZIP {zip_code}")
                continue

            # ☁️ Upload all scraped properties
            print(f"📤 Uploading {len(properties)} scraped properties to Airtable...")
            try:
                batch_upload(properties)
                print(f"✅ Uploaded batch for ZIP {zip_code}")
            except Exception as e:
                print(f"⚠️ Upload error for {zip_code}: {e}")

            # 🌙 Optional rest interval between ZIPs
            time.sleep(5)

        print(f"🏁 Completed Market: {market}")
        time.sleep(10)

    driver.quit()
    print("\n✅ Autopilot completed for all markets and ZIPs.")


if __name__ == "__main__":
    autopilot_run()