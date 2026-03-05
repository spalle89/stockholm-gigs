import requests
from bs4 import BeautifulSoup
import json
import re

URL = "https://annexet.se/evenemang/musik-show/"

MONTH_MAP = {
    "januari": "January", "februari": "February", "mars": "March", "april": "April",
    "maj": "May", "juni": "June", "juli": "July", "augusti": "August",
    "september": "September", "oktober": "October", "november": "November", "december": "December"
}

DATE_RE = re.compile(
    r"(\d{1,2})\s+(januari|februari|mars|april|maj|juni|juli|augusti|september|oktober|november|december)\s+(\d{4})",
    re.IGNORECASE
)

def scrape():
    resp = requests.get(URL, headers={"User-Agent": "Mozilla/5.0"})
    resp.encoding = "utf-8"
    soup = BeautifulSoup(resp.text, "html.parser")

    events = []
    seen = set()

    for h3 in soup.find_all("h3"):
        artist = h3.get_text(strip=True)
        if not artist or artist in seen:
            continue

        # Date and ticket link live exactly 2 levels up from h3
        container = h3.parent.parent if h3.parent else None
        if not container:
            continue

        text = container.get_text(" ", strip=True)
        m = DATE_RE.search(text)
        if not m:
            continue

        day = int(m.group(1))
        month_en = MONTH_MAP.get(m.group(2).lower())
        year = int(m.group(3))
        if not month_en:
            continue

        # Ticket link — must be a proper AXS event URL
        ticket_a = container.find("a", href=re.compile(r"axs\.com/se/events/\d+"))
        ticket_url = ticket_a["href"] if ticket_a else ""

        seen.add(artist)
        events.append({
            "artist": artist,
            "day": day,
            "month": month_en,
            "year": year,
            "venue": "Annexet",
            "event_url": ticket_url,
            "ticket_url": ticket_url,
        })

    print(f"[Annexet] Extracted {len(events)} events")
    with open("events_annexet.json", "w", encoding="utf-8") as f:
        json.dump(events, f, ensure_ascii=False, indent=2)
    print("Saved to events_annexet.json")
    for e in events:
        print(f"  {e['day']} {e['month']} {e['year']} | {e['artist']}")

if __name__ == "__main__":
    scrape()