from PIL import Image, ImageOps, ImageDraw, ImageFont
import pathlib

SRC = pathlib.Path.home()/"Downloads/2CADB61A-1801-4A6A-B5FF-17856CFD24D6.JPEG"
OUT = pathlib.Path.home()/"polaris/assets"
OUT.mkdir(parents=True, exist_ok=True)

im = Image.open(SRC).convert("L")
print("source", im.size)

# white star on black -> alpha mask
mask = im.point(lambda v: 255 if v > 110 else 0)
bbox = mask.getbbox()
print("star bbox", bbox, "w/h ratio", round((bbox[2]-bbox[0])/(bbox[3]-bbox[1]), 3))
star = mask.crop(bbox)

# square it with a little padding so rotations never clip
side = int(max(star.size) * 1.04)
sq = Image.new("L", (side, side), 0)
sq.paste(star, ((side-star.width)//2, (side-star.height)//2))

def ink_alpha(size, color=(11, 11, 12)):
    a = sq.resize((size, size), Image.LANCZOS)
    img = Image.new("RGBA", (size, size), color+(0,))
    img.putalpha(a)
    return img

ink = ink_alpha(1024)
ink.save(OUT/"logo-ink.png")
ink_alpha(1024, (255, 255, 255)).save(OUT/"logo-white.png")

# favicon: ink star on white, tight-ish padding
def favicon(size, pad_ratio=0.06):
    bg = Image.new("RGBA", (size, size), (255, 255, 255, 255))
    inner = int(size*(1-2*pad_ratio))
    a = sq.resize((inner, inner), Image.LANCZOS)
    fg = Image.new("RGBA", (inner, inner), (11, 11, 12, 0))
    fg.putalpha(a)
    bg.alpha_composite(fg, (int(size*pad_ratio), int(size*pad_ratio)))
    return bg

favicon(32).save(OUT/"favicon-32.png")
favicon(180).save(OUT/"apple-touch-icon.png")
favicon(512).save(OUT/"favicon-512.png")
ink.save(OUT/"logo-ink.png")

# og image 1200x630: white, ink mark, wordmark
og = Image.new("RGB", (1200, 630), (255, 255, 255))
m = ink_alpha(300)
og.paste(m, (450, 130), m)
d = ImageDraw.Draw(og)
def font(sz, bold=False):
    for p in ["/System/Library/Fonts/Supplemental/Arial Bold.ttf" if bold else "/System/Library/Fonts/Supplemental/Arial.ttf",
              "/System/Library/Fonts/Helvetica.ttc"]:
        try: return ImageFont.truetype(p, sz)
        except Exception: pass
    return ImageFont.load_default()
f = font(74, True)
t = "POLARIS"
w = d.textlength(t, font=f)
d.text(((1200-w)/2, 452), t, font=f, fill=(11, 11, 12))
f2 = font(22)
t2 = "computer-generated characters on Ethereum"
w2 = d.textlength(t2, font=f2)
d.text(((1200-w2)/2, 552), t2, font=f2, fill=(110, 110, 116))
og.save(OUT/"og.png", quality=92)

for p in sorted(OUT.glob("*.png")):
    print(f"{p.name:22} {p.stat().st_size//1024}KB")
