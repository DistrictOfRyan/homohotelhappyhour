# HHHH Social Automation — Setup Notes

## Current State (as of 2026-05-13)
- Facebook Page ID: `61589412247344` (New Pages Experience)
- App: "Tulsa Gays Auto Poster" (ID: `1468075241636760`) — same app as TulsaGays
- Page token: **PENDING** — needs manual refresh (see Step 1 below)
- Instagram: **PENDING** — needs William to link @homohotelhappyhour (see Step 2 below)

---

## Step 1: Get the Facebook Page Token (5 min, one-time setup)

**Why manual:** developers.facebook.com is blocked in Claude-in-Chrome (policy change 2026-05-07).
You have to do this in your regular Chrome browser.

1. Go to: https://developers.facebook.com/tools/explorer
2. App dropdown (top right): select **"Tulsa Gays Auto Poster"**
3. In the Permissions section, make sure all 5 are checked:
   - `pages_show_list`
   - `pages_manage_posts`
   - `pages_read_engagement`
   - `instagram_basic`
   - `instagram_content_publish`
4. Click **"Generate Access Token"** — a Facebook permissions dialog pops up, approve it
5. Copy the token from the **"Access Token"** field (long string starting with `EAAU...`)
6. Back in your Claude Code terminal, run:
   ```
   cd C:\Users\willi\hhhh-site
   python social/refresh_token.py EAAU3xyz...
   ```
   This script will:
   - Exchange for a long-lived token (~60 days)
   - Query the HHHH page directly to get the permanent page token
   - Save everything to `social/meta_api_config.json`
   - Print the Instagram account ID if IG is already linked

---

## Step 2: Link Instagram to the HHHH Facebook Page

**Why manual:** Requires the Instagram mobile app — cannot be automated.

1. Open Instagram on your phone, go to `@homohotelhappyhour`
2. Settings > Account type > **Switch to Professional account** (Creator or Business)
3. After switching: Settings > Account > **Linked accounts** > Facebook
4. Select the **"Tulsa's Homosexual Hotel Happy Hour, Inc."** page
5. Done. Once linked, re-run Step 1's `refresh_token.py` — it will auto-detect and save the IG account ID.

---

## Step 3: Test Before Posting

```bash
cd C:\Users\willi\hhhh-site
python social/post_event.py --dry-run
```

Expected output:
```
[+] Credentials valid -- page: 'Tulsa's Homosexual Hotel Happy Hour, Inc.' (X followers)
[dry-run] Credentials valid. No posts made.
  Facebook: READY  |  Instagram: READY
```

---

## Posting an Event

```bash
# Text only
python social/post_event.py --text "Join us this Friday at Twisted Arts! June 5, doors at 7pm. Free to attend."

# With local flyer image (will upload directly to Facebook, uses homohotelhappyhour.com URL for Instagram)
python social/post_event.py \
  --text "Join us June 5 at Twisted Arts!" \
  --image photos/flyer-may-2026.jpg

# With a public image URL (works for both FB + IG in one shot)
python social/post_event.py \
  --text "Join us June 5 at Twisted Arts!" \
  --image-url "https://homohotelhappyhour.com/photos/flyer-may-2026.jpg"
```

---

## Why New Pages Experience Requires Direct Page Query

Meta changed how page tokens work for New Pages Experience pages:
- `me/accounts` returns EMPTY (same quirk as TulsaGays)
- Solution: query the page directly by page ID: `/{page_id}?fields=access_token`
- This works as long as your user token has `pages_manage_posts` permission AND you are an admin of the page
- The resulting page token is **permanent** (expires only if you change your FB password or revoke the app)

---

## Token Refresh Schedule

The page token itself is permanent. The only times you need to re-run `refresh_token.py`:
- After changing your Facebook password
- After revoking the "Tulsa Gays Auto Poster" app in FB Settings > Apps
- After ~60 days if you want a fresh long-lived user token underneath (optional)

---

## Troubleshooting

| Error | Code | Fix |
|-------|------|-----|
| "Session invalid, user logged out" | 190/467 | Re-run refresh_token.py with new user token |
| "Permissions error" | 200 | Re-generate token with all 5 permissions selected |
| "Page not found" | 100 | Confirm you're logged into the right FB account (William's) |
| "access_token not in response" | -- | Might need to add app to page via Meta Business Suite |

---

## Meta Business Suite Path (if direct method fails)

If `refresh_token.py` hits "access_token not in response" and the direct page query method fails due to New Pages Experience restrictions:

1. Go to https://business.facebook.com
2. Select the HHHH page
3. Settings > Integrations > **Partner Apps**
4. Add app ID `1468075241636760` ("Tulsa Gays Auto Poster")
5. Grant: Manage page, Create content, Read page insights
6. Then re-run `refresh_token.py` — the page token will now return

This should NOT be necessary based on TulsaGays precedent, but it's the fallback.
