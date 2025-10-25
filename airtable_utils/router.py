# airtable_utils/router.py
import os
import time
from pyairtable import Table
from pathlib import Path
from dotenv import load_dotenv
from mappings import (
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
    to_title_case
)

load_dotenv()

AIRTABLE_KEY = os.getenv("AIRTABLE_API_KEY")
LEADS_BASE = os.getenv("LEADS_CONVOS_BASE")

# Map each field group to its table name
TABLE_MAP = {
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
}


def clean_record_fields(record):
    """Standardize and title-case fields."""
    clean = {}
    for k, v in record.items():
        if v in [None, ""]:
            continue
        clean[to_title_case(k)] = v
    return clean


def upload_to_airtable(table_name, record, retries=3):
    """Upload one record to Airtable with retries."""
    try:
        table = Table(AIRTABLE_KEY, LEADS_BASE, table_name)
        table.create(record)
        print(f"✅ Uploaded to {table_name}: {record.get('Full Address') or record.get('Property Address')}")
        return True
    except Exception as e:
        print(f"⚠️ Error uploading to {table_name}: {e}")
        if retries > 0:
            time.sleep(2)
            return upload_to_airtable(table_name, record, retries - 1)
        return False
    
    LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)
LOG_PATH = LOG_DIR / f"uploads_{time.strftime('%Y%m%d_%H%M%S')}.log"

def _log(line: str):
    print(line)
    with LOG_PATH.open("a", encoding="utf-8") as f:
        f.write(line + "\n")


def route_and_upload(record):
    """Automatically detect table type and upload."""
    uploaded = {}

    # Clean the record keys
    record = clean_record_fields(record)
    record_keys = set(record.keys())

    for table_name, fields in TABLE_MAP.items():
        if any(f in record_keys for f in fields):
            subset = {k: v for k, v in record.items() if k in fields}
            if subset:
                uploaded[table_name] = upload_to_airtable(table_name, subset)

    # Optional: Batch Upload Support
def batch_upload(records, batch_size=10):
    from itertools import islice
    records = list(records)
    total = len(records)
    print(f"🚀 Batch uploading {total} records...")

    for i in range(0, total, batch_size):
        chunk = records[i:i+batch_size]
        for rec in chunk:
            route_and_upload(rec)
        time.sleep(1)

    return uploaded