import json
import re
import requests
from bs4 import BeautifulSoup

BASE_URL = "https://berns.se"
CALENDAR_URL = "https://berns.se/calendar/"

MONTH_MAP = {
    "january": "January", "february": "February", "march": "March",
    "april": "April", "may": "May", "june": "June", "july": "July",
    "august": "August", "september": "September", "october": "October",
    "november": "November", "december": "December",
}

def parse_date(raw: str) -> dict:
    """Parse '06 March 2026' style dates."""
    tokens = raw.strip().split()
    day, month, year = "", "", ""
    for t in tokens:
        if t.isdigit() and len(t) <= 2:
            day = t.zfill(2)
        elif t.isdigit() and len(t) == 4:
            year = t
        elif t.lower() in MONTH_MAP:
            month = MONTH_MAP[t.lower()]
    return {"day": day, "month": month, "year": year,
            "date": f"{day} {month} {year}".strip()}

def scrape_berns():
    headers = {"User-Agent": "Mozilla/5.0 (compatible; StockholmGigsScraper/1.0)"}
    resp = requests.get(CALENDAR_URL, headers=headers, timeout=30)
    resp.raise_for_status()
    resp.encoding = "utf-8"
    soup = BeautifulSoup(resp.text, "html.parser")

    events = []
    seen = set()

    # Each event block: <a href="/calendar/<slug>"> wrapping image
    # followed by date text and <h5> artist name
    # Structure observed:
    #   <a href="/calendar/kerstin-ljungstrom/"> <img> </a>
    #   06 March 2026
    #   <a href="...">Explore</a> | ...
    #   <h5>Kerstin Ljungström</h5>

    # Find all calendar event containers — look for h5 tags near date text
    # The pattern: date string text node + h5 sibling
    event_links = soup.select("a[href*='/calendar/']")
    print(f"Found {len(event_links)} calendar links")

    for link in event_links:
        href = link.get("href", "")
        # Skip nav/footer links that just point to /calendar/
        if href.rstrip("/") == "/calendar" or href.rstrip("/") == BASE_URL + "/calendar":
            continue
        if href in seen:
            continue
        seen.add(href)

        event_url = BASE_URL + href if href.startswith("/") else href

        # Walk up to find the container, then look for date and h5
        container = link.parent
        for _ in range(4):
            if container is None:
                break
            # Look for h5 (artist name) in this container or its siblings
            h5 = container.find("h5")
            if h5:
                break
            container = container.parent

        if not container:
            continue

        artist_el = container.find("h5")
        artist = artist_el.get_text(strip=True) if artist_el else ""
        if not artist:
            continue

        # Date: look for text matching day + month + year pattern nearby
        date_raw = ""
        all_text = container.get_text(" ", strip=True)
        date_match = re.search(r'(\d{1,2}\s+\w+\s+\d{4})', all_text)
        if date_match:
            date_raw = date_match.group(1)

        date_parts = parse_date(date_raw) if date_raw else {"day": "", "month": "", "year": "", "date": ""}

        # Ticket URL: look for Explore link (event detail page has ticket link)
        explore_link = container.find("a", string=re.compile(r'Explore', re.I))
        ticket_url = (BASE_URL + explore_link["href"] if explore_link and explore_link.get("href", "").startswith("/")
                      else event_url)

        events.append({
            "artist": artist,
            "date": date_parts["date"],
            "day": date_parts["day"],
            "month": date_parts["month"],
            "year": date_parts["year"],
            "venue": "Berns",
            "event_url": event_url,
            "ticket_url": ticket_url,
            "source": "Berns",
        })

    print(f"Extracted {len(events)} events")
    with open("events_berns.json", "w", encoding="utf-8") as f:
        json.dump(events, f, ensure_ascii=False, indent=2)
    print("Saved to events_berns.json")
    for e in events:
        print(f"  {e['date']} | {e['artist']}")
    return events

if __name__ == "__main__":
    scrape_berns()