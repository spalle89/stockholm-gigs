import json
import os
from datetime import datetime

FILES = {
    "Fasching":           "events_fasching.json",
    "Debaser":            "events_debaser.json",
    "Nalen":              "events_nalen.json",
    "Södra Teatern":      "events_sodra_teatern.json",
    "Fållan":             "events_fallan.json",
    "B-K":                "events_bk.json",
    "Berns":              "events_berns.json",
    "Brygghuset":         "events_brygghuset.json",
    "Annexet":            "events_annexet.json",
    "Kollektivet Livet":  "events_kollektivet_livet.json",
    "Cirkus":             "events_cirkus.json",
}

MONTH_ABBR = {
    "jan": "January", "feb": "February", "mar": "March", "apr": "April",
    "may": "May", "jun": "June", "jul": "July", "aug": "August",
    "sep": "September", "oct": "October", "nov": "November", "dec": "December"
}

def parse_month(m):
    if not m:
        return None
    try:
        return datetime.strptime(m, "%B").month
    except:
        return datetime.strptime(MONTH_ABBR.get(m[:3].lower(), m), "%B").month

def parse_event_date(e):
    try:
        day = int(e.get("day") or 0)
        month = parse_month(e.get("month", ""))
        year = int(e.get("year") or 0)
        if day and month and year:
            return datetime(year, month, day)
    except:
        pass
    try:
        return datetime.strptime(e.get("date", ""), "%Y-%m-%d")
    except:
        pass
    return None

def normalize(e, venue_name):
    """Return a clean, consistent event dict."""
    dt = parse_event_date(e)
    if not dt:
        return None

    # Resolve end_date for multi-night events
    end_dt = None
    if e.get("end_date"):
        try:
            parts = e["end_date"].split()
            end_dt = datetime(int(parts[2]), parse_month(parts[1]), int(parts[0]))
        except:
            pass

    return {
        "artist":    e.get("artist", "").strip(),
        "support":   e.get("support", "").strip(),
        "day":       dt.day,
        "month":     dt.strftime("%B"),
        "year":      dt.year,
        "date":      dt.strftime("%Y-%m-%d"),  # ISO for easy sorting
        "end_date":  end_dt.strftime("%Y-%m-%d") if end_dt else None,
        "venue":     e.get("venue", venue_name).strip(),
        "sub_venue": e.get("sub_venue", "").strip(),
        "genre":     e.get("genre", "").strip(),
        "event_url": e.get("event_url", "").strip(),
        "ticket_url": e.get("ticket_url", "").strip(),
    }

today = datetime.now().date()
all_events = []
skipped_past = 0
skipped_invalid = 0

for venue_name, fname in FILES.items():
    if not os.path.exists(fname):
        print(f"⚠ Skipping {venue_name}: file not found")
        continue

    with open(fname, encoding="utf-8") as f:
        events = json.load(f)

    venue_count = 0
    for e in events:
        norm = normalize(e, venue_name)
        if not norm:
            skipped_invalid += 1
            continue

        # Filter past events (use end_date for multi-night shows)
        end_date = norm["end_date"] or norm["date"]
        if datetime.strptime(end_date, "%Y-%m-%d").date() < today:
            skipped_past += 1
            continue

        all_events.append(norm)
        venue_count += 1

    print(f"  {venue_name:<22} {venue_count} events")

# Sort by date then artist
all_events.sort(key=lambda e: (e["date"], e["artist"]))

# Save
with open("events_all.json", "w", encoding="utf-8") as f:
    json.dump(all_events, f, ensure_ascii=False, indent=2)

print(f"\n✓ Merged {len(all_events)} upcoming events → events_all.json")
print(f"  Skipped {skipped_past} past events, {skipped_invalid} invalid")