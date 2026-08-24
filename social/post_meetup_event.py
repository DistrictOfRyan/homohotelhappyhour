# -*- coding: utf-8 -*-
"""
post_meetup_event.py - create an HHHH event on Meetup via browser automation.

Meetup's event API is paid-only (Pro), so this drives the create-event composer
through the saved real-Chrome profile (see meetup_profile_login.py). Selectors
mapped live 2026-07-12 against the /{group}/schedule/ composer.

Flow (mapped):
  group /schedule/ -> "Start from scratch" modal -> single-page form:
    #title | date button (calendar: 'Go to the Next Month' + day aria-label)
    | input[aria-label='Edit start time'] | duration button (default '2 hours')
    | ProseMirror description editor | In-person location search
    | Save as draft / Publish

Usage:
  python social/post_meetup_event.py                 # fill + SAVE AS DRAFT + screenshot (safe default)
  python social/post_meetup_event.py --publish       # fill + PUBLISH live
  python social/post_meetup_event.py --event social/event_2026-08.json
"""
import sys, json, argparse, re, subprocess, datetime
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = Path(__file__).resolve().parent
PROFILE = str(HERE / "data" / "meetup_auto_profile")


def kill_profile_chrome():
    """Chrome leaves background procs holding the profile after a window closes;
    Playwright's channel=chrome then hands off and instantly exits. Kill them first."""
    ps = (
        "Get-CimInstance Win32_Process -Filter \"Name='chrome.exe'\" | "
        "Where-Object { $_.CommandLine -like '*meetup_auto_profile*' } | "
        "ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }"
    )
    try:
        subprocess.run(["powershell", "-NoProfile", "-Command", ps], capture_output=True, timeout=30)
    except Exception as e:
        print(f"[warn] could not sweep profile chrome: {e}")


def ordinal(n):
    return f"{n}{'th' if 11 <= n % 100 <= 13 else {1:'st',2:'nd',3:'rd'}.get(n % 10, 'th')}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--event", default=str(HERE / "event_2026-08.json"))
    ap.add_argument("--publish", action="store_true", help="publish live (default: save as draft)")
    ap.add_argument("--headless", action="store_true")
    a = ap.parse_args()

    ev = json.load(open(a.event, encoding="utf-8"))
    d = datetime.date.fromisoformat(ev["date"])
    target_month = d.strftime("%B %Y")                       # "August 2026"
    day_aria = f"{d.strftime('%A')}, {d.strftime('%B')} {ordinal(d.day)}, {d.year}"  # "Friday, August 7th, 2026"
    start_24 = ev["start_time"]                               # "18:00"
    group = ev["group_urlname"]
    print(f"Target: {ev['title']}")
    print(f"  date={day_aria}  start={start_24}  venue={ev['venue_name']}")

    kill_profile_chrome()
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        ctx = p.chromium.launch_persistent_context(
            PROFILE, channel="chrome", headless=a.headless,
            args=["--no-first-run", "--no-default-browser-check"])
        pg = ctx.pages[0] if ctx.pages else ctx.new_page()
        pg.set_default_timeout(30000)

        pg.goto(f"https://www.meetup.com/{group}/schedule/", wait_until="domcontentloaded")
        pg.wait_for_timeout(4000)

        # 1) "Start from scratch"
        sfs = pg.get_by_text("Start from scratch", exact=False)
        if sfs.count():
            sfs.first.click(); pg.wait_for_timeout(2500)
            print("[ok] start from scratch")

        # 2) title
        pg.fill("#title", ev["title"]); pg.wait_for_timeout(500)
        print("[ok] title")

        # 3) date -> open calendar, page to target month, click the day
        datebtn = None
        for b in pg.query_selector_all("button"):
            try:
                if b.is_visible() and re.search(r"(Mon|Tue|Wed|Thu|Fri|Sat|Sun),", (b.inner_text() or "")):
                    datebtn = b; break
            except Exception:
                pass
        if not datebtn:
            raise SystemExit("[fail] date button not found")
        datebtn.click(); pg.wait_for_timeout(1500)
        for _ in range(24):
            label = None
            for el in pg.query_selector_all("*"):
                try:
                    t = (el.inner_text() or "").strip()
                    if re.fullmatch(r"[A-Z][a-z]+ 20\d\d", t):
                        label = t; break
                except Exception:
                    pass
            if label == target_month:
                break
            nxt = pg.query_selector("button[aria-label='Go to the Next Month']")
            if not nxt:
                raise SystemExit("[fail] next-month button not found")
            nxt.click(); pg.wait_for_timeout(600)
        day = pg.query_selector(f"[aria-label='{day_aria}']")
        if not day:
            raise SystemExit(f"[fail] day cell not found: {day_aria}")
        day.click(); pg.wait_for_timeout(1200)
        print(f"[ok] date set ({target_month})")

        # 4) start time
        tin = pg.query_selector("input[aria-label='Edit start time']")
        tin.fill(start_24); pg.wait_for_timeout(400); tin.press("Tab"); pg.wait_for_timeout(600)
        print(f"[ok] start time {start_24}")

        # 5) description (ProseMirror) - pick the VISIBLE editor (ToastUI renders
        # a hidden markdown ProseMirror plus the visible WYSIWYG one).
        desc = None
        for el in pg.query_selector_all("div.ProseMirror"):
            if _vis(el):
                desc = el; break
        if not desc:
            raise SystemExit("[fail] visible description editor not found")
        desc.scroll_into_view_if_needed(); pg.wait_for_timeout(400)
        desc.click(); pg.wait_for_timeout(500)
        # insert_text dispatches a real input event into the focused ProseMirror
        # editor; far more reliable than per-char .type() (which flaked).
        pg.keyboard.insert_text(ev["description"]); pg.wait_for_timeout(700)
        print("[ok] description")

        # 6) location (In person -> search -> pick suggestion)
        for el in pg.query_selector_all("*"):
            try:
                if _vis(el) and (el.inner_text() or "").strip() == "In person":
                    el.scroll_into_view_if_needed(); el.click(); break
            except Exception:
                pass
        pg.wait_for_timeout(500)
        loc = pg.query_selector("input[placeholder='Search or add location...']")
        if loc:
            # venue-name query resolves to the real place; the street-address query
            # snaps to a wrong nearby point (mapped live 2026-07-12).
            q = ev.get("location_query") or f"{ev['venue_name']}, {ev['venue_address']}"
            match_key = str(ev.get("venue_match", "")).lower()
            loc.click(); loc.fill(""); pg.wait_for_timeout(300)
            loc.type(q, delay=15); pg.wait_for_timeout(4000)
            # the suggestion rows are <li class="cursor-pointer">
            opts = [o for o in pg.query_selector_all("li.cursor-pointer") if _vis(o)]
            chosen, how = None, "none"
            for o in opts:
                try:
                    t = (o.inner_text() or "").lower()
                    if match_key and match_key in t:
                        chosen, how = o, f"matched '{match_key}'"; break
                    if "courtyard" in t:
                        chosen, how = o, "matched 'courtyard'"; break
                except Exception:
                    pass
            if not chosen and opts:
                chosen, how = opts[0], "first suggestion (no key match)"
            if chosen:
                print("   location suggestions:", [((o.inner_text() or '').strip()[:45]) for o in opts][:5])
                chosen.click(); pg.wait_for_timeout(1500)
            print(f"[ok] location ({how})")

        pg.wait_for_timeout(1000)
        pg.screenshot(path=str(HERE / "_event_filled.png"), full_page=True)
        print("[shot] social/_event_filled.png")

        # 7) publish or save as draft (pick the VISIBLE button in the action bar)
        label = "Publish" if a.publish else "Save as draft"
        target_btn = None
        for b in pg.query_selector_all(f"button:has-text('{label}')"):
            if _vis(b):
                target_btn = b; break
        if target_btn:
            target_btn.scroll_into_view_if_needed(); pg.wait_for_timeout(300)
            target_btn.click(); pg.wait_for_timeout(6000)
            state = "published (LIVE)" if a.publish else "saved as DRAFT (not live)"
            print(f"[done] {state}. URL: {pg.url}")
        else:
            print(f"[warn] '{label}' button not visible; nothing submitted.")
        pg.screenshot(path=str(HERE / "_event_result.png"), full_page=True)
        print("[shot] social/_event_result.png")
        ctx.close()


def _vis(el):
    try:
        return el.is_visible()
    except Exception:
        return False


if __name__ == "__main__":
    main()
