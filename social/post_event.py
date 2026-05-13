"""
Post HHHH event announcements to Facebook Page and Instagram.

Usage:
    # Text-only Facebook post
    python social/post_event.py --text "Join us June 5 at Twisted Arts!"

    # Post with a local image (will upload via GitHub Pages URL)
    python social/post_event.py --text "caption" --image photos/flyer-may-2026.jpg

    # Post with a direct public image URL
    python social/post_event.py --text "caption" --image-url "https://homohotelhappyhour.com/photos/flyer-may-2026.jpg"

    # Post to Instagram only (requires linked IG account)
    python social/post_event.py --text "caption" --image-url "https://..." --ig-only

    # Dry run (validates credentials, no actual post)
    python social/post_event.py --dry-run

Notes:
    - Images must be public URLs for Instagram (local file path auto-resolves to GitHub Pages URL).
    - Facebook supports binary image upload; Instagram requires public URL.
    - Run refresh_token.py first if you get a 190 (invalid token) error.
"""

import argparse
import json
import os
import subprocess
import sys
import time
import requests
from pathlib import Path

ROOT     = Path(__file__).resolve().parent.parent
CFG_PATH = Path(__file__).parent / "meta_api_config.json"
API_BASE = "https://graph.facebook.com/v25.0"

# GitHub Pages public URL base for image hosting
SITE_BASE = "https://districtofRyan.github.io/homohotelhappyhour"


def load_config():
    with open(CFG_PATH, encoding="utf-8") as f:
        cfg = json.load(f)
    token = cfg.get("page_access_token", "")
    if not token or token.startswith("PENDING"):
        print("ERROR: No valid page token. Run: python social/refresh_token.py <USER_TOKEN>")
        sys.exit(1)
    return cfg


def validate_credentials(cfg):
    """Quick token check against the page."""
    r = requests.get(
        f"{API_BASE}/{cfg['page_id']}",
        params={"fields": "name,fan_count", "access_token": cfg["page_access_token"]},
        timeout=15,
    )
    data = r.json()
    if "error" in data:
        print(f"Token validation FAILED: {data['error']['message']}")
        print("Run: python social/refresh_token.py <USER_TOKEN>")
        sys.exit(1)
    print(f"[+] Credentials valid -- page: '{data['name']}' ({data.get('fan_count', 0)} followers)")
    return data


def post_to_facebook(page_id, page_token, message, image_path=None, image_url=None):
    """Post text (and optionally an image) to the HHHH Facebook page."""
    if image_path or image_url:
        # Photo post
        if image_path and not image_url:
            # Upload binary directly to FB
            img = Path(image_path)
            if not img.exists():
                print(f"ERROR: Image not found: {image_path}")
                sys.exit(1)
            with open(img, "rb") as f:
                r = requests.post(
                    f"{API_BASE}/{page_id}/photos",
                    data={"caption": message, "access_token": page_token},
                    files={"source": (img.name, f, "image/jpeg")},
                    timeout=30,
                )
        else:
            # Use URL
            r = requests.post(
                f"{API_BASE}/{page_id}/photos",
                data={
                    "url":          image_url,
                    "caption":      message,
                    "access_token": page_token,
                },
                timeout=30,
            )
        result = r.json()
        if "error" in result:
            print(f"FB photo post FAILED: {result['error']['message']}")
            return None
        post_id = result.get("post_id") or result.get("id")
        print(f"[+] Facebook photo post: {post_id}")
        return post_id
    else:
        # Text-only post
        r = requests.post(
            f"{API_BASE}/{page_id}/feed",
            data={"message": message, "access_token": page_token},
            timeout=30,
        )
        result = r.json()
        if "error" in result:
            print(f"FB text post FAILED: {result['error']['message']}")
            return None
        post_id = result.get("id")
        print(f"[+] Facebook text post: {post_id}")
        return post_id


def post_to_instagram(ig_id, page_token, caption, image_url):
    """Two-step Instagram image post (container -> publish)."""
    if not ig_id or ig_id.startswith("PENDING"):
        print("[!] Instagram: skipped -- no IG Business Account ID in config.")
        print("    Link @homohotelhappyhour to the HHHH Facebook page first.")
        return None

    print("Posting to Instagram...")

    # Step 1: Create media container
    r = requests.post(
        f"{API_BASE}/{ig_id}/media",
        data={
            "image_url":    image_url,
            "caption":      caption,
            "access_token": page_token,
        },
        timeout=30,
    )
    container = r.json()
    if "error" in container:
        print(f"IG container creation FAILED: {container['error']['message']}")
        return None
    creation_id = container.get("id")
    print(f"  Container ID: {creation_id}")

    # Brief pause before publish (Meta recommends ~5s)
    time.sleep(5)

    # Step 2: Publish
    r = requests.post(
        f"{API_BASE}/{ig_id}/media_publish",
        data={"creation_id": creation_id, "access_token": page_token},
        timeout=30,
    )
    result = r.json()
    if "error" in result:
        print(f"IG publish FAILED: {result['error']['message']}")
        return None
    ig_post_id = result.get("id")
    print(f"[+] Instagram post: {ig_post_id}")
    return ig_post_id


def parse_args():
    p = argparse.ArgumentParser(description="Post HHHH event to Facebook and Instagram")
    p.add_argument("--text",       help="Post caption/message")
    p.add_argument("--image",      help="Local image path (relative to repo root)")
    p.add_argument("--image-url",  dest="image_url", help="Public image URL")
    p.add_argument("--fb-only",    action="store_true", help="Post to Facebook only")
    p.add_argument("--ig-only",    action="store_true", help="Post to Instagram only (requires --image-url)")
    p.add_argument("--dry-run",    action="store_true", help="Validate credentials only, no posting")
    return p.parse_args()


if __name__ == "__main__":
    args = parse_args()
    cfg = load_config()

    page_id    = cfg["page_id"]
    page_token = cfg["page_access_token"]
    ig_id      = cfg.get("instagram_business_account_id", "PENDING")

    # Always validate first
    validate_credentials(cfg)

    if args.dry_run:
        print("[dry-run] Credentials valid. No posts made.")
        ig_status = "READY" if (ig_id and not ig_id.startswith("PENDING")) else "PENDING (link IG first)"
        print(f"  Facebook: READY  |  Instagram: {ig_status}")
        sys.exit(0)

    if not args.text:
        print("ERROR: --text is required.")
        sys.exit(1)

    fb_post_id = None
    ig_post_id = None

    # Resolve image URL if local path given
    image_url = args.image_url
    if args.image and not image_url:
        img_path = ROOT / args.image
        if not img_path.exists():
            print(f"ERROR: Image not found: {img_path}")
            sys.exit(1)
        # For IG we need a public URL -- use the homohotelhappyhour.com path
        relative = Path(args.image)
        image_url = f"https://homohotelhappyhour.com/{relative}"
        print(f"[*] Resolved image URL: {image_url}")

    # Post to Facebook
    if not args.ig_only:
        fb_post_id = post_to_facebook(
            page_id, page_token, args.text,
            image_path=args.image, image_url=args.image_url
        )

    # Post to Instagram
    if not args.fb_only and image_url:
        ig_post_id = post_to_instagram(ig_id, page_token, args.text, image_url)
    elif not args.fb_only and not image_url:
        print("[*] Instagram: skipped -- no image URL (IG requires an image).")

    # Summary
    print("\n=== Post Summary ===")
    print(f"Facebook:  {fb_post_id or 'skipped'}")
    print(f"Instagram: {ig_post_id or 'skipped'}")

    # Save result to config
    if fb_post_id or ig_post_id:
        from datetime import date
        cfg["last_post"] = {
            "date":       date.today().isoformat(),
            "fb_post_id": fb_post_id,
            "ig_post_id": ig_post_id,
            "caption":    args.text[:120],
        }
        with open(CFG_PATH, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=4)
        print("[+] Results saved to meta_api_config.json")
