from scraper.login_utils import get_driver, login
from scraper.zip_search import search_zip
from scraper.scraper_core import scroll_and_scrape_properties
from filters import apply_quick_filters
from airtable_utils.table_router import route_and_upload

# 🗺️ ZIPs to process — replace or import from your /markets files
ZIP_CODES = ["33147", "33127", "33054"]  # Example: Miami-Dade test set


def main():
    print("🚀 Starting DealMachine Scraper...\n")

    driver = get_driver()
    if not driver:
        print("[!] Driver failed to initialize")
        return

    try:
        # 1️⃣ Login
        if not login(driver):
            print("[!] Login failed")
            return

        # 2️⃣ Loop through ZIPs
        for zip_code in ZIP_CODES:
            print(f"\n===== Processing ZIP: {zip_code} =====")
            success = search_zip(driver, zip_code)

            if not success:
                print(f"[!] Skipping ZIP {zip_code} due to search failure")
                continue

            # 3️⃣ Apply filters (you can swap for advanced later)
            apply_quick_filters(driver, filters=["Vacant", "High Equity"])

            # 4️⃣ Scrape all sidebar property cards
            property_cards = scroll_and_scrape_properties(driver)

            if not property_cards:
                print(f"[!] No properties found in ZIP {zip_code}")
                continue

            # 5️⃣ Upload scraped properties to Airtable
            try:
                summary = route_and_upload(property_cards)
                print(
                    f"[✓] Completed ZIP: {zip_code} — Uploaded {summary['uploaded']} / {summary['total']}"
                )
            except Exception as e:
                print(f"⚠️ Upload failed for ZIP {zip_code}: {e}")

    finally:
        driver.quit()
        print("\n[✓] Driver closed\n✅ Scraper finished successfully.")


if __name__ == "__main__":
    main()
