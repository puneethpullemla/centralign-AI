import json
import os
from threading import Lock
from typing import Dict, Any, List, Optional


BASE_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..")
)

DATA_DIR = os.path.join(BASE_DIR, "data")
STORE_FILE = os.path.join(DATA_DIR, "billing_records.json")

_lock = Lock()


def _ensure_store():
    os.makedirs(DATA_DIR, exist_ok=True)

    if not os.path.exists(STORE_FILE):
        with open(STORE_FILE, "w", encoding="utf-8") as f:
            json.dump([], f)


def _read_records() -> List[Dict[str, Any]]:
    _ensure_store()

    with open(STORE_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def _write_records(records: List[Dict[str, Any]]):
    _ensure_store()

    with open(STORE_FILE, "w", encoding="utf-8") as f:
        json.dump(records, f, indent=2, ensure_ascii=False)


def get_records() -> List[Dict[str, Any]]:
    with _lock:
        return _read_records()


def find_by_invoice(invoice_id: str) -> Optional[Dict[str, Any]]:
    invoice_id = invoice_id.strip().lower()

    with _lock:
        records = _read_records()

        for record in records:
            if record.get("invoice_id", "").strip().lower() == invoice_id:
                return record

    return None


def create_record(
    company: str,
    invoice_id: str,
    amount: str,
    due_date: str
) -> Dict[str, Any]:

    with _lock:
        records = _read_records()

        # Prevent duplicate invoice records
        for record in records:
            if record.get("invoice_id", "").strip().lower() == invoice_id.strip().lower():
                return record

        next_number = 7840

        if records:
            numbers = []

            for record in records:
                record_id = record.get("record_id", "")

                if record_id.startswith("BILL-"):
                    try:
                        numbers.append(int(record_id.replace("BILL-", "")))
                    except ValueError:
                        pass

            if numbers:
                next_number = max(numbers) + 1

        record = {
            "record_id": f"BILL-{next_number}",
            "invoice_id": invoice_id,
            "company": company,
            "amount": amount,
            "due_date": due_date,
            "status": "COMMITTED"
        }

        records.append(record)
        _write_records(records)

        return record