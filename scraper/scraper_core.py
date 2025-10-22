from __future__ import annotations

import csv
import json
import random
import time
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

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


def apply_niche_filters(
    driver,
    filters: Optional[Iterable[str]] = None,
    pause: float = 1.2,
) -> None:
    """
    Apply a sequence of DealMachine quick filters, probing multiple containers.
    """

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
        except Exception as exc:  # pragma: no cover - defensive
            print(f"⚠️ Error applying filter '{label}': {exc}")


def _safe_json_preview(record: Dict[str, Any]) -> str:
    try:
        return json.dumps(record, indent=2, default=str)
    except TypeError:
        return str(record)


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
        except TimeoutException:
            continue
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
        except (NoSuchElementException, StaleElementReferenceException):
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
    layered: Dict[str, str] = {}

    max_attempts = 2
    for attempt in range(1, max_attempts + 1):
        try:
            handled = _dismiss_screen_overlays(driver)
            if handled and attempt == 1:
                print(f"ℹ️ Suppressed overlay layers: {', '.join(sorted(set(handled)))}")

            driver.execute_script(
                "arguments[0].scrollIntoView({block:'center', inline:'center'});",
                card,
            )
            WebDriverWait(driver, 10).until(lambda d: card.is_displayed())

            try:
                card.click()
            except Exception:
                driver.execute_script("arguments[0].click();", card)

            modal_root, locator_hint = _wait_for_modal(driver)

            field_map = {
                "Property Address": [
                    ".//span[contains(@class,'address')]",
                    ".//div[contains(@class,'address')]",
                    ".//h1[contains(@class,'address')]",
                ],
                "Owner Name": [
                    ".//span[contains(@class,'owner')]",
                    ".//div[contains(@class,'owner')]",
                    ".//h2[contains(@class,'owner')]",
                ],
                "Mailing Address": [
                    ".//span[contains(text(),'Mailing')]/following-sibling::*[1]",
                    ".//div[contains(text(),'Mailing Address')]/following-sibling::*[1]",
                ],
                "Property Type": [
                    ".//span[contains(text(),'Property Type')]/following-sibling::*[1]",
                    ".//div[contains(text(),'Property Type')]/following-sibling::*[1]",
                ],
                "Estimated Value": [
                    ".//span[contains(text(),'Est') or contains(text(),'Value')]/following-sibling::*[1]",
                    ".//div[contains(@class,'value') and contains(text(),'$')]",
                ],
                "Equity %": [
                    ".//span[contains(text(),'Equity')]",
                    ".//div[contains(text(),'Equity')]",
                ],
                "Beds/Baths": [
                    ".//span[contains(text(),'Beds') or contains(text(),'Baths')]/../*",
                ],
                "Sale Date / Year Built": [
                    ".//span[contains(text(),'Sale') or contains(text(),'Built')]/following-sibling::*[1]",
                    ".//div[contains(text(),'Sale Date') or contains(text(),'Year Built')]/following-sibling::*[1]",
                ],
            }

            def first_non_empty(paths: List[str]) -> str:
                for path in paths:
                    elements = modal_root.find_elements(By.XPATH, path)
                    for element in elements:
                        text = element.text.strip()
                        if text:
                            return text
                return ""

            for key, paths in field_map.items():
                value = first_non_empty(paths)
                if value:
                    layered[key] = value

            tag_elements = modal_root.find_elements(
                By.XPATH,
                ".//*[contains(@class,'chip') or contains(@class,'badge') or contains(@class,'tag')]",
            )
            tags = {tag.text.strip() for tag in tag_elements if tag.text.strip()}
            if tags:
                layered["Vacancy / Absentee Tags"] = ", ".join(sorted(tags))

            print(f"✅ Modal scraped for {address} (attempt {attempt})")
            _close_modal(driver, locator_hint)
            WebDriverWait(driver, 5).until(
                EC.invisibility_of_element_located((By.XPATH, locator_hint))
            )
            break

        except TimeoutException:
            modal_timeouts += 1
            print(f"⚠️ Modal timeout for {address} (attempt {attempt}, total {modal_timeouts})")
            _force_close_modal(driver)
            if modal_timeouts % 5 == 0:
                print("↻ Refreshing page after repeated timeouts.")
                driver.refresh()
                WebDriverWait(driver, 20).until(
                    EC.presence_of_element_located((By.XPATH, PROPERTY_CARD_SELECTOR))
                )

        except InvalidSessionIdException:
            _force_close_modal(driver)
            raise

        except StaleElementReferenceException:
            print(f"⚠️ Modal DOM went stale for {address}; retrying.")
            _force_close_modal(driver)
            if attempt == 2:
                layered = {}
            continue

        except Exception as exc:
            print(f"⚠️ Modal scrape error for {address}: {exc}")
            _force_close_modal(driver)
            if attempt == 2:
                layered = {}
            else:
                try:
                    driver.refresh()
                    WebDriverWait(driver, 20).until(
                        EC.presence_of_element_located((By.XPATH, PROPERTY_CARD_SELECTOR))
                    )
                except Exception:
                    pass

        finally:
            time.sleep(random.uniform(0.3, 0.7))
    else:
        print(f"⚠️ Skipping modal for {address} after {max_attempts} attempts.")

    return layered, modal_timeouts


def scroll_and_scrape_properties(
    driver,
    max_scrolls: int = 25,
    wait_time: float = 1.4,
    deep_scrape: bool = True,
    auto_filters: bool = True,
    modal_limit: int = 40,
    restart_callback=None,
    save_path: str = "data/scraped_properties.json",
    auto_quit: bool = False,
) -> List[Dict[str, Any]]:
    """Robust DealMachine scraper with modal handling, batching, and persistence."""

    print("🚀 Starting advanced property scraping sequence...")
    properties: List[Dict[str, Any]] = []
    modal_timeouts = 0
    modal_scraped = 0
    refresh_every = 50
    restart_attempts = 0
    output_path = Path(save_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    def _persist_batch(records: List[Dict[str, Any]]) -> None:
        if not records:
            return
        if output_path.suffix.lower() == ".csv":
            fieldnames = sorted({key for rec in records for key in rec.keys()})
            with output_path.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(handle, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(records)
        else:
            output_path.write_text(json.dumps(records, indent=2, default=str), encoding="utf-8")

    def _post_refresh() -> None:
        WebDriverWait(driver, 20).until(
            EC.visibility_of_element_located((By.XPATH, PROPERTY_CARD_SELECTOR))
        )
        if auto_filters:
            apply_niche_filters(driver)

    session_active = True
    try:
        while session_active:
            try:
                if auto_filters:
                    apply_niche_filters(driver)

                WebDriverWait(driver, 25).until(
                    EC.visibility_of_element_located((By.XPATH, PROPERTY_CARD_SELECTOR))
                )
                print("✅ Property cards detected.")

                last_count = 0
                modal_timeouts = 0
                modal_scraped = 0

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
                            WebDriverWait(driver, 10).until(lambda d, c=card: c.is_displayed())
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
                                "Property Type": "",
                                "Beds/Baths": "",
                                "Sale Date / Year Built": "",
                                "Vacancy / Absentee Tags": "",
                            }

                            if deep_scrape and modal_scraped < modal_limit:
                                layered, modal_timeouts = _deep_scrape_card(
                                    driver, card, address, modal_timeouts
                                )
                                modal_scraped += 1
                                if layered:
                                    record.update({key: layered.get(key, record.get(key, "")) for key in layered})
                            elif deep_scrape and modal_scraped >= modal_limit:
                                print(f"ℹ️ Modal limit ({modal_limit}) reached; continuing without deep scrape.")

                            properties.append(record)

                            if len(properties) % refresh_every == 0:
                                print("🔄 Refresh threshold reached — refreshing page and reapplying filters.")
                                driver.refresh()
                                _post_refresh()

                            position += 1
                            stale_retries = 0

                        except StaleElementReferenceException:
                            stale_retries += 1
                            if stale_retries > 2:
                                print(f"⚠️ Repeated DOM updates on card #{position + 1}; skipping.")
                                position += 1
                                stale_retries = 0
                            else:
                                WebDriverWait(driver, 3).until(lambda _: True)
                            continue
                        except TimeoutException:
                            print(f"⚠️ Card #{position + 1} timed out; moving on.")
                            position += 1
                            continue
                        except InvalidSessionIdException:
                            raise
                        except Exception as exc:
                            print(f"⚠️ Unexpected card parsing error: {exc}")
                            position += 1
                            continue

                    driver.execute_script(
                        "const sidebar=document.querySelector('.deal-scroll');"
                        "if(sidebar){sidebar.scrollBy(0, sidebar.scrollHeight);}" 
                    )
                    try:
                        WebDriverWait(driver, wait_time).until(
                            lambda d, count=len(cards_snapshot): len(d.find_elements(By.XPATH, PROPERTY_CARD_SELECTOR)) > count
                        )
                    except TimeoutException:
                        pass

                    current_total = len(driver.find_elements(By.XPATH, PROPERTY_CARD_SELECTOR))
                    if current_total == last_count:
                        print("🔚 Reached end of property list.")
                        break
                    last_count = current_total

                break

            except InvalidSessionIdException:
                print("⚠️ Session crashed — restarting driver…")
                restart_attempts += 1
                if restart_attempts > 3 or not restart_callback:
                    print("❌ Unable to recover from InvalidSessionIdException.")
                    break

                try:
                    driver.quit()
                except Exception:
                    pass

                driver = restart_callback()
                print("✅ Driver restart successful, resuming scrape…")
                continue

            except TimeoutException as exc:
                print(f"⚠️ Timeout encountered ({exc}). Attempting recovery via refresh.")
                try:
                    driver.refresh()
                    _post_refresh()
                except InvalidSessionIdException:
                    continue
                except Exception as recovery_exc:
                    print(f"⚠️ Refresh recovery failed: {recovery_exc}")
                    break

            except Exception as exc:
                print(f"⚠️ Unexpected scraper error: {exc}")
                try:
                    driver.refresh()
                    _post_refresh()
                except Exception:
                    pass
                break

        cleaned = [p for p in properties if isinstance(p, dict) and any(p.values())]
        print(f"✅ Scraped {len(cleaned)} property records.")
        if cleaned:
            print(f"🧠 Sample record:\n{_safe_json_preview(cleaned[0])}")
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
