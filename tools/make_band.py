from PIL import Image
import pathlib

SRC = pathlib.Path.home()/"Downloads/47A8B14A-15DB-4AAB-8541-817921020C91.JPG"
OUT = pathlib.Path.home()/"polaris/assets"
im = Image.open(SRC).convert("RGB")
W, H = im.size
print("source", W, H)

# desktop: 2.35:1 scope crop, pulled left off the full-width version so the
# black field does not eat more than a third of the band
w = 1918
x0 = W - w                      # stays inside the source: no black padding
assert x0 >= 0 and x0 + w <= W, "crop runs past the source edge"
wide = im.crop((x0, 0, x0 + w, H))
wide.save(OUT/"form-band.webp", quality=84, method=6)
wide.save(OUT/"form-band.jpg", quality=82, optimize=True, progressive=True)

# mobile: 4:3 crop around the black/white boundary so the crop stays interesting
cw = round(H * 4 / 3)                      # 1088
x0 = 1090
crop = im.crop((x0, 0, x0 + cw, H))
print("mobile crop", crop.size)
crop.save(OUT/"form-band-mobile.webp", quality=84, method=6)
crop.save(OUT/"form-band-mobile.jpg", quality=82, optimize=True, progressive=True)

for p in sorted(OUT.glob("form-band*")):
    print(f"{p.name:26} {p.stat().st_size//1024}KB  {Image.open(p).size}")
