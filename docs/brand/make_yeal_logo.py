"""Replaces the Yeal logo (0.9.1.33): icon.png (window / task bar / sidebar), Logo.ico and Logo.png, and puts the new tile into the
splash / card / mark pictures instead of the old red one. Sources: yeal_logo_new_source.jpg and the old_*.png copies in this folder."""
from collections import deque
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter

ROOT = Path(__file__).resolve().parents[2]
BRAND = ROOT / "docs" / "brand"
ASSETS = ROOT / "BIN" / "versions" / "v0.1" / "PyModul" / "yeal" / "ui" / "qml" / "assets"

src = Image.open(BRAND / "yeal_logo_new_source.jpg").convert("RGB")
# the tile: everything that is not the pure black around it
w, h = src.size
px = src.load()
box = src.convert("L").point(lambda v: 255 if v > 9 else 0).getbbox()
tile = src.crop(box)
side = max(tile.size)
sq = Image.new("RGB", (side, side), (0, 0, 0))
sq.paste(tile, ((side - tile.width) // 2, (side - tile.height) // 2))
# rounded corners as an alpha mask (the picture has black corners); radius like the tile (about 22 % of the side)
S = 4
mask = Image.new("L", (side * S, side * S), 0)
ImageDraw.Draw(mask).rounded_rectangle((0, 0, side * S - 1, side * S - 1), radius=int(side * S * 0.225), fill=255)
mask = mask.resize((side, side), Image.LANCZOS)
tile_rgba = sq.convert("RGBA")
tile_rgba.putalpha(mask)
print("tile", tile_rgba.size)

tile_rgba.resize((256, 256), Image.LANCZOS).save(ASSETS / "icon.png")
sizes = [(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
tile_rgba.resize((256, 256), Image.LANCZOS).save(ROOT / "docs" / "Logo.ico", sizes=sizes)
tile_rgba.resize((512, 512), Image.LANCZOS).save(ROOT / "docs" / "Logo_tile.png")


def swap_tile(old_name, out_path, region, tile_px):
    """Wipes the old tile (region = x0, y0, x1, y1): every row is filled by a blend between the background left and right of the
    region (the background there is a soft dark gradient), then the new tile is put in the middle of it."""
    im = Image.open(BRAND / old_name).convert("RGB")
    x0, y0, x1, y1 = region
    px = im.load()
    fill = im.copy()
    fp = fill.load()
    for y in range(y0, y1):
        left = [sum(px[x0 - 1 - i, y][c] for i in range(3)) / 3 for c in range(3)]
        right = [sum(px[x1 + i, y][c] for i in range(3)) / 3 for c in range(3)]
        for x in range(x0, x1):
            t = (x - x0) / max(1, x1 - x0 - 1)
            fp[x, y] = tuple(int(left[c] * (1 - t) + right[c] * t) for c in range(3))
    fill = fill.filter(ImageFilter.GaussianBlur(6))
    mask = Image.new("L", im.size, 0)
    ImageDraw.Draw(mask).rectangle((x0 + 6, y0 + 6, x1 - 6, y1 - 6), fill=255)
    mask = mask.filter(ImageFilter.GaussianBlur(10))
    im = Image.composite(fill, im, mask).convert("RGBA")
    t = tile_rgba.resize((tile_px, tile_px), Image.LANCZOS)
    im.alpha_composite(t, ((x0 + x1 - tile_px) // 2, (y0 + y1 - tile_px) // 2))
    im.convert("RGB").save(out_path)


swap_tile("old_logo_splash.png", ASSETS / "logo_splash.png", (330, 20, 820, 410), 360)
swap_tile("old_logo_card.png", ASSETS / "logo_card.png", (275, 15, 690, 345), 300)
swap_tile("old_logo_mark.png", ASSETS / "logo_mark.png", (275, 15, 690, 345), 300)
print("done")
