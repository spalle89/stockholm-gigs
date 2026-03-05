import json
import re
import requests
from bs4 import BeautifulSoup

BASE_URL = "https://nalen.com"
PROGRAM_URL = "https://nalen.com/sv/konserter-event"

MONTH_MAP = {
    "jan": "January", "feb": "February", "mars": "March", "apr": "April",
    "maj": "May", "juni": "June", "juli": "July", "aug": "August",
    "sep": "September", "okt": "October", "nov": "November", "dec": "December"
}

def parse_date(raw: str) -> dict:
    """Parse Nalen date strings like '07 mars' or '01 maj' into parts."""
    raw = raw.strip().lower()
    parts = raw.split()
    day = ""
    month = ""
    year = "2026"  # default; update if multi-year
    for p in parts:
        if p.isdigit():
            if len(p) == 4:
                year = p
            else:
                day = p.zfill(2)
        elif p.rstrip(".") in MONTH_MAP:
            month = MONTH_MAP[p.rstrip(".")]
    return {"day": day, "month": month, "year": year,
            "date": f"{day} {month} {year}".strip()}

def scrape_nalen():
    headers = {"User-Agent": "Mozilla/5.0 (compatible; StockholmGigsScraper/1.0)"}
    resp = requests.get(PROGRAM_URL, headers=headers, timeout=30)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    events = []

    # Each event is an <a> tag linking to /sv/konsert/...
    # that contains an img, artist name, support, price, and date
    event_links = soup.select("a[href*='/sv/konsert/']")
    print(f"Found {len(event_links)} event links")

    seen_urls = set()
    for link in event_links:
        href = link.get("href", "")
        if href in seen_urls:
            continue
        seen_urls.add(href)

        event_url = BASE_URL + href if href.startswith("/") else href

        # Image alt often contains artist + date info
        img = link.find("img")
        img_alt = img.get("alt", "") if img else ""

        # Get all text nodes, clean up
        texts = [t.strip() for t in link.stripped_strings]

        if not texts:
            continue

        # Artist name: usually first text block
        artist = texts[0] if texts else ""

        # Support act: second text line if it doesn't look like a price or date
        support = ""
        price = ""
        date_str = ""

        for t in texts[1:]:
            if re.match(r'^\d{1,2}\s+\w', t):  # looks like a date: "07 mars"
                date_str = t
            elif re.match(r'^\d{2,4}', t) and 'SEK' in t:  # price
                price = t
            elif t in ("UTSÅLT", "FÅTAL KVAR", "FÅTAL BORD KVAR", "TABLE"):
                pass  # sale status, skip
            elif t == "+ service":
                pass
            elif not support and t and t != artist:
                support = t

        date_parts = parse_date(date_str) if date_str else {"day": "", "month": "", "year": "", "date": ""}

        if artist:
            events.append({
                "artist": artist,
                "support": support,
                "date": date_parts["date"],
                "day": date_parts["day"],
                "month": date_parts["month"],
                "year": date_parts["year"],
                "price": price,
                "venue": "Nalen",
                "event_url": event_url,
                "ticket_url": event_url,  # Nalen sells tickets on their own event page
                "source": "Nalen"
            })

    print(f"Extracted {len(events)} events")

    with open("events_nalen.json", "w", encoding="utf-8") as f:
        json.dump(events, f, ensure_ascii=False, indent=2)
    print("Saved to events_nalen.json")

    for e in events[:5]:
        print(f"  {e['date']} | {e['artist']}" + (f" + {e['support']}" if e['support'] else ""))

    return events

if __name__ == "__main__":
    scrape_nalen()