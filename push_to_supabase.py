import json
import os
import requests

SUPABASE_URL = "https://kfqipfsywnecuceziiiy.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImtmcWlwZnN5d25lY3VjZXppaWl5Iiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3MjY4OTA5OSwiZXhwIjoyMDg4MjY1MDk5fQ.FIx5Qtzo7rlmfIdMSVtbqCGo78sdfJdyp34IUL7MsRA"

HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=minimal"
}

def clear_events():
    """Delete all existing events before re-inserting."""
    resp = requests.delete(
        f"{SUPABASE_URL}/rest/v1/events?id=gte.0",
        headers=HEADERS
    )
    resp.raise_for_status()
    print("✓ Cleared existing events")

def push_events(events, batch_size=100):
    """Insert events in batches."""
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

    # Clear and re-insert
    clear_events()
    inserted = push_events(events)

    print(f"\n✓ Done — {inserted} events pushed to Supabase")

if __name__ == "__main__":
    main()