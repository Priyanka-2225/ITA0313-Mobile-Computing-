"""Battery-aware secure field-tracking prototype (offline simulation).

This educational demo uses sample coordinates and simulated battery/network
conditions. It does not access a device GPS, battery, or real server.
"""
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / "data"
PENDING_FILE = DATA_DIR / "pending_records.json"
SERVER_FILE = DATA_DIR / "server_records.json"

@dataclass
class TrackingRecord:
    record_id: str
    user_id: str
    latitude: float
    longitude: float
    timestamp: str
    battery: int
    sync_status: str = "PENDING"


def battery_state(level: int, charging: bool = False) -> str:
    if charging:
        return "CHARGING"
    if level < 20:
        return "CRITICAL BATTERY"
    if level < 50:
        return "LOW BATTERY"
    return "NORMAL"


def make_record(record_id: str, user_id: str, lat: float, lon: float,
                battery: int) -> TrackingRecord:
    return TrackingRecord(record_id, user_id, lat, lon,
                          datetime.now(timezone.utc).isoformat(timespec="seconds"),
                          battery)


def load_records(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return json.loads(path.read_text(encoding="utf-8"))


def save_records(path: Path, records: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(records, indent=2), encoding="utf-8")


def add_pending(record: TrackingRecord) -> None:
    pending = load_records(PENDING_FILE)
    if any(item["record_id"] == record.record_id for item in pending):
        print(f"Duplicate local record ignored: {record.record_id}")
        return
    pending.append(asdict(record))
    save_records(PENDING_FILE, pending)
    print(f"Saved locally: {record.record_id} ({record.sync_status})")


def synchronize(network_available: bool) -> None:
    if not network_available:
        print("Network unavailable. Records remain safely pending.")
        return
    pending = load_records(PENDING_FILE)
    server = load_records(SERVER_FILE)
    known_ids = {item["record_id"] for item in server}
    uploaded = 0
    duplicates = 0
    for item in pending:
        if item["record_id"] in known_ids:
            duplicates += 1
            continue
        item["sync_status"] = "SYNCED"
        server.append(item)
        known_ids.add(item["record_id"])
        uploaded += 1
    save_records(SERVER_FILE, server)
    save_records(PENDING_FILE, [])
    print(f"Synchronization complete: {uploaded} uploaded, {duplicates} duplicate(s) skipped.")


def run_demo() -> None:
    # Start each demonstration with a clean sample dataset.
    save_records(PENDING_FILE, [])
    save_records(SERVER_FILE, [])
    print("BATTERY-AWARE SECURE FIELD-TRACKING PROTOTYPE")
    print("=" * 48)
    scenarios = [
        ("FT-1001", 65, False, True),
        ("FT-1002", 35, False, False),
        ("FT-1003", 12, False, False),
        ("FT-1004", 78, True, True),
    ]
    for record_id, battery, charging, network in scenarios:
        state = battery_state(battery, charging)
        print(f"\nRecord {record_id}: battery={battery}%, state={state}")
        if state == "CRITICAL BATTERY":
            print("Policy: reduce nonessential tracking; preserve essential data.")
        elif state == "LOW BATTERY":
            print("Policy: batch uploads and reduce background activity.")
        elif state == "CHARGING":
            print("Policy: pending synchronization is allowed.")
        else:
            print("Policy: normal tracking and synchronization when online.")
        record = make_record(record_id, "EMP-101", 13.0827, 80.2707, battery)
        add_pending(record)
        synchronize(network)

    # Demonstrate idempotency: re-submit an ID already stored on the server.
    print("\nDuplicate-upload check")
    duplicate = make_record("FT-1001", "EMP-101", 13.0827, 80.2707, 65)
    save_records(PENDING_FILE, [asdict(duplicate)])
    synchronize(network_available=True)
    print(f"\nFinal server record count: {len(load_records(SERVER_FILE))}")
    print(f"Remaining pending record count: {len(load_records(PENDING_FILE))}")
    print("\nNOTE: This is a local simulation with sample data, not live GPS/device data.")

if __name__ == "__main__":
    run_demo()
