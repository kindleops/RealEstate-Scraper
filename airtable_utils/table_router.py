"""Reliable Airtable uploader for DealMachine property records."""

from __future__ import annotations

import ast
import json
import os
import time
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, MutableMapping, Optional, Tuple

import requests
from airtable import Airtable
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("AIRTABLE_API_KEY")
if not API_KEY:
    API_KEY = (
        "pat3xx44piaEiE5op."
        "3d60eafd8a46b7bd634c8e3de26f31d6e510e46f26ef3f5d120e55cab88551d6"
    )

PROPERTY_TABLE = {
    "base_id": "app3Aa7p8C1dOZAyc",
    "table_name": "Properties",
    "fallback_fields": {
        "Property Address",
        "Owner Name",
        "Status",
        "Estimated Value",
        "Motivation Score",
        "Source ZIP",
        "Scrape Timestamp",
    },
}

LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)
LOG_PATH = LOG_DIR / f"uploads_{time.strftime('%Y%m%d_%H%M%S')}.log"

_SCHEMA_CACHE: Dict[Tuple[str, str], List[str]] = {}
_CLIENT_CACHE: Dict[Tuple[str, str], Airtable] = {}


def _log(line: str) -> None:
    print(line)
    with LOG_PATH.open("a", encoding="utf-8") as handle:
        handle.write(line + "\n")


def _get_airtable_client(base_id: str, table_name: str) -> Airtable:
    cache_key = (base_id, table_name)
    if cache_key not in _CLIENT_CACHE:
        _CLIENT_CACHE[cache_key] = Airtable(base_id, table_name, api_key=API_KEY)
    return _CLIENT_CACHE[cache_key]


def _fetch_table_fields(base_id: str, table_name: str) -> List[str]:
    cache_key = (base_id, table_name)
    if cache_key in _SCHEMA_CACHE:
        return _SCHEMA_CACHE[cache_key]

    url = f"https://api.airtable.com/v0/meta/bases/{base_id}/tables"
    headers = {"Authorization": f"Bearer {API_KEY}"}
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            data = response.json()
            for table in data.get("tables", []):
                if table.get("name") == table_name:
                    fields = [field.get("name") for field in table.get("fields", []) if field.get("name")]
                    _SCHEMA_CACHE[cache_key] = fields
                    return fields
    except requests.RequestException as exc:
        _log(f"⚠️ Unable to fetch schema for {table_name}: {exc}")

    fallback = list(PROPERTY_TABLE["fallback_fields"])
    _SCHEMA_CACHE[cache_key] = fallback
    return fallback


def _coerce_value(value: Any) -> Any:
    if value is None:
        return ""
    if isinstance(value, (int, float)):
        return value
    if isinstance(value, bool):
        return "Yes" if value else "No"
    if isinstance(value, (list, tuple, set)):
        return ", ".join(str(item) for item in value if item not in (None, ""))
    if isinstance(value, dict):
        return json.dumps(value, default=str)
    return str(value).strip()


def _extract(raw: Mapping[str, Any], *keys: str) -> Any:
    for key in keys:
        if key in raw:
            val = raw.get(key)
            if val is not None and str(val).strip():
                return val
    return None


def _coerce_record(record: Any) -> Any:
    if isinstance(record, str):
        text = record.strip()
        if text.startswith("{") and text.endswith("}"):
            try:
                return ast.literal_eval(text)
            except (ValueError, SyntaxError):
                return record
    return record


def normalize_property_record(raw: Any, valid_fields: Iterable[str]) -> Optional[Dict[str, Any]]:
    if not isinstance(raw, Mapping):
        return None

    valid_set = set(valid_fields)
    address = _coerce_value(
        _extract(
            raw,
            "Property Address",
            "property_address",
            "full_address",
            "address",
        )
    )
    if not address:
        return None

    normalized: Dict[str, Any] = {}
    fallback_sources = {
        "Property Address": address,
        "Owner Name": _coerce_value(
            _extract(raw, "Owner Name", "owner_name", "Owner", "seller_name")
        ),
        "Status": _coerce_value(_extract(raw, "Status", "status")),
        "Estimated Value": _coerce_value(
            _extract(raw, "Estimated Value", "estimated_value", "est_value")
        ),
        "Motivation Score": _coerce_value(
            _extract(raw, "Motivation Score", "motivation_score", "motivation")
        ),
        "Source ZIP": _coerce_value(
            _extract(raw, "Source ZIP", "source_zip", "zip", "ZIP")
        ),
    }

    fallback_sources["Scrape Timestamp"] = time.strftime("%Y-%m-%d %H:%M:%S")

    for key, value in fallback_sources.items():
        if key in valid_set:
            normalized[key] = _coerce_value(value)

    for key, value in raw.items():
        if key in valid_set and key not in normalized:
            normalized[key] = _coerce_value(value)

    return normalized if normalized.get("Property Address") else None


def _safe_create_record(client: Airtable, record: Dict[str, Any]) -> bool:
    for attempt in range(3):
        try:
            client.create(record)
            return True
        except Exception as exc:
            error_text = str(exc)
            if "429" in error_text or "Rate" in error_text:
                time.sleep(2 ** attempt)
                continue
            if attempt < 2:
                time.sleep(1)
                continue
            raise
    return False


def _safe_batch_create(client: Airtable, records: List[Dict[str, Any]]) -> bool:
    payload = [{"fields": rec} for rec in records]
    for attempt in range(3):
        try:
            client.batch_create(payload)
            return True
        except Exception as exc:
            error_text = str(exc)
            if "429" in error_text or "Rate" in error_text:
                time.sleep(2 ** attempt)
                continue
            if attempt < 2:
                time.sleep(1)
                continue
            raise
    return False


def route_and_upload(records: Iterable[Any], batch_size: Optional[int] = None) -> Dict[str, int]:
    if not API_KEY:
        _log("⚠️ AIRTABLE_API_KEY not configured. Skipping upload.")
        return {"total": 0, "uploaded": 0, "skipped": 0, "failed": 0}

    materialised: List[Any] = list(records or [])
    total = len(materialised)
    if total == 0:
        _log("ℹ️ No records to upload.")
        return {"total": 0, "uploaded": 0, "skipped": 0, "failed": 0}

    base_id = PROPERTY_TABLE["base_id"]
    table_name = PROPERTY_TABLE["table_name"]
    client = _get_airtable_client(base_id, table_name)
    schema = _fetch_table_fields(base_id, table_name)

    uploaded = skipped = failed = 0
    buffer: List[Dict[str, Any]] = []
    sample_logged = False

    for idx, raw in enumerate(materialised, start=1):
        record = _coerce_record(raw)
        normalized = normalize_property_record(record, schema)
        if not normalized:
            skipped += 1
            _log(f"⚠️ Skipping record #{idx}: invalid or empty payload.")
            continue

        if not sample_logged:
            _log(f"🧠 Sample upload: {json.dumps(normalized, indent=2)}")
            sample_logged = True

        if batch_size:
            buffer.append(normalized)
            if len(buffer) >= batch_size:
                try:
                    _safe_batch_create(client, buffer)
                    uploaded += len(buffer)
                    for rec in buffer:
                        _log(f"✅ Uploaded Property: {rec['Property Address']}")
                except Exception as exc:
                    failed += len(buffer)
                    _log(f"❌ Batch upload failed ({len(buffer)} records): {exc}")
                buffer = []
            continue

        try:
            _safe_create_record(client, normalized)
            uploaded += 1
            _log(f"✅ Uploaded Property #{idx}: {normalized['Property Address']}")
        except Exception as exc:
            failed += 1
            _log(f"❌ Upload failed for record #{idx}: {exc}")

    if batch_size and buffer:
        try:
            _safe_batch_create(client, buffer)
            uploaded += len(buffer)
            for rec in buffer:
                _log(f"✅ Uploaded Property: {rec['Property Address']}")
        except Exception as exc:
            failed += len(buffer)
            _log(f"❌ Batch upload failed ({len(buffer)} records): {exc}")

    summary = {
        "total": total,
        "uploaded": uploaded,
        "skipped": skipped,
        "failed": failed,
    }
    _log(
        "✅ Upload Summary — Total: {total}, Uploaded: {uploaded}, Skipped: {skipped}, Failed: {failed}".format(
            **summary
        )
    )
    return summary


def upload_batch(records: Iterable[Any], batch_size: int = 10) -> Dict[str, int]:
    return route_and_upload(records, batch_size=batch_size)
