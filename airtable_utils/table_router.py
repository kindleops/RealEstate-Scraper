"""
Utility for routing scraped DealMachine records into Airtable tables.

Prerequisites
-------------
    pip install airtable-python-wrapper python-dotenv

Environment
-----------
    AIRTABLE_API_KEY=<token>
"""

from __future__ import annotations

import os
import ast
from typing import Any, Dict, Iterable, List, Mapping, MutableMapping

from airtable import Airtable
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("AIRTABLE_API_KEY")
if not API_KEY:
    # Fall back to the provided scraper workspace token if env not set.
    API_KEY = (
        "pat3xx44piaEiE5op."
        "3d60eafd8a46b7bd634c8e3de26f31d6e510e46f26ef3f5d120e55cab88551d6"
    )


PROPERTY_TABLE = {
    "base_id": "app3Aa7p8C1dOZAyc",
    "table_name": "Properties",
    "valid_fields": {
        "Property Address",
        "Owner Name",
        "Status",
        "Estimated Value",
    },
}

SELLER_TABLE = {
    "base_id": "appOZysJe5NuxTXO6",
    "table_name": "Sellers",
    "valid_fields": {
        "Owner Name",
    },
}


def clean_fields(fields: Mapping[str, Any], valid_fields: Iterable[str]) -> Dict[str, Any]:
    """
    Retain only Airtable-supported fields and drop empty values.

    Args:
        fields: Candidate payload keyed by Airtable column name.
        valid_fields: Iterable of valid Airtable column names.

    Returns:
        Dict[str, Any]: Cleaned fields dictionary.
    """
    allowed = set(valid_fields)
    cleaned: Dict[str, Any] = {}
    for key, value in fields.items():
        if key not in allowed:
            continue
        if value is None:
            continue
        if isinstance(value, str):
            trimmed = value.strip()
            if not trimmed:
                continue
            cleaned[key] = trimmed
        elif isinstance(value, (list, dict)) and not value:
            continue
        else:
            cleaned[key] = value
    return cleaned


def _insert_record(config: Mapping[str, Any], payload: Dict[str, Any]) -> str | None:
    base_id = config["base_id"]
    table_name = config["table_name"]
    client = Airtable(base_id, table_name, api_key=API_KEY)
    response = client.insert(payload)
    return response.get("id") if isinstance(response, dict) else None


def _coerce_record(record: Any) -> Any:
    """Convert stringified dictionaries back into real dict objects."""
    if isinstance(record, str):
        text = record.strip()
        if text.startswith("{") and text.endswith("}"):
            try:
                parsed = ast.literal_eval(text)
                return parsed
            except (ValueError, SyntaxError):
                return record
    return record


def route_and_upload(records: Iterable[Any]) -> None:
    """
    Upload scraped property dictionaries into Airtable tables.

    Args:
        records: Iterable of dictionaries produced by the scraper. Expected keys:
            - full_address
            - owner_name
            - status
            - est_value

    Returns:
        None
    """
    if not API_KEY:
        print("⚠️ AIRTABLE_API_KEY not configured. Skipping upload.")
        return

    materialised: List[Any] = list(records)

    for i, sample in enumerate(materialised[:3], start=1):
        print(f"🔍 Record {i} type before upload: {type(sample).__name__}")

    for idx, raw_record in enumerate(materialised, start=1):
        record = _coerce_record(raw_record)
        if not isinstance(record, Mapping):
            print(f"⚠️ Skipping record #{idx}: payload is not a dict.")
            continue

        property_payload = {
            "Property Address": record.get("Property Address") or record.get("full_address"),
            "Owner Name": record.get("Owner Name") or record.get("owner_name"),
            "Status": record.get("Status") or record.get("status"),
            "Estimated Value": record.get("Estimated Value") or record.get("est_value"),
        }
        clean_property = clean_fields(property_payload, PROPERTY_TABLE["valid_fields"])

        seller_payload = {
            "Owner Name": record.get("Owner Name") or record.get("owner_name"),
        }
        clean_seller = clean_fields(seller_payload, SELLER_TABLE["valid_fields"])

        label = clean_property.get("Property Address") or clean_property.get("Owner Name") or f"Row {idx}"

        if clean_property:
            try:
                record_id = _insert_record(PROPERTY_TABLE, clean_property)
                if record_id:
                    print(f"✅ Properties → {label} (id={record_id})")
                else:
                    print(f"⚠️ Properties upload returned no ID for {label}.")
            except Exception as exc:  # pragma: no cover - network path
                print(f"⚠️ Properties upload failed for {label}: {exc}")
        else:
            print(f"ℹ️ No valid property fields for record #{idx}; skipped Properties table.")

        if clean_seller:
            try:
                record_id = _insert_record(SELLER_TABLE, clean_seller)
                name = clean_seller.get("Owner Name", label)
                if record_id:
                    print(f"✅ Sellers → {name} (id={record_id})")
                else:
                    print(f"⚠️ Sellers upload returned no ID for {name}.")
            except Exception as exc:  # pragma: no cover - network path
                print(f"⚠️ Sellers upload failed for {label}: {exc}")
        else:
            print(f"ℹ️ No seller fields for record #{idx}; skipped Sellers table.")
