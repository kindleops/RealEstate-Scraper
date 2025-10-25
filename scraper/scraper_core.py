#!/usr/bin/env python3
# ==========================================================
# 🚀 DealMachine AI Scraper Core
# Elite-tier property intelligence scraper with Airtable sync
# ==========================================================

from __future__ import annotations

import csv
import json
import random
import re
import time
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

from airtable_utils.router import route_and_upload

from selenium.common.exceptions import (
    InvalidSessionIdException,
    NoSuchElementException,
    StaleElementReferenceException,
    TimeoutException,
)
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

# --- Quick Filter Presets -----------------------------------------------
DEFAULT_FILTERS: List[str] = [
    "Vacant",
    "Absentee",
    "High Equity",
    "Owner Occupied",
    "Probate",
    "Pre-Foreclosure",
]

PROPERTY_CARD_SELECTOR = (
    "//div[contains(@class,'deal-scroll')]"
    "//div[contains(@class,'deal-wrapper') or contains(@class,'property-card')]"
)
CARD_CSS_SELECTORS: List[str] = [
    "div[data-testid='property-card']",
    "div.property-card",
    "div.card-property",
]
CARD_FALLBACK_XPATH = "//div[contains(@class,'property-card') or contains(., 'Est. Value')]"

PROPERTY_MODAL_SELECTOR = "//div[contains(@class,'property-details')]"
MODAL_LOCATORS: List[str] = [
    PROPERTY_MODAL_SELECTOR,
    "//div[@data-testid='property-modal']",
    "//div[contains(@class,'ReactModal__Content')]",
    "//div[contains(@class,'modal') and contains(@class,'open')]",
    "//div[contains(@role,'dialog') and (.//h1 or .//h2)]",
]

CLOSE_BUTTON_LOCATORS: List[str] = [
    "//button[contains(@aria-label,'close')]",
    "//button[contains(.,'Close')]",
    "//div[contains(@class,'modal')]//button[contains(@class,'close')]",
    "//div[contains(@class,'ReactModal__Content')]//button[contains(@class,'close')]",
]

OVERLAY_LOCATORS: List[str] = [
    "//div[contains(@class,'modal-backdrop')]",
    "//div[contains(@class,'ReactModal__Overlay')]",
]

FILTER_TOGGLE_LOCATORS: List[str] = [
    "//button[contains(@class,'quick-filter')]",
    "//button[contains(@class,'filters')]",
    "//button[contains(.,'Filters')]",
    "//button[contains(.,'Quick Filters')]",
]

FILTER_CONTAINER_LOCATORS: List[str] = [
    "//div[contains(@class,'quick-filters') and not(contains(@style,'display: none'))]",
    "//div[contains(@class,'filters-panel') and not(contains(@style,'display: none'))]",
    "//div[contains(@class,'modal')]//div[contains(@class,'filters') and contains(@class,'open')]",
    "//div[contains(@class,'ReactModal__Content')]//div[contains(@class,'filters')]",
]

OVERLAY_BLOCKERS: List[str] = [
    ".ReactModal__Overlay",
    ".deal-overlay",
    ".mapboxgl-canvas",
    ".mapboxgl-control-container",
]

ADDRESS_REGEX = re.compile(r"\d{3,5}\s+\w")

# -------------------------------------------------------------------------
# 🧠 Filter & Utility Layer
# -------------------------------------------------------------------------

def apply_niche_filters(driver, filters: Optional[Iterable[str]] = None, pause: float = 1.2) -> None:
    """Apply DealMachine quick filters."""
    labels = list(filters or DEFAULT_FILTERS)
    if not labels:
        return
    print("🧭 Applying quick filters...")
    _dismiss_screen_overlays(driver)

    container = _locate_filter_container(driver)
    if container is None:
        _toggle_filters_panel(driver)
        container = _locate_filter_container(driver, timeout=8)

    for label in labels:
        if container is None or not container.is_displayed():
            container = _locate_filter_container(driver, timeout=4)
            if container is None:
                print(f"⚠️ Filter container unavailable for '{label}'.")
                continue
        try:
            button = _find_filter_button(container, label)
            if button is None:
                print(f"⚠️ Filter not found: {label}")
                continue
            driver.execute_script("arguments[0].scrollIntoView({block:'center'});", button)
            driver.execute_script("arguments[0].click();", button)
            print(f"✅ Applied filter: {label}")
            time.sleep(pause)
        except StaleElementReferenceException:
            container = None
        except Exception as exc:
            print(f"⚠️ Error applying filter '{label}': {exc}")


def _dismiss_screen_overlays(driver) -> List[str]:
    script = """
    const selectors = arguments[0];
    const handled = [];
    selectors.forEach((sel) => {
        document.querySelectorAll(sel).forEach((el) => {
            const style = window.getComputedStyle(el);
            if (!style) return;
            const pointer = style.pointerEvents;
            if (pointer && pointer !== 'none') {
                el.dataset.__seleniumPointerEvents = pointer;
                el.style.pointerEvents = 'none';
                handled.push(sel);
            }
        });
    });
    return handled;
    """
    try:
        return driver.execute_script(script, OVERLAY_BLOCKERS) or []
    except Exception:
        return []


def _locate_filter_container(driver, timeout: float = 5.0):
    for locator in FILTER_CONTAINER_LOCATORS:
        try:
            container = WebDriverWait(driver, timeout).until(
                EC.presence_of_element_located((By.XPATH, locator))
            )
            if container and container.is_displayed():
                return container
        except Exception:
            continue
    return None


def _toggle_filters_panel(driver) -> None:
    for locator in FILTER_TOGGLE_LOCATORS:
        try:
            button = driver.find_element(By.XPATH, locator)
            if button.is_displayed():
                driver.execute_script("arguments[0].click();", button)
                time.sleep(0.6)
                return
        except Exception:
            continue


def _find_filter_button(container, label: str):
    normalized = label.strip().lower()
    xpaths = [
        f".//button[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{normalized}')]",
        f".//div[contains(@role,'option') and contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{normalized}')]",
    ]
    for xpath in xpaths:
        try:
            button = container.find_element(By.XPATH, xpath)
            if button.is_displayed():
                return button
        except NoSuchElementException:
            continue
    return None


# -------------------------------------------------------------------------
# 🏠 Property Scraping Core
# -------------------------------------------------------------------------

def _get_property_cards(driver) -> List[Any]:
    for selector in CARD_CSS_SELECTORS:
        cards = driver.find_elements(By.CSS_SELECTOR, selector)
        cards = [card for card in cards if card.is_displayed()]
        if cards:
            return cards
    cards = driver.find_elements(By.XPATH, CARD_FALLBACK_XPATH)
    return [card for card in cards if card.is_displayed()]


def _extract_address(lines: List[str], card) -> str:
    for line in lines:
        if ADDRESS_REGEX.search(line):
            return line
    try:
        text = (
            card.find_element(By.XPATH, ".//*[contains(@class,'address') or contains(text(), ', ')]")
            .text.strip()
        )
        return text if ADDRESS_REGEX.search(text) else ""
    except NoSuchElementException:
        return ""


def _extract_owner(lines: List[str]) -> str:
    for line in lines:
        if any(tag in line for tag in ("LLC", "Trust", "Inc", "Corp", "Properties", "Estates")) or (
            len(line.split()) <= 3 and line.istitle()
        ):
            return line
    return ""


def _extract_value(lines: List[str]) -> str:
    for line in lines:
        text = line.lower()
        if "$" in line or "value" in text or "est." in text:
            return line
    return ""


def _extract_tags(lines: List[str], card) -> List[str]:
    tags = [
        line
        for line in lines
        if any(keyword in line.lower() for keyword in ("vacant", "absentee", "lead", "owner occ", "high equity"))
    ]
    elements = card.find_elements(
        By.XPATH, ".//*[contains(@class,'chip') or contains(@class,'tag') or contains(@class,'badge')]"
    )
    for element in elements:
        text = element.text.strip()
        if text and text not in tags:
            tags.append(text)
    return tags


def _deep_scrape_card(driver, card, address: str, retry_count: int) -> Tuple[Dict[str, Any], int]:
    """
    Deep scrape a property card by opening its modal and extracting additional details.
    Returns a tuple of (scraped_data_dict, retry_count).
    """
    try:
        driver.execute_script("arguments[0].scrollIntoView({block:'center'});", card)
        driver.execute_script("arguments[0].click();", card)
        time.sleep(1.5)
        
        # Wait for modal to appear
        modal = None
        for locator in MODAL_LOCATORS:
            try:
                modal = WebDriverWait(driver, 5).until(
                    EC.presence_of_element_located((By.XPATH, locator))
                )
                if modal and modal.is_displayed():
                    break
            except Exception:
                continue
        
        if not modal:
            return {}, retry_count
        
        # Extract modal content
        modal_text = modal.text.strip()
        lines = [ln.strip() for ln in modal_text.split("\n") if ln.strip()]
        
        data = {
            "Property Address": address,
            "Owner Name": _extract_owner(lines),
            "Estimated Value": _extract_value(lines),
            "Status": ", ".join(_extract_tags(lines, modal)),
        }
        
        # Close modal
        for locator in CLOSE_BUTTON_LOCATORS:
            try:
                close_btn = driver.find_element(By.XPATH, locator)
                if close_btn.is_displayed():
                    driver.execute_script("arguments[0].click();", close_btn)
                    time.sleep(0.5)
                    break
            except Exception:
                continue
        
        return data, retry_count
        
    except Exception as e:
        print(f"⚠️ Deep scrape failed for {address}: {e}")
        return {}, retry_count


# -------------------------------------------------------------------------
# 💾 Airtable Upload Layer
# -------------------------------------------------------------------------

def save_property_to_airtable(scraped_record: Dict[str, Any]) -> None:
    """Upload a single property record to Airtable via router.py."""
    address = scraped_record.get("Property Address") or scraped_record.get("Full Address")
    print(f"📦 Uploading: {address or 'Unknown Address'}")

    try:
        result = route_and_upload(scraped_record)
        if isinstance(result, dict):
            print(f"📤 Upload result: {json.dumps(result, indent=2)}")
        else:
            print(f"📤 Upload complete: {result}")
    except Exception as e:
        print(f"❌ Upload failed for {address}: {e}")


def upload_all_properties(properties: List[Dict[str, Any]], delay: float = 0.4) -> None:
    """Batch upload with delay to prevent Airtable API throttling."""
    total = len(properties)
    if not total:
        print("⚠️ No properties to upload.")
        return

    print(f"🚀 Starting batch upload for {total} records...")
    uploaded, failed = 0, 0

    for i, record in enumerate(properties, 1):
        try:
            save_property_to_airtable(record)
            uploaded += 1
        except Exception as exc:
            print(f"⚠️ Upload error for record #{i}: {exc}")
            failed += 1

        time.sleep(delay)

    print(f"✅ Upload Summary → Uploaded: {uploaded} | Failed: {failed}")


# -------------------------------------------------------------------------
# 🔁 Scraper Execution
# -------------------------------------------------------------------------

def scroll_and_scrape_properties(
    driver,
    max_scrolls: int = 100,           # Extended scroll depth
    wait_time: float = 1.0,           # Faster scroll rhythm
    deep_scrape: bool = True,
    auto_filters: bool = True,
    modal_limit: int = 250,           # Higher modal cap
    restart_callback=None,
    save_path: str = "data/scraped_properties.json",
    auto_quit: bool = False,
    source_zip: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    ⚡️ High-Yield Mode:
    Adaptive scrolling + deduplication for massive property extraction.
    """

    print("🚀 [High-Yield Mode] Starting extended property scraping sequence...")
    properties: List[Dict[str, Any]] = []
    seen_addresses = set()
    output_path = Path(save_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    def _persist_batch(records: List[Dict[str, Any]]) -> None:
        if not records:
            return
        output_path.write_text(json.dumps(records, indent=2, default=str), encoding="utf-8")

    try:
        if auto_filters:
            apply_niche_filters(driver)

        WebDriverWait(driver, 25).until(lambda d: len(_get_property_cards(d)) > 0)
        print("✅ Property cards detected.")

        stable_count = 0
        last_total = 0
        modal_scraped = 0

        for scroll_index in range(max_scrolls):
            cards = _get_property_cards(driver)
            current_total = len(cards)
            print(f"📍 Scroll {scroll_index+1}: {current_total} cards visible.")

            # Stop when no new cards appear twice in a row
            if current_total == last_total:
                stable_count += 1
                if stable_count >= 2:
                    print("🔚 Detected end of list (no new cards twice).")
                    break
            else:
                stable_count = 0
            last_total = current_total

            for card in cards:
                try:
                    card_text = card.text.strip()
                    if not card_text:
                        continue
                    lines = [ln.strip() for ln in card_text.split("\n") if ln.strip()]
                    address = _extract_address(lines, card)
                    owner = _extract_owner(lines)
                    value = _extract_value(lines)
                    tags = _extract_tags(lines, card)

                    # Skip duplicates
                    if address in seen_addresses:
                        continue
                    seen_addresses.add(address)

                    record = {
                        "Property Address": address or "",
                        "Owner Name": (owner or "Unknown").strip(),
                        "Estimated Value": value.strip() if value else "",
                        "Status": ", ".join(tags) if tags else "",
                        "Source ZIP": source_zip or "",
                    }

                    # Optional deep modal scrape
                    if deep_scrape and modal_scraped < modal_limit:
                        layered, _ = _deep_scrape_card(driver, card, address, 0)
                        modal_scraped += 1
                        if layered:
                            record.update({k: layered.get(k, record.get(k, "")) for k in layered})

                    properties.append(record)

                except Exception as e:
                    print(f"⚠️ Error parsing card: {e}")
                    continue

            # Scroll sidebar dynamically
            driver.execute_script(
                "const sidebar=document.querySelector('.deal-scroll');"
                "if(sidebar){sidebar.scrollBy(0, sidebar.scrollHeight);}"
            )
            time.sleep(wait_time)

        cleaned = [p for p in properties if isinstance(p, dict) and any(p.values())]
        print(f"✅ [High-Yield] Scraped {len(cleaned)} unique property records.")
        if cleaned:
            print(f"🧠 Sample record:\n{json.dumps(cleaned[0], indent=2)}")
            upload_all_properties(cleaned)
        else:
            print("⚠️ No valid property data scraped.")

        return cleaned

    finally:
        _persist_batch(properties)
        if auto_quit:
            try:
                driver.quit()
            except Exception:
                pass