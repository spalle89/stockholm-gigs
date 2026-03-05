import json
import os
import requests
from datetime import date

SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://kfqipfsywnecuceziiiy.supabase.co")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "")

HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=minimal"
}

def get_existing_first_seen():
    """Fetch all existing event_key -> first_seen mappings."""
    resp = requests.get(
        f"{SUPABASE_URL}/rest/v1/events?select=event_key,first_seen&limit=10000",
        headers=HEADERS
    )
    resp.raise_for_status()
    return {row["event_key"]: row["first_seen"] for row in resp.json() if row.get("event_key")}

def clear_events():
    resp = requests.delete(
        f"{SUPABASE_URL}/rest/v1/events?id=gte.0",
        headers=HEADERS
    )
    resp.raise_for_status()
    print("✓ Cleared existing events")

def push_events(events, batch_size=100):
    total = len(events)
    inserted = 0
    for i in range(0, total, batch_size):
        batch = events[i:i + batch_size]
        resp = requests.post(
            f"{SUPABASE_URL}/rest/v1/events",
            headers=HEADERS,
            json=batch
        )
        if resp.status_code not in (200, 201):
            print(f"  ✗ Batch {i//batch_size + 1} failed: {resp.status_code} {resp.text}")
            continue
        inserted += len(batch)
        print(f"  Inserted batch {i//batch_size + 1} ({inserted}/{total})")
    return inserted

def main():
    if not os.path.exists("events_all.json"):
        print("✗ events_all.json not found — run merge_events.py first")
        return

    with open("events_all.json", encoding="utf-8") as f:
        events = json.load(f)

    print(f"Loaded {len(events)} events from events_all.json")

    # Fetch existing first_seen dates before clearing
    print("Fetching existing first_seen dates...")
    existing = get_existing_first_seen()
    print(f"  Found {len(existing)} existing events")

    today = date.today().isoformat()
    new_count = 0

    # Add event_key and first_seen to each event
    for e in events:
        key = f"{e['venue']}::{e['artist']}::{e['date']}"
        e["event_key"] = key
        if key in existing:
            e["first_seen"] = existing[key]  # preserve original first_seen
        else:
            e["first_seen"] = today  # new event
            new_count += 1

    print(f"  {new_count} new events this week")

    # Clear and re-insert
    clear_events()
    inserted = push_events(events)

    print(f"\n✓ Done — {inserted} events pushed to Supabase ({new_count} new)")

if __name__ == "__main__":
    main()