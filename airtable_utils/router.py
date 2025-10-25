# airtable_utils/router.py
# ------------------------------------------------------------
# Unified, multi-base Airtable router with schema validation,
# retries, batch uploads, detailed logging, and Slack alerts.
# ------------------------------------------------------------

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Tuple

import requests
from pyairtable import Table
from dotenv import load_dotenv

# === Load env ===
load_dotenv()
AIRTABLE_API_KEY = os.getenv("AIRTABLE_API_KEY")
SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL", "").strip()

if not AIRTABLE_API_KEY:
    raise RuntimeError("AIRTABLE_API_KEY is required in your .env")

# === Field mappings (import your canonical schemas) ===
# Ensure these come from your central mappings.py
from airtable_utils.mappings import (
    PROPERTY_FIELDS,
    SELLER_FIELDS,
    MORTGAGE_FIELDS,
    COMPANY_FIELDS,
    COMPANY_CONTACT_FIELDS,
    PHONE_FIELDS,
    EMAIL_FIELDS,
    AOD_FIELDS,
    PROBATE_FIELDS,
    LIEN_FIELDS,
    FORECLOSURE_FIELDS,
    to_title_case,
)

# === Logging ===
LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)
LOG_PATH = LOG_DIR / f"uploads_{time.strftime('%Y%m%d_%H%M%S')}.log"


def _log(line: str) -> None:
    print(line)
    try:
        with LOG_PATH.open("a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        # Don't crash the pipeline due to logging failures
        pass


def _slack_post(payload: Dict[str, Any]) -> None:
    if not SLACK_WEBHOOK_URL:
        return
    try:
        requests.post(SLACK_WEBHOOK_URL, json=payload, timeout=6)
    except Exception as exc:
        _log(f"⚠️ Slack post failed: {exc}")


def slack_info(msg: str) -> None:
    _slack_post({"text": f":white_check_mark: {msg}"})


def slack_warn(msg: str) -> None:
    _slack_post({"text": f":warning: {msg}"})


def slack_error(msg: str) -> None:
    _slack_post({"text": f":x: {msg}"})


# === Bases & Tables (one base per table) ===
# You provided these base IDs (each base contains a single table)
BASE_MAP: Dict[str, Dict[str, str]] = {
    # table_name: { "base_id": "<id>", "table_name": "<table in base>" }
    "Probate":           {"base_id": "appzYqD6j9MzJuxiO", "table_name": "Probate"},
    "Liens":             {"base_id": "appxYsTGMkmd4WAky", "table_name": "Liens"},
    "Mortgages":         {"base_id": "appuYvtpFqYJpXiBM", "table_name": "Mortgages"},
    "Company Contacts":  {"base_id": "appiysxXpr0dxQe5I", "table_name": "Company Contacts"},
    "AOD":               {"base_id": "appdI9MeNwQBob0IC", "table_name": "AOD"},
    "Foreclosure":       {"base_id": "appQzzDV85go43ITt", "table_name": "Foreclosure"},
    "Sellers":           {"base_id": "appOZysJe5NuxTXO6", "table_name": "Sellers"},
    "Email Addresses":   {"base_id": "appNFNqvPAK8u5ReT", "table_name": "Email Addresses"},
    "Vacant":            {"base_id": "appJXK47tV5o7D6UJ", "table_name": "Vacant"},
    "Phone Numbers":     {"base_id": "app3MqkpxEiHXBKAW", "table_name": "Phone Numbers"},
    "Properties":        {"base_id": "app3Aa7p8C1dOZAyc", "table_name": "Properties"},
    "Companies":         {"base_id": "app21RPKrr0JIg4Ea", "table_name": "Companies"},
}

# Canonical schemas per table (used to auto-route records)
TABLE_FIELD_GROUPS: Dict[str, List[str]] = {
    "Properties": PROPERTY_FIELDS,
    "Sellers": SELLER_FIELDS,
    "Mortgages": MORTGAGE_FIELDS,
    "Companies": COMPANY_FIELDS,
    "Company Contacts": COMPANY_CONTACT_FIELDS,
    "Phone Numbers": PHONE_FIELDS,
    "Email Addresses": EMAIL_FIELDS,
    "AOD": AOD_FIELDS,
    "Probate": PROBATE_FIELDS,
    "Liens": LIEN_FIELDS,
    "Foreclosure": FORECLOSURE_FIELDS,
    # "Vacant" has no explicit schema from your mapping; it’ll rely on live schema
}

# === Caches ===
_CLIENT_CACHE: Dict[Tuple[str, str], Table] = {}
_SCHEMA_CACHE: Dict[Tuple[str, str], List[str]] = {}


def _get_table(base_id: str, table_name: str) -> Table:
    key = (base_id, table_name)
    if key not in _CLIENT_CACHE:
        _CLIENT_CACHE[key] = Table(AIRTABLE_API_KEY, base_id, table_name)
    return _CLIENT_CACHE[key]


def _fetch_live_schema(base_id: str, table_name: str) -> List[str]:
    """
    Pull the live schema from Airtable Meta API. Fallback to known schema map.
    """
    cache_key = (base_id, table_name)
    if cache_key in _SCHEMA_CACHE:
        return _SCHEMA_CACHE[cache_key]

    url = f"https://api.airtable.com/v0/meta/bases/{base_id}/tables"
    headers = {"Authorization": f"Bearer {AIRTABLE_API_KEY}"}
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        if resp.status_code == 200:
            meta = resp.json()
            for t in meta.get("tables", []):
                if t.get("name") == table_name:
                    fields = [f.get("name") for f in t.get("fields", []) if f.get("name")]
                    if fields:
                        _SCHEMA_CACHE[cache_key] = fields
                        return fields
        else:
            _log(f"⚠️ Meta API {base_id}/{table_name} returned {resp.status_code}: {resp.text[:200]}")
    except Exception as exc:
        _log(f"⚠️ Meta API error for {base_id}/{table_name}: {exc}")

    # fallback to canonical mapping if available
    fallback = TABLE_FIELD_GROUPS.get(table_name, [])
    _SCHEMA_CACHE[cache_key] = list(fallback)
    return _SCHEMA_CACHE[cache_key]


def _clean_record_keys(record: Mapping[str, Any]) -> Dict[str, Any]:
    """
    Title-case keys and drop null/empty values.
    """
    clean: Dict[str, Any] = {}
    for k, v in (record or {}).items():
        if v in (None, ""):
            continue
        clean[to_title_case(str(k))] = v
    return clean


def _subset_to_schema(record: Mapping[str, Any], fields: List[str]) -> Dict[str, Any]:
    if not fields:
        # if no known fields (e.g., Vacant, or temp table), pass everything
        return dict(record)
    allowed = set(fields)
    return {k: v for k, v in record.items() if k in allowed}


def _create_with_retries(table: Table, fields: Dict[str, Any], max_attempts: int = 3) -> bool:
    """
    Create a single record with exponential backoff on 429s and transient errors.
    """
    for attempt in range(1, max_attempts + 1):
        try:
            table.create(fields)
            return True
        except Exception as exc:
            msg = str(exc)
            is_rate = "429" in msg or "Rate" in msg or "Too Many Requests" in msg
            _log(f"⚠️ create failed (attempt {attempt}/{max_attempts}): {msg}")
            if attempt < max_attempts and (is_rate or True):
                time.sleep(min(8, 2 ** attempt))
                continue
            return False


def _batch_create_with_retries(table: Table, batch: List[Dict[str, Any]], max_attempts: int = 3) -> bool:
    """
    Batch create (up to Airtable’s limits) with retries.
    """
    payload = [{"fields": rec} for rec in batch]
    for attempt in range(1, max_attempts + 1):
        try:
            table.batch_create(payload)
            return True
        except Exception as exc:
            msg = str(exc)
            is_rate = "429" in msg or "Rate" in msg or "Too Many Requests" in msg
            _log(f"⚠️ batch_create failed (attempt {attempt}/{max_attempts}): {msg}")
            if attempt < max_attempts and (is_rate or True):
                time.sleep(min(8, 2 ** attempt))
                continue
            return False


def _detect_target_tables(cleaned: Mapping[str, Any]) -> List[str]:
    """
    Decide which tables a record should be routed to based on field overlap
    with canonical schemas. If none match, default to Properties when there is a
    'Property Address' or 'Full Address'.
    """
    keys = set(cleaned.keys())
    hits: List[Tuple[str, int]] = []

    for table_name, fields in TABLE_FIELD_GROUPS.items():
        overlap = len(keys.intersection(set(fields)))
        if overlap > 0:
            hits.append((table_name, overlap))

    # Sort by strongest schema match (more overlapping fields first)
    hits.sort(key=lambda x: x[1], reverse=True)
    targets = [t for t, _ in hits]

    if not targets:
        # heuristic fallback
        if any(k in keys for k in ("Property Address", "Full Address", "Street Address")):
            targets = ["Properties"]

    return targets


def route_and_upload(
    record: Mapping[str, Any],
    *,
    prefer_tables: Optional[List[str]] = None,
    batch_mode: bool = False,
) -> Dict[str, bool]:
    """
    Route a single record to the appropriate base(s)/table(s).
    Returns per-table success booleans.
    """
    if not isinstance(record, Mapping):
        _log("⚠️ route_and_upload: record is not a mapping; skipped")
        return {}

    cleaned = _clean_record_keys(record)
    if not cleaned:
        _log("⚠️ route_and_upload: empty/invalid record after cleaning; skipped")
        return {}

    # Pick targets
    targets = prefer_tables or _detect_target_tables(cleaned)
    if not targets:
        _log("ℹ️ No matching table for record; skipped")
        return {}

    results: Dict[str, bool] = {}

    for table_name in targets:
        meta = BASE_MAP.get(table_name)
        if not meta:
            _log(f"⚠️ Unknown table in BASE_MAP: {table_name} — skipping")
            results[table_name] = False
            continue

        base_id = meta["base_id"]
        real_table = meta["table_name"]
        table = _get_table(base_id, real_table)
        live_fields = _fetch_live_schema(base_id, real_table)

        subset = _subset_to_schema(cleaned, live_fields)
        if not subset:
            _log(f"ℹ️ Record has no valid fields for {table_name}; skipping")
            results[table_name] = False
            continue

        pretty = subset.get("Full Address") or subset.get("Property Address") or subset.get("Company Name") or "(no key)"
        _log(f"📦 Upload → [{table_name}] {pretty}")

        ok = _create_with_retries(table, subset)
        results[table_name] = ok
        if ok:
            _log(f"✅ Uploaded → [{table_name}] {pretty}")
        else:
            _log(f"❌ Upload failed → [{table_name}] {pretty}")

    return results


def batch_upload(
    records: Iterable[Mapping[str, Any]],
    *,
    batch_size: int = 10,
    hard_batch: bool = False,
    prefer_tables: Optional[List[str]] = None,
) -> Dict[str, int]:
    """
    Batch upload with routing. Two modes:
      - hard_batch=True: group by table and use batch_create for each group
      - hard_batch=False (default): per-record route_and_upload (safer if schemas vary)
    Returns summary counts.
    """
    materialized = [r for r in (records or []) if isinstance(r, Mapping)]
    if not materialized:
        _log("ℹ️ No records provided to batch_upload.")
        return {"total": 0, "uploaded": 0, "failed": 0, "skipped": 0}

    total = len(materialized)
    uploaded = failed = skipped = 0

    if not hard_batch:
        for idx, rec in enumerate(materialized, 1):
            res = route_and_upload(rec, prefer_tables=prefer_tables)
            if not res:
                skipped += 1
                continue
            # Count success/fail for this record as a single unit:
            if any(res.values()):
                uploaded += 1
            else:
                failed += 1
        summary = {"total": total, "uploaded": uploaded, "failed": failed, "skipped": skipped}
        _log(f"📊 Batch summary: {summary}")
        if uploaded:
            slack_info(f"Batch upload complete: {uploaded}/{total} records uploaded")
        elif failed:
            slack_warn(f"Batch upload completed with failures: {failed}/{total} failed")
        return summary

    # hard_batch mode: route to buckets by table and use batch_create
    # Build per-table buckets (use live schema for filtering)
    buckets: Dict[str, List[Dict[str, Any]]] = {}

    for rec in materialized:
        cleaned = _clean_record_keys(rec)
        targets = prefer_tables or _detect_target_tables(cleaned)
        if not targets:
            skipped += 1
            continue
        for table_name in targets:
            meta = BASE_MAP.get(table_name)
            if not meta:
                continue
            base_id = meta["base_id"]
            real_table = meta["table_name"]
            live_fields = _fetch_live_schema(base_id, real_table)
            subset = _subset_to_schema(cleaned, live_fields)
            if subset:
                buckets.setdefault(table_name, []).append(subset)

    for table_name, rows in buckets.items():
        meta = BASE_MAP[table_name]
        base_id = meta["base_id"]
        real_table = meta["table_name"]
        table = _get_table(base_id, real_table)

        # chunk
        for i in range(0, len(rows), batch_size):
            chunk = rows[i:i + batch_size]
            ok = _batch_create_with_retries(table, chunk)
            if ok:
                uploaded += len(chunk)
                _log(f"✅ Batch → [{table_name}] +{len(chunk)}")
            else:
                failed += len(chunk)
                _log(f"❌ Batch failed → [{table_name}] ({len(chunk)})")

    summary = {"total": total, "uploaded": uploaded, "failed": failed, "skipped": skipped}
    _log(f"📊 Batch summary: {summary}")
    if uploaded:
        slack_info(f"Batch upload complete: {uploaded}/{total} records uploaded")
    elif failed:
        slack_warn(f"Batch upload completed with failures: {failed}/{total} failed")
    return summary


# ---------- Convenience helpers ----------

def upload_property(record: Mapping[str, Any]) -> bool:
    """
    Force route to Properties only (useful when you are sure of target)
    """
    res = route_and_upload(record, prefer_tables=["Properties"])
    return bool(res.get("Properties"))


def upload_seller(record: Mapping[str, Any]) -> bool:
    res = route_and_upload(record, prefer_tables=["Sellers"])
    return bool(res.get("Sellers"))


def upload_company(record: Mapping[str, Any]) -> bool:
    res = route_and_upload(record, prefer_tables=["Companies"])
    return bool(res.get("Companies"))


def upload_contact(record: Mapping[str, Any]) -> bool:
    res = route_and_upload(record, prefer_tables=["Company Contacts"])
    return bool(res.get("Company Contacts"))


def upload_phone(record: Mapping[str, Any]) -> bool:
    res = route_and_upload(record, prefer_tables=["Phone Numbers"])
    return bool(res.get("Phone Numbers"))


def upload_email(record: Mapping[str, Any]) -> bool:
    res = route_and_upload(record, prefer_tables=["Email Addresses"])
    return bool(res.get("Email Addresses"))


def upload_probate(record: Mapping[str, Any]) -> bool:
    res = route_and_upload(record, prefer_tables=["Probate"])
    return bool(res.get("Probate"))


def upload_lien(record: Mapping[str, Any]) -> bool:
    res = route_and_upload(record, prefer_tables=["Liens"])
    return bool(res.get("Liens"))


def upload_foreclosure(record: Mapping[str, Any]) -> bool:
    res = route_and_upload(record, prefer_tables=["Foreclosure"])
    return bool(res.get("Foreclosure"))


def upload_aod(record: Mapping[str, Any]) -> bool:
    res = route_and_upload(record, prefer_tables=["AOD"])
    return bool(res.get("AOD"))


def upload_mortgage(record: Mapping[str, Any]) -> bool:
    res = route_and_upload(record, prefer_tables=["Mortgages"])
    return bool(res.get("Mortgages"))


def upload_vacant(record: Mapping[str, Any]) -> bool:
    res = route_and_upload(record, prefer_tables=["Vacant"])
    return bool(res.get("Vacant"))