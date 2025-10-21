from __future__ import annotations

import json
import time
from typing import Any, Dict, Iterable, List, Optional

from selenium.common.exceptions import (
    NoSuchElementException,
    StaleElementReferenceException,
    TimeoutException,
)
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

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
PROPERTY_MODAL_SELECTOR = "//div[contains(@class,'property-details')]"


def apply_niche_filters(
    driver,
    filters: Optional[Iterable[str]] = None,
    pause: float = 1.2,
) -> None:
    """
    Apply a sequence of DealMachine quick filters.
    """

    filters = list(filters or DEFAULT_FILTERS)
    if not filters:
        return

    print("🧭 Applying quick filters...")
    for label in filters:
        try:
            button = WebDriverWait(driver, 6).until(
                EC.element_to_be_clickable((By.XPATH, f"//button[contains(., '{label}')]"))
            )
            driver.execute_script("arguments[0].click();", button)
            print(f"✅ Applied filter: {label}")
            time.sleep(pause)
        except TimeoutException:
            print(f"⚠️ Filter not found: {label}")
        except Exception as exc:  # pragma: no cover - defensive
            print(f"⚠️ Error applying filter '{label}': {exc}")


def _safe_json_preview(record: Dict[str, Any]) -> str:
    try:
        return json.dumps(record, indent=2, default=str)
    except TypeError:
        return str(record)


def _scrape_modal(driver) -> Dict[str, str]:
    """
    Scrape additional details from the property modal.
    """

    layered: Dict[str, str] = {
        "Equity %": "",
        "Mailing Address": "",
        "Last Sale Date": "",
        "Last Sale Price": "",
    }

    WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.XPATH, PROPERTY_MODAL_SELECTOR))
    )
    modal_text = driver.find_element(By.XPATH, PROPERTY_MODAL_SELECTOR).text
    lines = [line.strip() for line in modal_text.split("\n") if line.strip()]

    for line in lines:
        lower = line.lower()
        if "equity" in lower and "%" in line:
            layered["Equity %"] = line
        elif "mailing" in lower or ("address" in lower and "," in line):
            layered["Mailing Address"] = line
        elif any(keyword in lower for keyword in ("sold", "sale", "purchased")):
            if "$" in line:
                layered["Last Sale Price"] = line
            else:
                layered["Last Sale Date"] = line

    # Close modal gracefully
    try:
        close_btn = driver.find_element(
            By.XPATH,
            "//button[contains(.,'Close') or contains(@aria-label,'close')]",
        )
        driver.execute_script("arguments[0].click();", close_btn)
    except Exception:  # pragma: no cover - fallback
        driver.execute_script(
            "document.querySelector('body') && document.querySelector('body').click();"
        )

    time.sleep(0.7)
    return layered


def scroll_and_scrape_properties(
    driver,
    max_scrolls: int = 25,
    wait_time: float = 1.4,
    deep_scrape: bool = True,
    auto_filters: bool = True,
) -> List[Dict[str, Any]]:
    """
    Scroll through DealMachine property cards and return Airtable-ready dictionaries.
    """

    print("🚀 Starting advanced property scraping sequence...")
    properties: List[Dict[str, Any]] = []

    if auto_filters:
        apply_niche_filters(driver)

    try:
        WebDriverWait(driver, 25).until(
            EC.presence_of_element_located((By.XPATH, PROPERTY_CARD_SELECTOR))
        )
        print("✅ Property cards detected.")
    except TimeoutException:
        print("⚠️ No property cards found — aborting scrape.")
        return []

    last_count = 0
    for scroll_index in range(max_scrolls):
        cards = driver.find_elements(By.XPATH, PROPERTY_CARD_SELECTOR)
        print(f"📍 Found {len(cards)} cards after scroll {scroll_index + 1}")

        for position, card in enumerate(cards, start=1):
            try:
                card_text = card.text.strip()
                if not card_text:
                    continue

                lines = [ln.strip() for ln in card_text.split("\n") if ln.strip()]
                if not lines:
                    continue

                address = _extract_address(lines, card)
                if not address:
                    continue

                owner = _extract_owner(lines)
                value = _extract_value(lines)
                tags = _extract_tags(lines, card)

                record: Dict[str, Any] = {
                    "Property Address": address.strip(),
                    "Owner Name": (owner or "Unknown").strip(),
                    "Estimated Value": value.strip() if value else "",
                    "Status": ", ".join(tags) if tags else "",
                    "Equity %": "",
                    "Mailing Address": "",
                    "Last Sale Date": "",
                    "Last Sale Price": "",
                }

                if deep_scrape:
                    try:
                        driver.execute_script("arguments[0].scrollIntoView(true);", card)
                        driver.execute_script("arguments[0].click();", card)
                        layered = _scrape_modal(driver)
                        record.update({key: layered.get(key, record[key]) for key in layered})
                    except TimeoutException:
                        print(f"⚠️ Modal timeout for {address}")
                    except Exception as exc:
                        print(f"⚠️ Deep scrape error on {address}: {exc}")

                properties.append(record)

            except (NoSuchElementException, StaleElementReferenceException):
                print(f"⚠️ Skipping card #{position} due to DOM update.")
                continue

        driver.execute_script(
            "const sidebar=document.querySelector('.deal-scroll');"
            "if(sidebar){sidebar.scrollBy(0, sidebar.scrollHeight);}"
        )
        time.sleep(wait_time)

        if len(cards) == last_count:
            print("🔚 Reached end of property list.")
            break
        last_count = len(cards)

    cleaned = [p for p in properties if isinstance(p, dict) and any(p.values())]
    print(f"✅ Scraped {len(cleaned)} property records.")
    if cleaned:
        print(f"🧠 Sample record:\n{_safe_json_preview(cleaned[0])}")
    else:
        print("⚠️ No valid property data scraped.")

    return cleaned


def _extract_address(lines: List[str], card) -> str:
    for line in lines:
        lower = line.lower()
        if ("," in line and any(state in lower for state in ("fl", "tx", "ca", "ny", "az", "nv", "il"))) or any(
            token in lower for token in (" st", " ave", " rd", " blvd", " ln", " dr", " ct", " cir")
        ):
            return line
    try:
        return (
            card.find_element(By.XPATH, ".//*[contains(@class,'address') or contains(text(), ', ')]")
            .text.strip()
        )
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
