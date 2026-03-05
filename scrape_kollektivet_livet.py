import requests
from bs4 import BeautifulSoup
import json
import re
from datetime import datetime, timedelta

BASE_URL = "https://stadsgardsterminalen.com"
URL = "https://stadsgardsterminalen.com/program/"

MONTH_MAP = {
    "jan": "January", "feb": "February", "mar": "March", "apr": "April",
    "maj": "May", "jun": "June", "jul": "July", "aug": "August",
    "sep": "September", "okt": "October", "nov": "November", "dec": "December"
}

WEEKDAYS = {"mån", "tis", "ons", "tor", "fre", "lör", "sön"}

def parse_date(date_str):
    """
    Parse Swedish date strings like:
    - 'tors 12 mars'
    - 'lör 7 mars till sön 8 mars'
    - 'Idag'
    - 'Imorgon till lör 7 mars'
    Returns (day, month_en, year) for start date
    """
    today = datetime.now()
    date_str = date_str.strip().lower()

    if date_str == "idag":
        return today.day, today.strftime("%B"), today.year

    if date_str.startswith("imorgon"):
        tomorrow = today + timedelta(days=1)
        return tomorrow.day, tomorrow.strftime("%B"), tomorrow.year

    # Extract first date occurrence: optional weekday + day + month
    m = re.search(r"(\d{1,2})\s+(jan|feb|mar|apr|maj|jun|jul|aug|sep|okt|nov|dec)", date_str)
    if m:
        day = int(m.group(1))
        month_sv = m.group(2)[:3]
        month_en = MONTH_MAP.get(month_sv)
        if not month_en:
            return None, None, None
        # Determine year: if month is earlier than current month, assume next year
        month_num = list(MONTH_MAP.keys()).index(month_sv) + 1
        year = today.year if month_num >= today.month else today.year + 1
        return day, month_en, year

    return None, None, None

def scrape():
    resp = requests.get(URL, headers={"User-Agent": "Mozilla/5.0"})
    resp.encoding = "utf-8"
    soup = BeautifulSoup(resp.text, "html.parser")

    events = []
    seen = set()

    # Each event card: image, date text, sub-venue, h3 artist, ticket link
    # Cards are linked via <a href="/event/...">
    for card in soup.select("a[href*='/event/']"):
        href = card.get("href", "")
        if not href or href in seen:
            continue
        seen.add(href)

        h3 = card.find("h3")
        if not h3:
            continue
        artist = h3.get_text(strip=True)

        # Date: look for text with day+month pattern or Idag/Imorgon
        all_text = [t.strip() for t in card.stripped_strings if t.strip()]
        date_raw = None
        for t in all_text:
            tl = t.lower()
            if tl in ("idag", "imorgon") or re.search(r"\d{1,2}\s+(jan|feb|mar|apr|maj|jun|jul|aug|sep|okt|nov|dec)", tl):
                date_raw = t
                break

        if not date_raw:
            continue

        day, month, year = parse_date(date_raw)
        if not day:
            continue

        # Sub-venue (Stora Scen / Lilla Scen)
        sub_venue = ""
        for t in all_text:
            if "scen" in t.lower() or "kollektivet" in t.lower():
                sub_venue = t
                break

        # Ticket link
        ticket_a = card.find("a", href=re.compile(r"tickster|ticketmaster|blackplanet"))
        ticket_url = ticket_a["href"] if ticket_a else BASE_URL + href

        events.append({
            "artist": artist,
            "day": day,
            "month": month,
            "year": year,
            "venue": "Kollektivet Livet",
            "sub_venue": sub_venue,
            "event_url": BASE_URL + href if href.startswith("/") else href,
            "ticket_url": ticket_url,
        })

    print(f"[Kollektivet Livet] Extracted {len(events)} events")
    with open("events_kollektivet_livet.json", "w", encoding="utf-8") as f:
        json.dump(events, f, ensure_ascii=False, indent=2)
    print("Saved to events_kollektivet_livet.json")
    for e in events:
        print(f"  {e['day']} {e['month']} {e['year']} | {e['artist']} ({e['sub_venue']})")

if __name__ == "__main__":
    scrape()