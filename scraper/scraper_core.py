from __future__ import annotations

import json
import time
from typing import Any, Dict, Iterable, List, Optional, Tuple

from selenium.common.exceptions import (
    NoSuchElementException,
    StaleElementReferenceException,
    TimeoutException,
)
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
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
MODAL_LOCATORS: List[str] = [
    PROPERTY_MODAL_SELECTOR,
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


def _wait_for_modal(driver, timeout: float = 10.0):
    last_error: Optional[Exception] = None
    for locator in MODAL_LOCATORS:
        try:
            element = WebDriverWait(driver, timeout).until(
                EC.visibility_of_element_located((By.XPATH, locator))
            )
            return element, locator
        except TimeoutException as exc:
            last_error = exc
    raise last_error or TimeoutException("Property modal not found")


def _close_modal(driver, locator_hint: Optional[str] = None, timeout: float = 5.0) -> None:
    for locator in CLOSE_BUTTON_LOCATORS:
        try:
            button = driver.find_element(By.XPATH, locator)
            driver.execute_script("arguments[0].click();", button)
            if locator_hint:
                WebDriverWait(driver, timeout).until(
                    EC.invisibility_of_element_located((By.XPATH, locator_hint))
                )
            return
        except (NoSuchElementException, StaleElementReferenceException):
            continue
        except TimeoutException:
            continue

    for overlay in OVERLAY_LOCATORS:
        try:
            element = driver.find_element(By.XPATH, overlay)
            driver.execute_script("arguments[0].click();", element)
            if locator_hint:
                WebDriverWait(driver, timeout).until(
                    EC.invisibility_of_element_located((By.XPATH, locator_hint))
                )
            return
        except (NoSuchElementException, StaleElementReferenceException):
            continue
        except TimeoutException:
            continue

    try:
        body = driver.find_element(By.TAG_NAME, "body")
        body.send_keys(Keys.ESCAPE)
    except Exception:
        pass
    time.sleep(0.4)


def _force_close_modal(driver) -> None:
    try:
        _close_modal(driver, None)
    except Exception:
        pass
    for locator in MODAL_LOCATORS:
        try:
            WebDriverWait(driver, 2).until(
                EC.invisibility_of_element_located((By.XPATH, locator))
            )
        except TimeoutException:
            continue


def _scrape_modal(driver) -> Dict[str, str]:
    """Scrape additional details from the property modal."""

    element, locator_hint = _wait_for_modal(driver)
    raw_text = element.text or element.get_attribute("innerText") or ""
    lines = [line.strip() for line in raw_text.split("\n") if line.strip()]

    layered: Dict[str, str] = {
        "Equity %": "",
        "Mailing Address": "",
        "Last Sale Date": "",
        "Last Sale Price": "",
    }

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

    _close_modal(driver, locator_hint)
    return layered


def _deep_scrape_card(
    driver,
    card,
    address: str,
    modal_timeouts: int,
) -> Tuple[Dict[str, str], int]:
    attempts = 0
    layered: Dict[str, str] = {}

    while attempts < 2:
        attempts += 1
        try:
            driver.execute_script(
                "arguments[0].scrollIntoView({block:'center', inline:'center'});",
                card,
            )
            WebDriverWait(driver, 6).until(lambda d: card.is_displayed())
            try:
                card.click()
            except Exception:
                driver.execute_script("arguments[0].click();", card)

            layered = _scrape_modal(driver)
            break

        except TimeoutException:
            modal_timeouts += 1
            if modal_timeouts <= 3 or modal_timeouts % 5 == 0:
                print(f"⚠️ Modal timeout for {address} (#{modal_timeouts})")
            _force_close_modal(driver)

        except StaleElementReferenceException:
            _force_close_modal(driver)
            raise

        except Exception as exc:
            print(f"⚠️ Deep scrape error on {address}: {exc}")
            _force_close_modal(driver)
            break

    return layered, modal_timeouts


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

    modal_timeouts = 0
    last_count = 0

    for scroll_index in range(max_scrolls):
        cards_snapshot = driver.find_elements(By.XPATH, PROPERTY_CARD_SELECTOR)
        print(f"📍 Found {len(cards_snapshot)} cards after scroll {scroll_index + 1}")

        position = 0
        stale_retries = 0

        while True:
            current_cards = driver.find_elements(By.XPATH, PROPERTY_CARD_SELECTOR)
            if position >= len(current_cards):
                break

            card = current_cards[position]
            try:
                card_text = card.text.strip()
                if not card_text:
                    position += 1
                    continue

                lines = [ln.strip() for ln in card_text.split("\n") if ln.strip()]
                if not lines:
                    position += 1
                    continue

                address = _extract_address(lines, card)
                if not address:
                    position += 1
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
                        layered, modal_timeouts = _deep_scrape_card(
                            driver, card, address, modal_timeouts
                        )
                        if layered:
                            record.update({key: layered.get(key, record[key]) for key in layered})
                    except StaleElementReferenceException:
                        stale_retries += 1
                        if stale_retries > 2:
                            print(f"⚠️ Repeated DOM updates on card #{position + 1}; skipping.")
                            position += 1
                            stale_retries = 0
                        else:
                            time.sleep(0.3)
                        continue

                properties.append(record)
                position += 1
                stale_retries = 0

            except StaleElementReferenceException:
                stale_retries += 1
                if stale_retries > 2:
                    print(f"⚠️ Repeated DOM updates on card #{position + 1}; skipping.")
                    position += 1
                    stale_retries = 0
                else:
                    time.sleep(0.3)
                continue
            except NoSuchElementException:
                position += 1
                continue

        driver.execute_script(
            "const sidebar=document.querySelector('.deal-scroll');"
            "if(sidebar){sidebar.scrollBy(0, sidebar.scrollHeight);}"
        )
        time.sleep(wait_time)

        current_total = len(driver.find_elements(By.XPATH, PROPERTY_CARD_SELECTOR))
        if current_total == last_count:
            print("🔚 Reached end of property list.")
            break
        last_count = current_total

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
