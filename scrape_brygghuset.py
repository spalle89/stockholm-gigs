import requests
from bs4 import BeautifulSoup
import json
import re

URL = "https://www.brygghuset.se/live/events"

MONTH_MAP = {
    "jan": "January", "feb": "February", "mar": "March", "apr": "April",
    "maj": "May", "jun": "June", "jul": "July", "aug": "August",
    "sep": "September", "okt": "October", "nov": "November", "dec": "December"
}

MONTH_NAME_TO_EN = {
    "januari": "January", "februari": "February", "mars": "March", "april": "April",
    "maj": "May", "juni": "June", "juli": "July", "augusti": "August",
    "september": "September", "oktober": "October", "november": "November", "december": "December"
}

def parse_date(date_str):
    """Parse various Swedish date formats into (day, month_en, year)."""
    # E.g. '18•apr.•2026', '22•mar•2026', '06•mar•2026'
    m = re.search(r"(\d{1,2})[•/.\s]+([a-zA-ZåäöÅÄÖ]+)\.?\s*[•/.\s]+(\d{4})", date_str.strip())
    if m:
        day = int(m.group(1))
        month_sv = m.group(2).lower()[:3]
        year = int(m.group(3))
        month_en = MONTH_MAP.get(month_sv) or MONTH_NAME_TO_EN.get(month_sv)
        if month_en:
            return day, month_en, year

    # E.g. '13/6-2026' or '13/6 2026'
    m = re.search(r"(\d{1,2})/(\d{1,2})[-_ ](\d{4})", date_str.strip())
    if m:
        day = int(m.group(1))
        month_num = int(m.group(2))
        year = int(m.group(3))
        months = ["", "January", "February", "March", "April", "May", "June",
                  "July", "August", "September", "October", "November", "December"]
        if 1 <= month_num <= 12:
            return day, months[month_num], year

    # E.g. 'feb2025' or '11okt2025'
    m = re.search(r"(\d{1,2})?([a-zA-ZåäöÅÄÖ]{3,})\.?(\d{4})", date_str.strip())
    if m:
        day = int(m.group(1)) if m.group(1) else 1
        month_sv = m.group(2).lower()[:3]
        year = int(m.group(3))
        month_en = MONTH_MAP.get(month_sv) or MONTH_NAME_TO_EN.get(month_sv)
        if month_en:
            return day, month_en, year

    return None, None, None

def scrape():
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    events = []
    seen = set()

    for page in range(1, 6):
        page_url = f"{URL}?page={page}"
        try:
            resp = requests.get(page_url, headers=headers, timeout=10)
            resp.encoding = "utf-8"
        except Exception as err:
            print(f"[Brygghuset] Error fetching page {page}: {err}")
            continue

        soup = BeautifulSoup(resp.text, "html.parser")
        articles = soup.find_all("article")
        if not articles:
            break

        page_has_new = False
        for art in articles:
            h3 = art.find(["h3", "h4"])
            if not h3:
                continue
            artist = h3.get_text(strip=True)
            if not artist or artist in seen:
                continue

            a_tag = art.find("a", href=True)
            if not a_tag:
                continue
            href = a_tag["href"]
            if href.startswith("/"):
                href = "https://www.brygghuset.se" + href

            # Fetch detail page to extract date
            day, month, year = None, None, None
            try:
                e_resp = requests.get(href, headers=headers, timeout=10)
                e_resp.encoding = "utf-8"
                e_soup = BeautifulSoup(e_resp.text, "html.parser")
                body_text = e_soup.get_text()

                m = re.search(r"(\d{1,2}\s*[•/.]\s*[a-zA-ZåäöÅÄÖ]+\.?\s*[•/.]\s*\d{4})", body_text)
                if m:
                    day, month, year = parse_date(m.group(1))
            except Exception as err:
                print(f"[Brygghuset] Error fetching detail page {href}: {err}")

            if not day:
                # Fallback: try parsing from artist title or href
                day, month, year = parse_date(artist)
                if not day:
                    day, month, year = parse_date(href)

            if not day or not month or not year:
                print(f"[Brygghuset] ⚠ Could not parse date for '{artist}' ({href})")
                continue

            seen.add(artist)
            page_has_new = True
            events.append({
                "artist": artist,
                "day": day,
                "month": month,
                "year": year,
                "venue": "Brygghuset",
                "event_url": href,
                "ticket_url": href,
            })

        if not page_has_new:
            break

    print(f"[Brygghuset] Extracted {len(events)} events")
    with open("events_brygghuset.json", "w", encoding="utf-8") as f:
        json.dump(events, f, ensure_ascii=False, indent=2)
    print("Saved to events_brygghuset.json")
    for e in events[:10]:
        print(f"  {e['day']} {e['month']} {e['year']} | {e['artist']}")

if __name__ == "__main__":
    scrape()
