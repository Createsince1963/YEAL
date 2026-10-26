"""Makes the logo files of the top buttons from the sources in docs/brand (run once; the result is in yeal/ui/qml/assets)."""
import colorsys
from collections import deque
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter

ROOT = Path(r"C:\Users\mail\AI_Coworker_Claude\APK YEAL")
SRC = ROOT / "docs" / "brand"
OUT = ROOT / "BIN" / "versions" / "v0.1" / "PyModul" / "yeal" / "ui" / "qml" / "assets"


def trim(im, pad=0):
    box = im.getchannel("A").point(lambda a: 255 if a > 8 else 0).getbbox()
    im = im.crop(box)
    if pad:
        canvas = Image.new("RGBA", (im.width + 2 * pad, im.height + 2 * pad), (0, 0, 0, 0))
        canvas.paste(im, (pad, pad))
        im = canvas
    return im


def key_black(im, limit=34):
    """Black background -> transparent: only black that is connected to the border (the dark parts inside the mark stay)."""
    im = im.convert("RGBA")
    w, h = im.size
    px = im.load()
    seen = [[False] * w for _ in range(h)]
    queue = deque((x, y) for x in range(w) for y in (0, h - 1))
    queue.extend((x, y) for y in range(h) for x in (0, w - 1))
    while queue:
        x, y = queue.popleft()
        if not (0 <= x < w and 0 <= y < h) or seen[y][x]:
            continue
        r, g, b, a = px[x, y]
        if max(r, g, b) > limit:
            continue
        seen[y][x] = True
        px[x, y] = (r, g, b, 0)
        queue.extend(((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)))
    return im


def erode(im, size=3):
    """One pixel less at the edge: the dark rim left by the keyed black background disappears on light themes."""
    r, g, b, a = im.split()
    return Image.merge("RGBA", (r, g, b, a.filter(ImageFilter.MinFilter(size))))


def fit_height(im, height):
    return im.resize((max(1, round(im.width * height / im.height)), height), Image.LANCZOS)


# ---- MediaOrbit: the whole logo (mark + name + slogan) and the mark alone
full = key_black(Image.open(SRC / "mediaorbit_source.png"))
full = trim(erode(full), 2)
full.save(OUT / "logo_mediaorbit.png")
small = Image.open(SRC / "mediaorbit_source.png").convert("RGB")
mark = trim(erode(key_black(small).crop((0, 0, 90, small.height))), 1)
mark = fit_height(mark, 96)
mark.save(OUT / "logo_player.png")
print("mark", mark.size, "full", full.size)

# ---- YouTube: red -> blue, trimmed, smaller
yt = trim(Image.open(SRC / "youtube_source.png").convert("RGBA"))
r, g, b, a = yt.split()
rgb = Image.merge("RGB", (r, g, b))
hsv = rgb.convert("HSV")
h, s, v = hsv.split()
shift = round(0.60 * 255)                 # red (0) -> blue (216 degrees)
h = h.point(lambda x: (x + shift) % 256)
blue = Image.merge("HSV", (h, s, v)).convert("RGB")
yt_blue = Image.merge("RGBA", (*blue.split(), a))
fit_height(yt_blue, 96).save(OUT / "logo_youtube.png")

# ---- TIDAL: white mark (dark theme), dark mark (light theme), white mark on a blue square (TIDAL DIY)
tid = Image.open(SRC / "tidal_source.jpg").convert("L")
tid = tid.point(lambda x: 0 if x < 40 else min(255, x))
white = Image.merge("RGBA", (Image.new("L", tid.size, 255),) * 3 + (tid,))
white = trim(white)
fit_height(white, 96).save(OUT / "logo_tidal.png")
dark = Image.merge("RGBA", (Image.new("L", tid.size, 20),) * 3 + (tid,))
fit_height(trim(dark), 96).save(OUT / "logo_tidal_dark.png")
size = 128
tile = Image.new("RGBA", (size, size), (0, 0, 0, 0))
ImageDraw.Draw(tile).rounded_rectangle((0, 0, size - 1, size - 1), radius=size // 4, fill=(10, 132, 255, 255))
mk = trim(white)
mk = mk.resize((round(size * 0.62), round(mk.height * size * 0.62 / mk.width)), Image.LANCZOS)
tile.alpha_composite(mk, ((size - mk.width) // 2, (size - mk.height) // 2))
tile.save(OUT / "logo_tidal_diy.png")
print("done")
