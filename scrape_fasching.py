from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
import json

def scrape_fasching():
    print("Scraping Fasching...")

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.goto("https://www.fasching.se/en/calendar/")
        
        # Wait for initial load
        page.wait_for_timeout(3000)
        
        # Scroll to load all events
        print("Scrolling to load all events...")
        last_height = 0
        attempts = 0
        while attempts < 30:
            page.evaluate("window.scrollBy(0, 1000)")
            page.wait_for_timeout(600)
            new_height = page.evaluate("document.body.scrollHeight")
            if new_height == last_height:
                attempts += 1
            else:
                attempts = 0
            last_height = new_height
        
        print("Reached bottom of page!")
        html = page.content()
        browser.close()

    # Extract events
    soup = BeautifulSoup(html, "html.parser")
    cards = soup.find_all("li", class_="card")
    print(f"Found {len(cards)} events")

    events = []
    for card in cards:
        # Get date and time
        date = card.get("data-date", "")
        time = card.get("data-time", "")

        # Get artist name
        title_tag = card.find("h2", class_="card__title")
        artist = title_tag.text.strip() if title_tag else ""

        # Get description
        desc_tag = card.find("p")
        description = desc_tag.text.strip() if desc_tag else ""

        # Get ticket link
        ticket_tag = card.find("a", class_="btn--state-buy_ticket")
        ticket_url = ticket_tag["href"] if ticket_tag else ""

        if artist:
            events.append({
                "venue": "Fasching",
                "artist": artist,
                "date": date,
                "time": time,
                "description": description,
                "ticket_url": ticket_url
            })

    # Save to a JSON file
    with open("events_fasching.json", "w", encoding="utf-8") as f:
        json.dump(events, f, ensure_ascii=False, indent=2)

    print(f"Saved {len(events)} events to events_fasching.json")
    
    # Print a preview
    print("\nFirst 3 events:")
    for e in events[:3]:
        print(f"  {e['date']} {e['time']} — {e['artist']}")

scrape_fasching()