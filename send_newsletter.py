import os
import requests
import resend
from datetime import date

SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://kfqipfsywnecuceziiiy.supabase.co")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImtmcWlwZnN5d25lY3VjZXppaWl5Iiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3MjY4OTA5OSwiZXhwIjoyMDg4MjY1MDk5fQ.FIx5Qtzo7rlmfIdMSVtbqCGo78sdfJdyp34IUL7MsRA")
RESEND_API_KEY = os.environ["RESEND_API_KEY"]

HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
}

DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
          "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def fetch_new_events(today: str) -> list:
    resp = requests.get(
        f"{SUPABASE_URL}/rest/v1/events?select=*&first_seen=eq.{today}&order=date.asc,venue.asc,artist.asc&limit=2000",
        headers=HEADERS,
    )
    resp.raise_for_status()
    return resp.json()


def fetch_subscribers() -> list:
    resp = requests.get(
        f"{SUPABASE_URL}/rest/v1/subscribers?select=email&limit=10000",
        headers=HEADERS,
    )
    resp.raise_for_status()
    return [row["email"] for row in resp.json()]


def format_date(date_str: str) -> str:
    d = date_str.split("-")
    year, month, day = int(d[0]), int(d[1]), int(d[2])
    from datetime import date as dt
    weekday = dt(year, month, day).weekday()
    return f"{DAYS[weekday]} {day} {MONTHS[month - 1]}"


def build_html(events: list) -> str:
    # Group by date then venue
    by_date: dict = {}
    for e in events:
        d = e["date"]
        v = e["venue"]
        by_date.setdefault(d, {}).setdefault(v, []).append(e)

    rows_html = ""
    for date_str in sorted(by_date):
        date_label = format_date(date_str)
        rows_html += f"""
        <tr>
          <td colspan="2" style="padding:20px 0 8px; border-bottom:1px solid #2a2a30;">
            <span style="font-family:'Georgia',serif;font-size:13px;font-weight:bold;
                         color:#e8c87a;letter-spacing:0.12em;text-transform:uppercase;">
              {date_label}
            </span>
          </td>
        </tr>"""
        for venue in sorted(by_date[date_str]):
            for ev in by_date[date_str][venue]:
                ticket_url = ev.get("ticket_url") or ev.get("event_url") or ""
                artist_html = (
                    f'<a href="{ticket_url}" style="color:#e8e4dc;text-decoration:none;">'
                    f'{ev["artist"]}</a>'
                    if ticket_url
                    else ev["artist"]
                )
                rows_html += f"""
        <tr>
          <td style="padding:8px 0;border-bottom:1px solid #1e1e24;vertical-align:top;">
            <span style="font-family:'Georgia',serif;font-size:15px;color:#e8e4dc;">
              {artist_html}
            </span>
          </td>
          <td style="padding:8px 0 8px 16px;border-bottom:1px solid #1e1e24;
                     vertical-align:top;white-space:nowrap;text-align:right;">
            <span style="font-family:'Courier New',monospace;font-size:10px;
                         color:#e8c87a;text-transform:uppercase;letter-spacing:0.08em;">
              {ev["venue"]}
            </span>
          </td>
        </tr>"""

    return f"""<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body style="margin:0;padding:0;background:#0d0d0f;">
  <table width="100%" cellpadding="0" cellspacing="0" border="0"
         style="background:#0d0d0f;font-family:sans-serif;">
    <tr>
      <td align="center" style="padding:40px 20px;">
        <table width="600" cellpadding="0" cellspacing="0" border="0"
               style="max-width:600px;width:100%;">

          <!-- Header -->
          <tr>
            <td style="padding:0 0 32px;border-bottom:1px solid #2a2a30;">
              <span style="font-family:'Georgia',serif;font-size:28px;font-weight:bold;
                           color:#e8e4dc;letter-spacing:-0.01em;">
                Stockholm <em style="color:#e8c87a;">Gigs</em>
              </span>
              <p style="margin:8px 0 0;font-family:'Courier New',monospace;font-size:11px;
                        color:#7a7670;letter-spacing:0.18em;text-transform:uppercase;">
                New this week
              </p>
            </td>
          </tr>

          <!-- Events table -->
          <tr>
            <td style="padding:16px 0 0;">
              <table width="100%" cellpadding="0" cellspacing="0" border="0">
                {rows_html}
              </table>
            </td>
          </tr>

          <!-- Footer -->
          <tr>
            <td style="padding:32px 0 0;border-top:1px solid #2a2a30;margin-top:24px;">
              <p style="font-family:'Courier New',monospace;font-size:10px;
                        color:#7a7670;letter-spacing:0.1em;text-transform:uppercase;margin:0;">
                Stockholm Gigs &mdash; weekly digest
              </p>
            </td>
          </tr>

        </table>
      </td>
    </tr>
  </table>
</body>
</html>"""


def main():
    today = date.today().isoformat()
    print(f"Fetching new events for {today}...")

    events = fetch_new_events(today)
    print(f"  {len(events)} new events found")

    if not events:
        print("No new events today — skipping newsletter.")
        return

    subscribers = fetch_subscribers()
    print(f"  {len(subscribers)} subscribers")

    if not subscribers:
        print("No subscribers — skipping newsletter.")
        return

    html = build_html(events)
    subject = f"Stockholm Gigs \u2014 {len(events)} new event{'s' if len(events) != 1 else ''} this week"

    resend.api_key = RESEND_API_KEY

    sent = 0
    for email in subscribers:
        try:
            resend.Emails.send({
                "from": "Stockholm Gigs <onboarding@resend.dev>",
                "to": email,
                "subject": subject,
                "html": html,
            })
            sent += 1
        except Exception as exc:
            print(f"  ✗ Failed to send to {email}: {exc}")

    print(f"\n✓ Newsletter sent to {sent}/{len(subscribers)} subscribers")


if __name__ == "__main__":
    main()
