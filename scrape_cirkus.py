import asyncio
import json
import re
from datetime import datetime
from playwright.async_api import async_playwright

BASE_URL = "https://cirkus.se"
MONTH_MAP = {
    "JAN": "January", "FEB": "February", "MAR": "March", "APR": "April",
    "MAJ": "May", "JUN": "June", "JUL": "July", "AUG": "August",
    "SEP": "September", "OKT": "October", "NOV": "November", "DEC": "December"
}

SKIP_HREFS = {"/sv/evenemang/", "/sv/evenemang/konsert/", "/sv/evenemang/musikal/",
              "/sv/evenemang/humor/", "/sv/evenemang/dans/"}

def parse_date_str(s):
    """Parse '11 MARS 2026' -> (11, 'March', 2026)"""
    m = re.match(r"(\d{1,2})\s+(\w+)\s+(\d{4})", s.strip())
    if not m:
        return None
    day, month_sv, year = m.group(1), m.group(2).upper(), int(m.group(3))
    month_en = MONTH_MAP.get(month_sv[:3])
    if not month_en:
        return None
    return int(day), month_en, year

async def get_event_links(page):
    """Scrape all event hrefs across all pages."""
    all_links = []
    url = f"{BASE_URL}/sv/evenemang/"
    pg = 1
    while url:
        print(f"  Collecting page {pg}: {url}")
        await page.goto(url, wait_until="domcontentloaded")
        await page.wait_for_timeout(1500)

        cards = await page.eval_on_selector_all(
            "a[href*='/sv/evenemang/']",
            "els => els.map(e => ({href: e.getAttribute('href'), text: e.innerText.trim()}))"
        )
        for card in cards:
            href = card["href"]
            text = card["text"]
            if not href or href in SKIP_HREFS or "/page/" in href or not text:
                continue
            if href not in [l[0] for l in all_links]:
                all_links.append((href, text))

        next_link = await page.query_selector("a[href*='/page/']")
        next_url = None
        # Find "Nästa sida" link
        nav_links = await page.eval_on_selector_all(
            "a[href*='/page/']",
            "els => els.map(e => ({href: e.getAttribute('href'), text: e.innerText.trim()}))"
        )
        for nl in nav_links:
            if "ста" in nl["text"] or "NÄSTA" in nl["text"].upper():
                next_url = BASE_URL + nl["href"] if nl["href"].startswith("/") else nl["href"]
                break
        url = next_url
        pg += 1

    return all_links

async def get_event_date(page, href):
    """Visit event page and extract date."""
    url = BASE_URL + href if href.startswith("/") else href
    await page.goto(url, wait_until="domcontentloaded")
    await page.wait_for_timeout(1500)

    text = await page.inner_text("body")
    # Look for date patterns like "11 MARS 2026" or "3 MARS 2026 - 11 MARS 2026"
    date_range = re.search(r"(\d{1,2}\s+[A-ZÅÄÖ]+\s+\d{4})\s*-\s*(\d{1,2}\s+[A-ZÅÄÖ]+\s+\d{4})", text)
    single_date = re.search(r"(\d{1,2}\s+[A-ZÅÄÖ]+\s+\d{4})", text)

    start_date = end_date = None
    if date_range:
        start_date = parse_date_str(date_range.group(1))
        end_date = parse_date_str(date_range.group(2))
    elif single_date:
        start_date = parse_date_str(single_date.group(1))

    return start_date, end_date

async def main():
    all_events = []
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()

        print("Step 1: Collecting event links...")
        links = await get_event_links(page)
        print(f"Found {len(links)} events\n")

        print("Step 2: Fetching dates from event pages...")
        for href, artist in links:
            print(f"  {artist[:50]}...")
            start, end = await get_event_date(page, href)
            if not start:
                print(f"    ⚠ No date found, skipping")
                continue
            day, month, year = start
            end_date_str = f"{end[0]} {end[1]} {end[2]}" if end else None
            all_events.append({
                "artist": artist,
                "day": day,
                "month": month,
                "year": year,
                "end_date": end_date_str,
                "venue": "Cirkus",
                "event_url": BASE_URL + href,
                "ticket_url": BASE_URL + href,
            })

        await browser.close()

    print(f"\nTotal events: {len(all_events)}")
    with open("events_cirkus.json", "w", encoding="utf-8") as f:
        json.dump(all_events, f, ensure_ascii=False, indent=2)
    print("Saved to events_cirkus.json")
    for e in all_events:
        print(f"  {e['day']} {e['month']} {e['year']} | {e['artist']}")

if __name__ == "__main__":
    asyncio.run(main())