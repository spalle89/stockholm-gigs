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

REQUIRED_FIELDS = ["artist", "day", "month", "year", "venue"]

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

today = datetime.now()
total = 0
issues = []

print(f"{'Venue':<22} {'Events':>6}  {'Missing fields':<22}  {'Past':>5}  Next event")
print("─" * 80)

for venue, fname in FILES.items():
    if not os.path.exists(fname):
        print(f"{venue:<22} {'—':>6}  ⚠ FILE NOT FOUND")
        issues.append(f"{venue}: file not found")
        continue

    try:
        with open(fname, encoding="utf-8") as f:
            content = f.read().strip()
        if not content:
            print(f"{venue:<22} {'—':>6}  ⚠ FILE IS EMPTY")
            issues.append(f"{venue}: file is empty")
            continue
        events = json.loads(content)
    except json.JSONDecodeError as ex:
        print(f"{venue:<22} {'—':>6}  ⚠ INVALID JSON: {ex}")
        issues.append(f"{venue}: invalid JSON")
        continue

    count = len(events)
    total += count
    missing_fields = set()
    past_count = 0
    no_url_count = 0
    next_event = None

    for e in events:
        for field in REQUIRED_FIELDS:
            if not e.get(field):
                if field in ("day", "month", "year") and e.get("date"):
                    continue
                missing_fields.add(field)

        if not e.get("event_url") and not e.get("ticket_url"):
            no_url_count += 1

        dt = parse_event_date(e)
        if dt is None:
            missing_fields.add("invalid date")
            continue

        end_dt = None
        if e.get("end_date"):
            try:
                parts = e["end_date"].split()
                end_dt = datetime(int(parts[2]), parse_month(parts[1]), int(parts[0]))
            except:
                pass

        effective_end = end_dt or dt
        if effective_end.date() < today.date():
            past_count += 1
        elif next_event is None or dt < next_event:
            next_event = dt

    next_str = next_event.strftime("%-d %b %Y") if next_event else "—"

    # Free events legitimately have no URL - not flagged as an issue

    field_str = ", ".join(sorted(missing_fields)) if missing_fields else "✓"
    past_str = str(past_count) if past_count else "✓"

    print(f"{venue:<22} {count:>6}  {field_str:<22}  {past_str:>5}  {next_str}")

    if missing_fields:
        issues.append(f"{venue}: {missing_fields}")
    if past_count > 5:
        issues.append(f"{venue}: {past_count} past events")

print("─" * 80)
print(f"{'TOTAL':<22} {total:>6}")

if issues:
    print(f"\n⚠ Issues:")
    for i in issues:
        print(f"  • {i}")
else:
    print(f"\n✓ All good!")