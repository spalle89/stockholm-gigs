import requests
from bs4 import BeautifulSoup
import json
import re
from datetime import datetime

URL = "https://www.brygghuset.se/live/events"

MONTH_MAP = {
    "jan": "January", "feb": "February", "mar": "March", "apr": "April",
    "maj": "May", "jun": "June", "jul": "July", "aug": "August",
    "sep": "September", "okt": "October", "nov": "November", "dec": "December"
}

def parse_date(date_str):
    """Parse '06•mar•2026' -> (6, 'March', 2026)"""
    m = re.match(r"(\d{1,2})•(\w+)•(\d{4})", date_str.strip())
    if not m:
        return None, None, None
    day, month_sv, year = int(m.group(1)), m.group(2)[:3].lower(), int(m.group(3))
    month_en = MONTH_MAP.get(month_sv)
    if not month_en:
        return None, None, None
    return day, month_en, year

def scrape():
    resp = requests.get(URL, headers={"User-Agent": "Mozilla/5.0"})
    resp.encoding = "utf-8"
    soup = BeautifulSoup(resp.text, "html.parser")

    events = []
    seen = set()

    for card in soup.find_all("a", href=True):
        href = card.get("href", "")
        if "brygghuset.se" not in href:
            continue

        # Skip nav/utility links
        skip_paths = ["/event", "/moten", "/cowork", "/live", "/delibaren",
                      "/om-oss", "/kontakta", "/kickoff", "/integritet"]
        if any(href.rstrip("/").endswith(p) for p in skip_paths):
            continue

        h3 = card.find("h3")
        if not h3:
            continue
        artist = h3.get_text(strip=True)
        if artist in seen:
            continue

        texts = [t.strip() for t in card.stripped_strings if t.strip()]
        date_raw = next((t for t in texts if re.search(r"•", t) and re.search(r"\d{4}", t)), "")
        if not date_raw:
            continue

        # Skip past events section
        if "Passerat" in texts:
            continue

        day, month, year = parse_date(date_raw)
        if not day:
            continue

        seen.add(artist)
        events.append({
            "artist": artist,
            "day": day,
            "month": month,
            "year": year,
            "venue": "Brygghuset",
            "event_url": href,
            "ticket_url": href,
        })

    print(f"[Brygghuset] Extracted {len(events)} events")
    with open("events_brygghuset.json", "w", encoding="utf-8") as f:
        json.dump(events, f, ensure_ascii=False, indent=2)
    print("Saved to events_brygghuset.json")
    for e in events:
        print(f"  {e['day']} {e['month']} {e['year']} | {e['artist']}")

if __name__ == "__main__":
    scrape()