"""Parking & logistics graphic for HHHH August 2026 (Courtyard Downtown).

Facts (William, 2026-08-04, from the Courtyard directly):
  - Street parking is the best bet.
  - Valet available at a $15 daily rate; the hotel extends that rate to HHHH guests.
Event facts verified against event_2026-08.json + the approved August promo:
  Friday Aug 7, 6:00-8:00 PM, Courtyard Downtown, 415 S Boston Ave, PFLAG Tulsa.

Brand tokens copied from tulsagays/gen_hhhh_promo_may.py (the canonical HHHH
promo generator): white bg, 4-square HHHH badge, HOMO HOTEL black / HAPPY HOUR
orange, Georgia bold for date lines, orange benefitting band. No em/en dashes
anywhere (William's voice rule covers graphics).
"""
from PIL import Image, ImageDraw, ImageFont
from pathlib import Path

W, H = 1080, 1350
OUT = Path(__file__).parent.parent / "photos" / "hhhh_parking_2026-08.png"

WHITE = (255, 255, 255)
BLACK = (30, 30, 30)
ORANGE = (235, 120, 40)
GRAY = (100, 100, 100)
LIGHT = (200, 200, 200)
CARD_BG = (247, 247, 247)

FONT_DIR = Path(r"C:\Windows\Fonts")


def ttf(name, size):
    for p in (FONT_DIR / name, Path(name)):
        if p.exists():
            return ImageFont.truetype(str(p), size)
    return ImageFont.load_default()


im = Image.new("RGB", (W, H), WHITE)
d = ImageDraw.Draw(im)


def center(text, font, y, fill):
    bb = d.textbbox((0, 0), text, font=font)
    d.text(((W - (bb[2] - bb[0])) / 2 - bb[0], y), text, fill=fill, font=font)
    return bb[3] - bb[1]


# HHHH logo badge (4-square), smaller than the promo since this is an info card
cx, cy = W // 2, 150
r = 118
d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=BLACK)
s = 58
colors = [(147, 51, 182), (85, 165, 70), (235, 130, 45), (72, 172, 206)]
positions = [(-s - 5, -s - 5), (5, -s - 5), (-s - 5, 5), (5, 5)]
badge_font = ttf("arialbd.ttf", 48)
for (dx, dy), col in zip(positions, colors):
    x0, y0 = cx + dx, cy + dy
    d.rectangle((x0, y0, x0 + s, y0 + s), fill=col)
    bb = d.textbbox((0, 0), "H", font=badge_font)
    tw, th = bb[2] - bb[0], bb[3] - bb[1]
    d.text((x0 + (s - tw) / 2 - bb[0], y0 + (s - th) / 2 - bb[1] - 3),
           "H", fill=WHITE, font=badge_font)

# Title
title_font = ttf("arialbd.ttf", 64)
center("HOMO HOTEL", title_font, 300, BLACK)
center("HAPPY HOUR", title_font, 372, ORANGE)

# Kicker
kicker_font = ttf("arialbd.ttf", 46)
center("PARKING + GETTING THERE", kicker_font, 480, BLACK)
d.line((W / 2 - 180, 552, W / 2 + 180, 552), fill=ORANGE, width=4)

# Date / venue block
serif = ttf("georgiab.ttf", 44)
center("Friday, August 7  \u00b7  6:00-8:00 PM", serif, 580, BLACK)
venue_font = ttf("arialbd.ttf", 40)
center("Courtyard Downtown", venue_font, 650, BLACK)
sub_font = ttf("arial.ttf", 32)
center("415 S Boston Ave, Tulsa", sub_font, 702, GRAY)

# ── Option cards ─────────────────────────────────────────────────────────────
card_x0, card_x1 = 90, W - 90
head_font = ttf("arialbd.ttf", 40)
body_font = ttf("arial.ttf", 32)

# Card 1: street parking
c1_top, c1_bot = 775, 955
d.rounded_rectangle((card_x0, c1_top, card_x1, c1_bot), radius=22, fill=CARD_BG,
                    outline=LIGHT, width=2)
d.text((card_x0 + 40, c1_top + 28), "STREET PARKING", fill=BLACK, font=head_font)
d.text((card_x0 + 40, c1_top + 88), "Your best bet. Grab a street spot", fill=GRAY, font=body_font)
d.text((card_x0 + 40, c1_top + 130), "near the hotel and walk right in.", fill=GRAY, font=body_font)

# Card 2: valet
c2_top, c2_bot = 985, 1165
d.rounded_rectangle((card_x0, c2_top, card_x1, c2_bot), radius=22, fill=CARD_BG,
                    outline=LIGHT, width=2)
d.text((card_x0 + 40, c2_top + 28), "VALET", fill=BLACK, font=head_font)
bb = d.textbbox((0, 0), "VALET", font=head_font)
d.text((card_x0 + 40 + (bb[2] - bb[0]) + 24, c2_top + 32), "$15", fill=ORANGE,
       font=ttf("arialbd.ttf", 40))
d.text((card_x0 + 40, c2_top + 88), "The Courtyard is extending its daily", fill=GRAY, font=body_font)
d.text((card_x0 + 40, c2_top + 130), "rate to our guests. Pull up out front.", fill=GRAY, font=body_font)

# Orange footer band
band_top = 1210
d.rectangle((0, band_top, W, H), fill=ORANGE)
ben_font = ttf("arialbd.ttf", 26)
center("FREE TO ATTEND  \u00b7  RAFFLE BENEFITTING PFLAG TULSA", ben_font, band_top + 28, WHITE)
foot_font = ttf("georgiab.ttf", 40)
center("homohotelhappyhour.com", foot_font, band_top + 70, WHITE)

OUT.parent.mkdir(parents=True, exist_ok=True)
im.save(OUT, "PNG", optimize=True)
print(f"Wrote {OUT} ({OUT.stat().st_size} bytes)")
