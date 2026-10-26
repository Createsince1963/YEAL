"""Draws the MediaOrbit mark (same geometry as BrandLogo.qml) in high resolution for the Player button: assets/logo_player.png."""
from pathlib import Path
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "BIN" / "versions" / "v0.1" / "PyModul" / "yeal" / "ui" / "qml" / "assets" / "logo_player.png"
SIZE, SS = 192, 4


def rounded(points, r, size, steps=24):
    n, out = len(points), []
    for i in range(n):
        p0, p1, p2 = points[(i - 1) % n], points[i], points[(i + 1) % n]
        v1, v2 = (p0[0] - p1[0], p0[1] - p1[1]), (p2[0] - p1[0], p2[1] - p1[1])
        l1, l2 = (v1[0] ** 2 + v1[1] ** 2) ** .5, (v2[0] ** 2 + v2[1] ** 2) ** .5
        k = min(r, l1 / 2, l2 / 2)
        a = (p1[0] + v1[0] / l1 * k, p1[1] + v1[1] / l1 * k)
        b = (p1[0] + v2[0] / l2 * k, p1[1] + v2[1] / l2 * k)
        for s in range(steps + 1):                  # quadratic bezier a -> p1 -> b
            t = s / steps
            out.append((((1 - t) ** 2 * a[0] + 2 * (1 - t) * t * p1[0] + t * t * b[0]) * size,
                        ((1 - t) ** 2 * a[1] + 2 * (1 - t) * t * p1[1] + t * t * b[1]) * size))
    return out


def gradient(size, stops, p0, p1):
    img = Image.new("RGB", (size, size))
    px = img.load()
    dx, dy = p1[0] - p0[0], p1[1] - p0[1]
    ll = dx * dx + dy * dy
    for y in range(size):
        for x in range(size):
            t = max(0.0, min(1.0, ((x - p0[0]) * dx + (y - p0[1]) * dy) / ll))
            for i in range(len(stops) - 1):
                if t <= stops[i + 1][0]:
                    u = (t - stops[i][0]) / (stops[i + 1][0] - stops[i][0])
                    px[x, y] = tuple(int(stops[i][1][c] * (1 - u) + stops[i + 1][1][c] * u) for c in range(3))
                    break
    return img


S = SIZE * SS
main = Image.new("L", (S, S), 0)
ImageDraw.Draw(main).polygon(rounded([(.10, .06), (.96, .50), (.10, .94)], .17, S), fill=255)
lobe = Image.new("L", (S, S), 0)
ImageDraw.Draw(lobe).polygon(rounded([(.10, .55), (.52, .76), (.10, .94)], .15, S), fill=255)
dark = Image.new("L", (S, S), 0)
ImageDraw.Draw(dark).polygon(rounded([(.33, .30), (.70, .50), (.33, .70)], .07, S), fill=255)
img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
g1 = gradient(S, [(0.0, (0x1F, 0xE0, 0xF5)), (0.55, (0x2D, 0x84, 0xF6)), (1.0, (0x73, 0x58, 0xF0))], (0, 0), (S, S))
img.paste(g1, (0, 0), main)
g2 = gradient(S, [(0.0, (0x1E, 0x6B, 0xFF)), (1.0, (0x2B, 0x3F, 0xD8))], (0, S * .5), (S * .6, S))
img.paste(g2, (0, 0), lobe)
img.paste(Image.new("RGB", (S, S), (0x0B, 0x14, 0x20)), (0, 0), dark)
img = img.resize((SIZE, SIZE), Image.LANCZOS)
img.save(OUT)
print("mark", img.size)
