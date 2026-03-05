import asyncio
import json
import re
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup

BASE_URL = "https://debaser.se"
CALENDAR_URL = "https://debaser.se/kalender"

async def scrape_debaser():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        print("Loading Debaser calendar...")
        await page.goto(CALENDAR_URL, wait_until="networkidle", timeout=60000)

        # Scroll to load all events
        prev_height = 0
        attempts = 0
        while attempts < 30:
            curr_height = await page.evaluate("document.body.scrollHeight")
            if curr_height == prev_height:
                break
            prev_height = curr_height
            await page.evaluate("window.scrollBy(0, 1000)")
            await asyncio.sleep(0.6)
            attempts += 1

        print(f"Scrolled {attempts} times. Extracting HTML...")
        html = await page.content()
        await browser.close()

    soup = BeautifulSoup(html, "html.parser")
    events = []

    # Each event is a w-dyn-item list item
    items = soup.select("div[role='listitem'].w-dyn-item")
    print(f"Found {len(items)} list items")

    for item in items:
        # Use the desktop version: .evenitemwhite > a.event-info
        event_info = item.select_one("a.event-info")
        if not event_info:
            continue

        # Date: three .b1-data divs inside .event-date-hero.border
        date_hero = event_info.select_one("div.event-date-hero.border")
        if not date_hero:
            continue

        date_parts = [d.get_text(strip=True) for d in date_hero.select("div.b1-data")]
        # date_parts = [day_num, month, year, weekday] or similar
        day = next((p for p in date_parts if p.isdigit() and len(p) <= 2), "")
        month = next((p for p in date_parts if re.match(r'^[A-Za-z]{3,}$', p)), "")
        year = next((p for p in date_parts if p.isdigit() and len(p) == 4), "")
        date_str = f"{day} {month} {year}".strip()

        # Artist name
        artist_el = event_info.select_one("div.h3.calendar-mobile")
        artist = artist_el.get_text(strip=True) if artist_el else ""

        # Support act
        support_el = event_info.select_one("div.support div.h4")
        support = support_el.get_text(strip=True) if support_el else ""

        # Venue: inside .event-date-hero.border-copy
        venue_el = item.select_one("div.event-date-hero.border-copy div.b2")
        venue = venue_el.get_text(strip=True) if venue_el else "Debaser"

        # Genre: inside .event-date-hero.border-genre
        genre_el = item.select_one("div.event-date-hero.border-genre div.b2")
        genre = genre_el.get_text(strip=True) if genre_el else ""

        # Event page URL
        event_href = event_info.get("href", "")
        event_url = BASE_URL + event_href if event_href.startswith("/") else event_href

        # Ticket URL: a.ticket-new.on-event inside .evenitemwhite
        ticket_el = item.select_one("div.evenitemwhite a.ticket-new.on-event")
        ticket_url = ticket_el.get("href", "") if ticket_el else ""

        if artist:
            events.append({
                "artist": artist,
                "support": support,
                "date": date_str,
                "day": day,
                "month": month,
                "year": year,
                "venue": venue,
                "genre": genre,
                "event_url": event_url,
                "ticket_url": ticket_url,
                "source": "Debaser"
            })

    print(f"Extracted {len(events)} events")

    with open("events_debaser.json", "w", encoding="utf-8") as f:
        json.dump(events, f, ensure_ascii=False, indent=2)
    print("Saved to events_debaser.json")

    # Preview first 3
    for e in events[:3]:
        print(f"  {e['date']} | {e['artist']} | {e['venue']}")

    return events

if __name__ == "__main__":
    asyncio.run(scrape_debaser())
