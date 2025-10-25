# ============================================
# 🚀 DealMachine AI Scraper Runner (Production)
# ============================================

from scraper.login_utils import get_driver, login
from scraper.zip_search import search_zip
from scraper.scraper_core import scroll_and_scrape_properties
from config.filters_engine import apply_quick_filters
from airtable_utils.router import batch_upload  # ✅ unified router import
from config.zips import MARKETS

import time


def main():
    print("🚀 Starting DealMachine Scraper...\n")

    # ✅ Initialize the browser
    driver = get_driver()
    if not driver:
        print("[!] Driver failed to initialize")
        return

    try:
        # 1️⃣ Login
        if not login(driver):
            print("[!] Login failed — stopping execution.")
            return

        # 2️⃣ Loop through all configured markets & zips
        for market, zips in MARKETS.items():
            print(f"\n🌎 Market: {market}")
            for zip_code in zips:
                print(f"\n===== Processing ZIP: {zip_code} =====")
                success = search_zip(driver, zip_code)

                if not success:
                    print(f"[!] Skipping ZIP {zip_code} due to search failure.")
                    continue

                # 3️⃣ Apply quick filters (can later switch to advanced filter engine)
                apply_quick_filters(driver, filters=["Vacant", "High Equity", "Absentee"])

                # 4️⃣ Scrape properties in the current ZIP
                property_records = scroll_and_scrape_properties(driver, source_zip=zip_code)

                if not property_records:
                    print(f"[!] No properties found in ZIP {zip_code}")
                    continue

                # 5️⃣ Upload results via unified router
                try:
                    print("📦 Uploading batch to Airtable...")
                    batch_upload(property_records)
                    print(f"✅ Uploaded {len(property_records)} records for {zip_code}")
                except Exception as e:
                    print(f"⚠️ Upload failed for ZIP {zip_code}: {e}")

                # 🕐 Optional: brief delay between zips to avoid rate limiting
                time.sleep(5)

    finally:
        # Always close the browser
        driver.quit()
        print("\n[✓] Driver closed\n✅ Scraper finished successfully.")


if __name__ == "__main__":
    main()
