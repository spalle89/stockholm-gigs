import asyncio
import json
import re
from playwright.async_api import async_playwright

MONTH_MAP = {
    "january": "January",   "jan": "January",
    "february": "February", "feb": "February",
    "march": "March",       "mar": "March",
    "april": "April",       "apr": "April",
    "may": "May",
    "june": "June",         "jun": "June",
    "july": "July",         "jul": "July",
    "august": "August",     "aug": "August",
    "september": "September","sep": "September",
    "october": "October",   "oct": "October",
    "november": "November", "nov": "November",
    "december": "December", "dec": "December",
}

EVENT_TYPES = {"Concert", "Club", "Festival", "Event", "Tickets", "Club Night", "Live"}

VENUES = {
    "Fållan": "https://www.fallan.nu/whats-on",
    "B-K":    "https://www.b-k.se/whats-on",
}

def parse_date(date_str):
    date_str = date_str.strip()
    m = re.match(r"(\w+)\s+(\d{1,2}),?\s+(\d{4})", date_str)
    if not m:
        return None, None, None
    month_str, day, year = m.group(1), int(m.group(2)), int(m.group(3))
    month_en = MONTH_MAP.get(month_str.lower())
    if not month_en:
        return None, None, None
    return day, month_en, year

async def scrape_venue(page, venue_name, url):
    print(f"Loading {venue_name}...")
    await page.goto(url, wait_until="domcontentloaded")
    await page.wait_for_timeout(3000)

    # Scroll to load all events
    prev_height = 0
    attempts = 0
    while attempts < 40:
        curr_height = await page.evaluate("document.body.scrollHeight")
        if curr_height == prev_height:
            break
        prev_height = curr_height
        await page.evaluate("window.scrollBy(0, 800)")
        await page.wait_for_timeout(600)
        attempts += 1

    print(f"  Scrolled {attempts} times")

    from bs4 import BeautifulSoup
    html = await page.content()
    soup = BeautifulSoup(html, "html.parser")

    events = []
    seen = set()

    for a in soup.find_all("a", href=re.compile(r"/whats-on/")):
        href = a.get("href", "")
        if href in seen:
            continue

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

        texts = [t.strip() for t in a.stripped_strings if t.strip()]
        date_raw = next(
            (t for t in texts if re.match(
                r"(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec"
                r"|January|February|March|April|June|July|August"
                r"|September|October|November|December)",
                t, re.IGNORECASE
            )),
            ""
        )
        if not date_raw:
            continue

        day, month, year = parse_date(date_raw)
        if not day:
            continue

        sub_venue = ""
        for t in texts:
            if t not in EVENT_TYPES and t != artist and not re.match(
                r"(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec"
                r"|January|February|March|April|June|July|August"
                r"|September|October|November|December)",
                t, re.IGNORECASE
            ):
                if any(v in t for v in ["Fållan", "BAR", "Lilla", "B-K", "Stora"]):
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

async def scrape():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        for venue_name, url in VENUES.items():
            events = await scrape_venue(page, venue_name, url)
            fname = "events_fallan.json" if venue_name == "Fållan" else "events_bk.json"
            with open(fname, "w", encoding="utf-8") as f:
                json.dump(events, f, ensure_ascii=False, indent=2)
            print(f"[{venue_name}] Extracted {len(events)} events → {fname}")
            for e in events:
                print(f"  {e['day']} {e['month']} {e['year']} | {e['artist']}")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(scrape())