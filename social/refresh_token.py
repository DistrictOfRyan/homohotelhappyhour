"""
Exchange a Facebook user access token for the HHHH page access token.

Usage:
    python social/refresh_token.py <USER_ACCESS_TOKEN>

How to get the user token:
  1. Go to https://developers.facebook.com/tools/explorer
  2. App dropdown: select "Tulsa Gays Auto Poster"
  3. Permissions (add all if missing):
       pages_show_list, pages_manage_posts, pages_read_engagement,
       instagram_basic, instagram_content_publish
  4. Click "Generate Access Token" -- approve the dialog
  5. Copy the token from the "Access Token" field (starts with EAAU...)
  6. Run: python social/refresh_token.py EAAU3NOdIA5g...
"""

import json
import sys
import requests
from datetime import date
from pathlib import Path

APP_ID      = "1468075241636760"
PAGE_ID     = "1158982793957912"   # Graph API asset ID (NOT the profile URL ID 61589412247344)
SECRET_PATH = Path.home() / ".credentials" / "meta_app_secret_1468075241636760.txt"
CFG_PATH    = Path(__file__).parent / "meta_api_config.json"


def load_secret():
    if not SECRET_PATH.exists():
        print(f"ERROR: App secret not found at {SECRET_PATH}")
        sys.exit(1)
    return SECRET_PATH.read_text().strip()


def exchange_for_long_lived(short_token, app_secret):
    """Exchange a short-lived user token (~1hr) for a long-lived one (~60 days)."""
    r = requests.get(
        "https://graph.facebook.com/v25.0/oauth/access_token",
        params={
            "grant_type":       "fb_exchange_token",
            "client_id":        APP_ID,
            "client_secret":    app_secret,
            "fb_exchange_token": short_token,
        },
        timeout=15,
    )
    data = r.json()
    if "access_token" in data:
        print(f"  [+] Long-lived user token acquired (expires in ~{data.get('expires_in', '?')} sec)")
        return data["access_token"]
    print(f"  [!] Token exchange failed ({data.get('error', {}).get('message', 'unknown')}). Using short-lived token.")
    return short_token


def get_page_token(user_token):
    """Query the HHHH page directly to get its permanent page access token."""
    r = requests.get(
        f"https://graph.facebook.com/v25.0/{PAGE_ID}",
        params={"fields": "access_token,name,fan_count", "access_token": user_token},
        timeout=15,
    )
    data = r.json()
    if "error" in data:
        err = data["error"]
        print(f"ERROR: {err['message']}")
        print(f"       Code: {err.get('code')}  Subcode: {err.get('error_subcode')}")
        print()
        if err.get("code") == 190:
            print("Token is expired or invalid. Generate a fresh one from Graph API Explorer.")
        elif err.get("code") == 200:
            print("Permissions missing. Re-generate token with all 5 permissions checked.")
        elif err.get("code") == 100:
            print("Page not found or not accessible with this token.")
            print(f"Make sure your Facebook account is an admin of Page ID {PAGE_ID}.")
        sys.exit(1)
    if "access_token" not in data:
        print(f"ERROR: 'access_token' not in response. Got: {data}")
        print("This usually means your token doesn't have pages_manage_posts permission,")
        print("OR the page uses New Pages Experience and needs Business Manager setup.")
        print("See SETUP_NOTES.md in this directory for the Business Manager path.")
        sys.exit(1)
    return data["access_token"], data.get("name", "HHHH Page"), data.get("fan_count", 0)


def get_instagram_id(page_token):
    """Fetch the Instagram Business Account ID linked to the HHHH page (if linked)."""
    r = requests.get(
        f"https://graph.facebook.com/v25.0/{PAGE_ID}",
        params={"fields": "instagram_business_account", "access_token": page_token},
        timeout=15,
    )
    data = r.json()
    ig = data.get("instagram_business_account", {})
    return ig.get("id")


def verify_page_token(page_token):
    """Confirm the token works by fetching basic page info."""
    r = requests.get(
        f"https://graph.facebook.com/v25.0/{PAGE_ID}",
        params={"fields": "name,fan_count", "access_token": page_token},
        timeout=15,
    )
    return r.json()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    user_token = sys.argv[1].strip()
    app_secret = load_secret()

    print(f"\n=== HHHH Meta Token Refresh ===\n")

    print("Step 1: Exchanging for long-lived user token...")
    long_user = exchange_for_long_lived(user_token, app_secret)

    print(f"Step 2: Getting page token for Page ID {PAGE_ID}...")
    page_token, page_name, fan_count = get_page_token(long_user)
    print(f"  [+] Page: '{page_name}' (followers: {fan_count})")

    print("Step 3: Checking for linked Instagram account...")
    ig_id = get_instagram_id(page_token)
    if ig_id:
        print(f"  [+] Instagram Business Account ID: {ig_id}")
    else:
        print("  [!] No Instagram account linked yet.")
        print("      Fix: Switch @homohotelhappyhour to Professional account in the IG app,")
        print("      then Settings > Accounts > Linked Accounts > Facebook > select this page.")

    print("Step 4: Verifying page token...")
    verified = verify_page_token(page_token)
    if "name" in verified:
        print(f"  [+] Token verified -- page name: '{verified['name']}'")
    else:
        print(f"  [!] Verification unexpected: {verified}")

    # Load and update config
    print("Step 5: Saving to meta_api_config.json...")
    with open(CFG_PATH, encoding="utf-8") as f:
        cfg = json.load(f)

    cfg["page_access_token"]  = page_token
    cfg["page_token_expires"] = "never"
    cfg["last_refreshed"]     = date.today().isoformat()
    cfg["page_token_note"]    = (
        f"Permanent page token. Refreshed {date.today().isoformat()} via "
        "Graph API Explorer user token exchange. expires_at=0 (never expires "
        "unless password changed or app revoked)."
    )
    if ig_id:
        cfg["instagram_business_account_id"] = ig_id

    with open(CFG_PATH, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=4)

    print(f"  [+] Saved to {CFG_PATH}")
    print(f"\n=== Done ===")
    print(f"Page token:    set (permanent)")
    print(f"Instagram ID:  {ig_id or 'PENDING (link IG to FB page first)'}")
    print(f"\nNext step: run post_event.py --dry-run to validate posting credentials.")
