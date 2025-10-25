#!/usr/bin/env python3
# ===============================================================
# 🧠 DealMachine Auto-Cycle Runner (Self-Healing Edition)
# ===============================================================

from __future__ import annotations
import random
import time
import traceback
from pathlib import Path

from config.zips import TARGET_ZIP_MAP
from scraper.scraper_core import scroll_and_scrape_properties
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import WebDriverException, TimeoutException
from webdriver_manager.chrome import ChromeDriverManager


# ---------------------------------------------------------------
# 🚀 Driver Initialization
# ---------------------------------------------------------------
def create_driver(headless: bool = True):
    """Create a new Chrome driver instance with robust options."""
    options = Options()
    options.add_argument("--disable-notifications")
    options.add_argument("--disable-infobars")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)
    if headless:
        options.add_argument("--headless=new")

    try:
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
        driver.set_page_load_timeout(60)
        return driver
    except Exception as e:
        print(f"❌ Failed to initialize Chrome: {e}")
        raise


# ---------------------------------------------------------------
# 🧠 Self-Healing Market Runner
# ---------------------------------------------------------------
def run_market_cycle(markets: dict, pause_between_zips: float = 6.0, max_retries: int = 3):
    """Run through all ZIPs across all markets, restarting driver when needed."""
    print("🚀 Starting self-healing auto-cycle scrape...\n")

    total_scraped = 0
    cycle_start = time.strftime("%Y-%m-%d %H:%M:%S")
    print(f"🕒 Session started at {cycle_start}\n")

    for market, zips in markets.items():
        print(f"🏙️ Now scraping market: {market} ({len(zips)} ZIPs)")
        for idx, zip_code in enumerate(zips, 1):
            retry = 0
            success = False
            while retry < max_retries and not success:
                try:
                    print(f"\n📍 [{market}] ZIP {zip_code} (Attempt {retry+1}/{max_retries})")
                    driver = create_driver(headless=True)
                    driver.get("https://dealmachine.com/app/map")

                    records = scroll_and_scrape_properties(
                        driver=driver,
                        max_scrolls=60,
                        wait_time=1.0,
                        deep_scrape=False,   # set True for full modal scraping
                        auto_filters=True,
                        modal_limit=0,
                        auto_quit=True,
                        source_zip=str(zip_code),
                    )

                    print(f"✅ Completed ZIP {zip_code} — {len(records)} records scraped.")
                    total_scraped += len(records)
                    success = True
                    time.sleep(random.uniform(pause_between_zips, pause_between_zips + 3))

                except (WebDriverException, TimeoutException) as e:
                    retry += 1
                    print(f"⚠️ Browser or timeout issue on ZIP {zip_code}: {e}")
                    traceback.print_exc()
                    try:
                        driver.quit()
                    except Exception:
                        pass
                    time.sleep(5)
                    if retry >= max_retries:
                        print(f"❌ Skipping ZIP {zip_code} after {max_retries} failed attempts.")
                        continue

                except Exception as e:
                    retry += 1
                    print(f"⚠️ Unexpected error on ZIP {zip_code}: {e}")
                    traceback.print_exc()
                    try:
                        driver.quit()
                    except Exception:
                        pass
                    time.sleep(5)
                    if retry >= max_retries:
                        print(f"❌ Skipping ZIP {zip_code} after repeated errors.")
                        continue

        print(f"🏁 Finished market {market}.\n")
        time.sleep(10)

    cycle_end = time.strftime("%Y-%m-%d %H:%M:%S")
    print(f"\n✅ Auto-cycle completed.")
    print(f"🕒 {cycle_start} → {cycle_end}")
    print(f"📦 Total scraped this session: {total_scraped:,} properties.\n")


# ---------------------------------------------------------------
# 🔁 Continuous 24/7 Loop
# ---------------------------------------------------------------
if __name__ == "__main__":
    while True:
        try:
            run_market_cycle(TARGET_ZIP_MAP, pause_between_zips=6.0)
            print("🌙 Cycle complete — sleeping 4 hours before next run...")
            time.sleep(4 * 60 * 60)

        except Exception as e:
            print(f"⚠️ Fatal error in main loop: {e}")
            traceback.print_exc()
            print("🧠 Restarting entire cycle in 2 minutes...")
            time.sleep(120)