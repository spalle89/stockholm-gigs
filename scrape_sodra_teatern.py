import json
import re
import requests
from bs4 import BeautifulSoup

BASE_URL = "https://sodrateatern.com"
EVENTS_URL = "https://sodrateatern.com/en/events/music-show/"

MONTH_MAP = {
    "january": "January", "february": "February", "march": "March",
    "april": "April", "may": "May", "june": "June", "july": "July",
    "august": "August", "september": "September", "october": "October",
    "november": "November", "december": "December"
}

def parse_date_range(raw: str) -> list[dict]:
    """
    Parse strings like:
      'March 5, 2026'
      'March 5 - March 29, 2026'
      'April 18 - April 19, 2026'
    Returns a list of date dicts (one per date in range).
    """
    raw = raw.strip()
    year_match = re.search(r'\d{4}', raw)
    year = year_match.group() if year_match else "2026"

    # Remove year for easier parsing
    raw_no_year = re.sub(r',?\s*\d{4}', '', raw).strip()

    # Split on ' - ' for ranges
    parts = [p.strip() for p in raw_no_year.split(' - ')]

    dates = []
    for part in parts:
        tokens = part.split()
        month = ""
        day = ""
        for t in tokens:
            tl = t.lower().rstrip(',')
            if tl in MONTH_MAP:
                month = MONTH_MAP[tl]
            elif t.isdigit():
                day = t.zfill(2)
        if day and month:
            dates.append({
                "day": day,
                "month": month,
                "year": year,
                "date": f"{day} {month} {year}"
            })

    return dates if dates else [{"day": "", "month": "", "year": year, "date": raw}]


def scrape_sodra_teatern():
    headers = {"User-Agent": "Mozilla/5.0 (compatible; StockholmGigsScraper/1.0)"}
    resp = requests.get(EVENTS_URL, headers=headers, timeout=30)
    resp.raise_for_status()
    resp.encoding = "utf-8"
    soup = BeautifulSoup(resp.text, "html.parser")

    events = []

    # Each event card is an <article> or a container with a heading + date + ticket link
    # From the HTML structure observed: events are in card-like blocks with:
    # - a date text node
    # - h3 for artist
    # - p or span for subtitle
    # - text for stage
    # - <a> "Buy ticket" with href to tickster

    # Try to find all event card containers
    # They seem to be siblings under a listing container
    # Look for elements containing "Buy ticket" links
    ticket_links = soup.select("a[href*='tickster.com']")
    print(f"Found {len(ticket_links)} ticket links")

    seen = set()
    for link in ticket_links:
        ticket_url = link.get("href", "")

        # Walk up to find the card container
        card = link.parent
        for _ in range(6):
            if card is None:
                break
            # Look for a heading inside
            heading = card.find(["h2", "h3", "h4"])
            if heading:
                break
            card = card.parent

        if not card:
            continue

        # Artist name from heading
        heading = card.find(["h2", "h3", "h4"])
        artist = heading.get_text(strip=True) if heading else ""

        if not artist or artist in seen:
            continue
        seen.add(artist)

        # All text in the card
        texts = [t.strip() for t in card.stripped_strings if t.strip()]

        # Date: look for pattern like "March 5, 2026" or "March 5 - March 29, 2026"
        date_raw = ""
        subtitle = ""
        stage = ""
        for t in texts:
            if re.match(r'(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d', t):
                date_raw = t
            elif t in ("Music/show", "Sport", "Comedy/Talks", "Buy ticket"):
                pass
            elif any(s in t for s in ("Kägelbanan", "Main Stage", "Mosebacke")):
                stage = " ".join(t.split())
            elif t != artist and not date_raw and not t.startswith("http"):
                if not subtitle:
                    subtitle = t

        dates = parse_date_range(date_raw) if date_raw else [{"day": "", "month": "", "year": "", "date": ""}]

        # For multi-date events, create one entry per date
        for d in dates:
            events.append({
                "artist": artist,
                "subtitle": subtitle,
                "date": d["date"],
                "day": d["day"],
                "month": d["month"],
                "year": d["year"],
                "stage": stage,
                "venue": "Södra Teatern",
                "ticket_url": ticket_url,
                "event_url": ticket_url,
                "source": "Södra Teatern"
            })

    print(f"Extracted {len(events)} events")

    with open("events_sodra_teatern.json", "w", encoding="utf-8") as f:
        json.dump(events, f, ensure_ascii=False, indent=2)
    print("Saved to events_sodra_teatern.json")

    for e in events[:5]:
        print(f"  {e['date']} | {e['artist']}" + (f" – {e['subtitle']}" if e['subtitle'] else "") + f" @ {e['stage']}")

    return events


if __name__ == "__main__":
    scrape_sodra_teatern()