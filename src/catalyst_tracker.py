"""
Catalyst tracking: load/save status, fire/reset catalysts, print dashboards.

CLI (via scripts/catalyst_check.py):
  python scripts/catalyst_check.py                   # show all
  python scripts/catalyst_check.py --fire PCB "GB300/Rubin放量" "confirmed in earnings"
  python scripts/catalyst_check.py --miss PCB "GB300/Rubin放量" "delayed to Q4"
  python scripts/catalyst_check.py --reset PCB "GB300/Rubin放量"
"""

import json
from datetime import date
from pathlib import Path

STATUS_FILE = Path(__file__).parent.parent / "data" / "catalyst_status.json"

STATUS_SYMBOLS = {"pending": "⏳", "fired": "✅", "missed": "❌"}


def _load() -> dict:
    with open(STATUS_FILE) as f:
        return json.load(f)


def _save(data: dict):
    with open(STATUS_FILE, "w") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _find(data: dict, sector: str, text: str):
    for item in data.get(sector, []):
        if item["text"] == text:
            return item
    return None


def fire(sector: str, text: str, notes: str = ""):
    data = _load()
    item = _find(data, sector, text)
    if item is None:
        raise ValueError(f"Catalyst not found: [{sector}] {text}")
    item["status"] = "fired"
    item["fired_date"] = str(date.today())
    if notes:
        item["notes"] = notes
    _save(data)
    print(f"✅ Fired: [{sector}] {text}")


def miss(sector: str, text: str, notes: str = ""):
    data = _load()
    item = _find(data, sector, text)
    if item is None:
        raise ValueError(f"Catalyst not found: [{sector}] {text}")
    item["status"] = "missed"
    item["fired_date"] = str(date.today())
    if notes:
        item["notes"] = notes
    _save(data)
    print(f"❌ Missed: [{sector}] {text}")


def reset(sector: str, text: str):
    data = _load()
    item = _find(data, sector, text)
    if item is None:
        raise ValueError(f"Catalyst not found: [{sector}] {text}")
    item["status"] = "pending"
    item["fired_date"] = None
    _save(data)
    print(f"⏳ Reset: [{sector}] {text}")


def summary() -> dict:
    """Return {total, fired, missed, pending} counts."""
    data = _load()
    counts = {"total": 0, "fired": 0, "missed": 0, "pending": 0}
    for sector, items in data.items():
        if sector.startswith("_"):
            continue
        for item in items:
            counts["total"] += 1
            counts[item["status"]] += 1
    return counts


def print_dashboard(filter_status: str = None):
    data = _load()

    col_w = [10, 26, 8, 12, 30]
    header = f"{'Sector':<{col_w[0]}}  {'Catalyst':<{col_w[1]}}  {'Status':<{col_w[2]}}  {'Date':<{col_w[3]}}  {'Notes'}"
    sep = "─" * (sum(col_w) + 10)

    print()
    print("  CATALYST TRACKER — 2026 Long-Short Pairs")
    print(sep)
    print(header)
    print(sep)

    for sector, items in data.items():
        if sector.startswith("_"):
            continue
        for item in items:
            st = item["status"]
            if filter_status and st != filter_status:
                continue
            sym = STATUS_SYMBOLS.get(st, "?")
            fired = item.get("fired_date") or "—"
            notes = item.get("notes") or ""
            print(
                f"{sector:<{col_w[0]}}  "
                f"{item['text']:<{col_w[1]}}  "
                f"{sym} {st:<{col_w[2]-2}}  "
                f"{fired:<{col_w[3]}}  "
                f"{notes}"
            )

    print(sep)
    c = summary()
    print(f"  Total {c['total']}  |  ✅ Fired {c['fired']}  |  ⏳ Pending {c['pending']}  |  ❌ Missed {c['missed']}")
    print()
