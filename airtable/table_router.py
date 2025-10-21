"""
Airtable routing utilities for the scraper.

Prerequisites:
    pip install airtable-python-wrapper python-dotenv

Environment:
    Create a .env file with:
        AIRTABLE_API_KEY=<their_token_here>
"""

from __future__ import annotations

import os
import site
import sys
from functools import lru_cache
from typing import Any, Dict, Iterable, List, MutableMapping, Optional, Sequence

from dotenv import load_dotenv

from .field_mapping import (
    AOD_FIELDS,
    COMPANY_CONTACT_FIELDS,
    COMPANY_FIELDS,
    EMAIL_FIELDS,
    FORECLOSURE_FIELDS,
    LIEN_FIELDS,
    MORTGAGE_FIELDS,
    PHONE_FIELDS,
    PROBATE_FIELDS,
    PROPERTY_FIELDS,
    SELLER_FIELDS,
    to_title_case,
)

def _import_airtable_client():
    try:
        from airtable import Airtable as AirtableClient  # type: ignore
        return AirtableClient
    except (ImportError, AttributeError):
        sys.modules.pop("airtable", None)
        candidate_paths: List[str] = []
        try:
            candidate_paths.extend(site.getsitepackages())
        except Exception:
            pass
        try:
            user_site = site.getusersitepackages()
            if isinstance(user_site, str):
                candidate_paths.append(user_site)
            else:
                candidate_paths.extend(list(user_site))
        except Exception:
            pass

        inserted: List[str] = []
        for path in candidate_paths:
            if path and path not in sys.path:
                sys.path.insert(0, path)
                inserted.append(path)

        try:
            from airtable import Airtable as AirtableClient  # type: ignore
            return AirtableClient
        except Exception as exc:
            raise ImportError(
                "airtable-python-wrapper is required. Install it with "
                "`pip install airtable-python-wrapper`."
            ) from exc
        finally:
            for path in inserted:
                if path in sys.path:
                    sys.path.remove(path)


Airtable = _import_airtable_client()

load_dotenv()

API_KEY = os.getenv("AIRTABLE_API_KEY")
if not API_KEY:
    print(
        "⚠️ AIRTABLE_API_KEY not found. Create a .env file with "
        "AIRTABLE_API_KEY=<their_token_here> before uploading to Airtable."
    )

TABLES: Dict[str, Dict[str, Any]] = {
    "properties": {
        "base_id": "app3Aa7p8C1dOZAyc",
        "table": "Properties",
        "fields": PROPERTY_FIELDS,
        "display_fields": ("Full Address", "Property Id", "Seller Name"),
    },
    "sellers": {
        "base_id": "appOZysJe5NuxTXO6",
        "table": "Sellers",
        "fields": SELLER_FIELDS,
        "display_fields": ("Full Name", "Seller Name"),
    },
    "mortgage": {
        "base_id": "appuYvtpFqYJpXiBM",
        "table": "Mortgage",
        "fields": MORTGAGE_FIELDS,
        "display_fields": ("Lender Name", "Mortgage Position"),
    },
    "companies": {
        "base_id": "app21RPKrr0JIg4Ea",
        "table": "Companies",
        "fields": COMPANY_FIELDS,
        "display_fields": ("Company Name",),
    },
    "company_contacts": {
        "base_id": "appiysxXpr0dxQe5I",
        "table": "Company Contacts",
        "fields": COMPANY_CONTACT_FIELDS,
        "display_fields": ("Full Name", "Company Name"),
    },
    "phones": {
        "base_id": "app3MqkpxEiHXBKAW",
        "table": "Phone Numbers",
        "fields": PHONE_FIELDS,
        "display_fields": ("Phone Number", "Full Name"),
    },
    "emails": {
        "base_id": "appNFNqvPAK8u5ReT",
        "table": "Email Addresses",
        "fields": EMAIL_FIELDS,
        "display_fields": ("Email Address", "Full Name"),
    },
    "aod": {
        "base_id": "appdI9MeNwQBob0IC",
        "table": "AOD",
        "fields": AOD_FIELDS,
        "display_fields": ("Document Title", "Primary Party Name"),
    },
    "probate": {
        "base_id": "appzYqD6j9MzJuxiO",
        "table": "Probate",
        "fields": PROBATE_FIELDS,
        "display_fields": ("Document Title", "Deceased Or Estate"),
    },
    "liens": {
        "base_id": "appxYsTGMkmd4WAky",
        "table": "Liens",
        "fields": LIEN_FIELDS,
        "display_fields": ("Document Title", "Primary Party Name"),
    },
    "foreclosure": {
        "base_id": "appQzzDV85go43ITt",
        "table": "Foreclosure",
        "fields": FORECLOSURE_FIELDS,
        "display_fields": ("Document Title", "Default Date"),
    },
    "vacant": {
        "base_id": "appJXK47tV5o7D6UJ",
        "table": "Vacant",
        "fields": None,
        "display_fields": ("Status", "Property Id", "Full Address"),
    },
}

SECTION_KEYS: Dict[str, Sequence[str]] = {
    "properties": ("properties", "property"),
    "sellers": ("sellers", "seller", "owners", "owner"),
    "mortgage": ("mortgage", "mortgages"),
    "companies": ("companies", "company"),
    "company_contacts": ("company_contacts", "contacts"),
    "phones": ("phones", "phone_numbers", "phone"),
    "emails": ("emails", "email_addresses", "email"),
    "aod": ("aod",),
    "probate": ("probate",),
    "liens": ("liens", "lien"),
    "foreclosure": ("foreclosure", "foreclosures"),
    "vacant": ("vacant",),
}


@lru_cache(maxsize=None)
def _get_airtable(base_id: str, table_name: str) -> Airtable:
    return Airtable(base_id, table_name, api_key=API_KEY)


def _extract_section(record: MutableMapping[str, Any], keys: Iterable[str]) -> Any:
    for key in keys:
        if key in record:
            return record[key]
    return None


def _iter_entries(section_payload: Any) -> List[Dict[str, Any]]:
    if section_payload is None:
        return []
    if isinstance(section_payload, list):
        return [entry for entry in section_payload if isinstance(entry, dict)]
    if isinstance(section_payload, dict):
        return [section_payload]
    return []


def _prune_value(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str) and not value.strip():
        return False
    if isinstance(value, (list, tuple, set, dict)) and not value:
        return False
    return True


def _prepare_entry(entry: Dict[str, Any], allowed_fields: Optional[Sequence[str]]) -> Dict[str, Any]:
    prepared: Dict[str, Any] = {}
    for key, value in entry.items():
        if not _prune_value(value):
            continue
        title_key = to_title_case(key) if isinstance(key, str) else key
        if allowed_fields and title_key not in allowed_fields:
            continue
        prepared[title_key] = value
    return prepared


def _identify_entry(entry: Dict[str, Any], display_fields: Sequence[str]) -> str:
    for field in display_fields:
        value = entry.get(field)
        if isinstance(value, list):
            joined = ", ".join(str(item) for item in value if item)
            if joined:
                return joined
        elif value not in (None, "", [], {}):
            return str(value)
    return "Record"


def route_and_upload(record: Dict[str, Any]) -> Dict[str, List[str]]:
    """
    Upload each section of a scraped record to its Airtable base.

    Args:
        record: A dictionary containing nested sections (property, sellers, etc.).

    Returns:
        Dict[str, List[str]]: Airtable record IDs keyed by section.
    """
    if not isinstance(record, dict):
        print("⚠️ Invalid record payload. Expected a dictionary.")
        return {}

    if not API_KEY:
        print(
            "⚠️ AIRTABLE_API_KEY missing. Unable to upload. "
            "Add it to your .env file as AIRTABLE_API_KEY=<their_token_here>."
        )
        return {}

    results: Dict[str, List[str]] = {}

    for section, config in TABLES.items():
        payload = _extract_section(record, SECTION_KEYS.get(section, (section,)))
        entries = _iter_entries(payload)
        if not entries:
            continue

        allowed_fields: Optional[Sequence[str]] = config.get("fields")
        display_fields: Sequence[str] = config.get("display_fields", ("Record",))

        for entry in entries:
            prepared = _prepare_entry(entry, allowed_fields)
            if not prepared:
                print(f"⚠️ No valid fields to upload for {config['table']}.")
                continue

            try:
                airtable = _get_airtable(config["base_id"], config["table"])
                response = airtable.insert(prepared)
                record_id = response.get("id") if isinstance(response, dict) else None
                label = _identify_entry(prepared, display_fields)
                if record_id:
                    print(f"✅ Uploaded to {config['table']}: {label}")
                    results.setdefault(section, []).append(record_id)
                else:
                    print(f"⚠️ Upload failed for {config['table']}: No record ID returned.")
            except Exception as exc:  # pragma: no cover - network failure paths
                print(f"⚠️ Upload failed for {config['table']}: {exc}")

    return results
