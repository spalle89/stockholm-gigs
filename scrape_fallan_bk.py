import requests
from bs4 import BeautifulSoup
import json
import re
from datetime import datetime

MONTH_MAP = {
    "january": "January", "february": "February", "march": "March", "april": "April",
    "may": "May", "june": "June", "july": "July", "august": "August",
    "september": "September", "october": "October", "november": "November", "december": "December"
}

EVENT_TYPES = {"Concert", "Club", "Festival", "Event", "Tickets", "Club Night", "Live"}

VENUES = {
    "Fållan": "https://www.fallan.nu/whats-on",
    "B-K":    "https://www.b-k.se/whats-on",
}

def parse_date(date_str):
    """Parse 'March 6, 2026' -> (6, 'March', 2026)"""
    date_str = date_str.strip()
    m = re.match(r"(\w+)\s+(\d{1,2}),?\s+(\d{4})", date_str)
    if not m:
        return None, None, None
    month_str, day, year = m.group(1), int(m.group(2)), int(m.group(3))
    month_en = MONTH_MAP.get(month_str.lower())
    if not month_en:
        return None, None, None
    return day, month_en, year

def scrape_venue(venue_name, url):
    resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
    resp.encoding = "utf-8"
    soup = BeautifulSoup(resp.text, "html.parser")

    events = []
    seen = set()

    for a in soup.find_all("a", href=re.compile(r"/whats-on/")):
        href = a.get("href", "")
        if href in seen:
            continue

        # Artist: prefer h3, fallback h4, skip h2 event types
        artist = ""
        for tag in ["h3", "h4", "h2"]:
            el = a.find(tag)
            if el:
                text = el.get_text(strip=True)
                if text and text not in EVENT_TYPES:
                    artist = text
                    break
        if not artist:
            continue

        # Date
        texts = [t.strip() for t in a.stripped_strings if t.strip()]
        date_raw = next(
            (t for t in texts if re.match(r"(January|February|March|April|May|June|July|August|September|October|November|December)", t)),
            ""
        )
        if not date_raw:
            continue

        day, month, year = parse_date(date_raw)
        if not day:
            continue

        # Sub-venue (e.g. Fållan / BAR15 / Lilla Fållan)
        sub_venue = ""
        for t in texts:
            if t not in EVENT_TYPES and t != artist and not re.match(r"(January|February)", t):
                if any(v in t for v in ["Fållan", "BAR", "Lilla", "B-K", "Stora", "Lilla"]):
                    sub_venue = t
                    break

        key = f"{artist}_{date_raw}"
        if key in seen:
            continue
        seen.add(key)
        seen.add(href)

        events.append({
            "artist": artist,
            "day": day,
            "month": month,
            "year": year,
            "venue": venue_name,
            "sub_venue": sub_venue,
            "event_url": href,
            "ticket_url": href,
        })

    return events

def scrape():
    for venue_name, url in VENUES.items():
        events = scrape_venue(venue_name, url)
        fname = f"events_{venue_name.lower().replace('-', '_').replace('å', 'a').replace('ä', 'a').replace('ö', 'o')}.json"
        # Use consistent filenames
        fname = "events_fallan.json" if venue_name == "Fållan" else "events_bk.json"
        with open(fname, "w", encoding="utf-8") as f:
            json.dump(events, f, ensure_ascii=False, indent=2)
        print(f"[{venue_name}] Extracted {len(events)} events → {fname}")
        for e in events:
            print(f"  {e['day']} {e['month']} {e['year']} | {e['artist']}")

if __name__ == "__main__":
    scrape()