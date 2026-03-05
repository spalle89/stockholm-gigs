import asyncio
import json
import re
from datetime import datetime, timedelta
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup

URL = "https://stadsgardsterminalen.com/program/"
BASE_URL = "https://stadsgardsterminalen.com"

MONTH_MAP = {
    "jan": "January", "feb": "February", "mar": "March", "apr": "April",
    "maj": "May", "jun": "June", "jul": "July", "aug": "August",
    "sep": "September", "okt": "October", "nov": "November", "dec": "December"
}

def parse_date(date_str):
    today = datetime.now()
    date_str = date_str.strip().lower()

    if date_str == "idag":
        return today.day, today.strftime("%B"), today.year
    if date_str.startswith("imorgon"):
        t = today + timedelta(days=1)
        return t.day, t.strftime("%B"), t.year

    m = re.search(r"(\d{1,2})\s+(jan|feb|mar|apr|maj|jun|jul|aug|sep|okt|nov|dec)", date_str)
    if m:
        day = int(m.group(1))
        month_sv = m.group(2)[:3]
        month_en = MONTH_MAP.get(month_sv)
        if not month_en:
            return None, None, None
        month_num = list(MONTH_MAP.keys()).index(month_sv) + 1
        year = today.year if month_num >= today.month else today.year + 1
        return day, month_en, year

    return None, None, None

async def scrape():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        print("Loading Kollektivet Livet program page...")
        await page.goto(URL, wait_until="domcontentloaded")
        await page.wait_for_timeout(3000)

        # Scroll incrementally and click "LÄS IN FLER" whenever it appears
        clicks = 0
        scroll_pos = 0
        no_button_count = 0

        while no_button_count < 5:
            # Scroll down a bit
            scroll_pos += 600
            await page.evaluate(f"window.scrollTo(0, {scroll_pos})")
            await page.wait_for_timeout(500)

            # Try to click the button via JS
            clicked = await page.evaluate("""
                () => {
                    const els = Array.from(document.querySelectorAll('a, button'));
                    const btn = els.find(e => e.innerText.trim() === 'LÄS IN FLER');
                    if (btn) { btn.click(); return true; }
                    return false;
                }
            """)
            if clicked:
                await page.wait_for_timeout(2000)
                clicks += 1
                scroll_pos = 0  # reset scroll after new content loads
                no_button_count = 0
                print(f"  Clicked 'LÄS IN FLER' ({clicks}x), loading more...")
            else:
                # Check if we've reached the bottom
                at_bottom = await page.evaluate(
                    "window.scrollY + window.innerHeight >= document.body.scrollHeight - 100"
                )
                if at_bottom:
                    no_button_count += 1

        print(f"Done clicking. Extracting HTML...")
        html = await page.content()
        await browser.close()

    soup = BeautifulSoup(html, "html.parser")
    events = []
    seen = set()

    for h3 in soup.find_all("h3"):
        artist = h3.get_text(strip=True)
        if not artist:
            continue

        container = h3.parent
        date_raw = None
        ticket_url = ""
        event_url = ""

        for _ in range(6):
            if not container:
                break
            text = container.get_text(" ", strip=True)

            date_match = re.search(
                r"(idag|imorgon|\d{1,2}\s+(?:jan|feb|mar|apr|maj|jun|jul|aug|sep|okt|nov|dec)[a-z]*)",
                text, re.IGNORECASE
            )
            if date_match:
                date_raw = date_match.group(1)

            event_a = container.find("a", href=re.compile(r"/event/"))
            if event_a:
                event_url = event_a.get("href", "")

            ticket_a = container.find("a", href=re.compile(r"tickster|blackplanet|ticketmaster"))
            if ticket_a:
                ticket_url = ticket_a.get("href", "")

            if date_raw and event_url:
                break
            container = container.parent

        if not date_raw or not event_url:
            continue

        if event_url in seen:
            continue
        seen.add(event_url)

        day, month, year = parse_date(date_raw)
        if not day:
            continue

        sub_venue = ""
        if container:
            for t in container.stripped_strings:
                t = t.strip()
                if "scen" in t.lower() or "kollektivet livet" in t.lower():
                    sub_venue = t
                    break

        events.append({
            "artist": artist,
            "day": day,
            "month": month,
            "year": year,
            "venue": "Kollektivet Livet",
            "sub_venue": sub_venue,
            "event_url": BASE_URL + event_url if event_url.startswith("/") else event_url,
            "ticket_url": ticket_url or (BASE_URL + event_url if event_url.startswith("/") else event_url),
        })

    print(f"[Kollektivet Livet] Extracted {len(events)} events")
    with open("events_kollektivet_livet.json", "w", encoding="utf-8") as f:
        json.dump(events, f, ensure_ascii=False, indent=2)
    print("Saved to events_kollektivet_livet.json")
    for e in events:
        print(f"  {e['day']} {e['month']} {e['year']} | {e['artist']}")

if __name__ == "__main__":
    asyncio.run(scrape())