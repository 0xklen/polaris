"""Pick a scrim that keeps white footer text readable over the band image."""
from PIL import Image
import pathlib

OUT = pathlib.Path.home()/"polaris/assets"


def lum(rgb):
    def f(c):
        c = c / 255
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = rgb[:3]
    return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b)


def ratio(a, b):
    la, lb = lum(a), lum(b)
    hi, lo = max(la, lb), min(la, lb)
    return (hi + 0.05) / (lo + 0.05)


INK = (11, 11, 12)
WHITE = (255, 255, 255)

# candidate gradients: (label, stops as (position, alpha))
cands = {
    "flat .78": [(0, .78), (1, .78)],
    "grad .94 -> .70": [(0, .94), (0.38, .88), (0.70, .78), (1, .70)],
    "grad .95 -> .80": [(0, .95), (0.40, .90), (0.75, .84), (1, .80)],
}

for name, img_name in (("desktop", "form-band.jpg"), ("mobile", "form-band-mobile.jpg")):
    im = Image.open(OUT/img_name).convert("RGB")
    w, h = im.size
    px = im.load()
    print(f"\n{name} {w}x{h}")
    for label, stops in cands.items():
        worst = 99
        worst_x = None
        for xi in range(0, w, max(1, w//40)):
            a = 0
            for i in range(len(stops)-1):
                p0, a0 = stops[i]; p1, a1 = stops[i+1]
                t = xi/(w-1)
                if p0 <= t <= p1:
                    k = (t-p0)/(p1-p0) if p1 > p0 else 0
                    a = a0 + (a1-a0)*k
                    break
            for yi in range(0, h, max(1, h//20)):
                r, g, b = px[xi, yi]
                comp = tuple(round(c*(1-a) + INK[i]*a) for i, c in enumerate((r, g, b)))
                cr = ratio(WHITE, comp)
                if cr < worst:
                    worst, worst_x = cr, (xi, yi, comp)
        print(f"  {label:<18} worst contrast vs white: {worst:.2f}:1  at {worst_x}")
