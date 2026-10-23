#!/usr/bin/env python3
"""Generate bust (head + shoulders) crops of the Polaris forms.

    ~/.venvs/psd/bin/python tools/make_busts.py [--jobs 8]

Reads nft/png/*.png, writes nft/bust/*.png. The crop is adaptive per sprite:
headroom above the tallest point + a square frame that holds head, shoulders
and upper chest, horizontally centred on the character.
"""
import argparse, multiprocessing as mp, pathlib, sys
from PIL import Image

ROOT = pathlib.Path(__file__).resolve().parent.parent
PNG = ROOT / "nft" / "png"
OUT = ROOT / "nft" / "bust"

SIDE_FRAC = 0.70      # square side as fraction of body height
HEADROOM_FRAC = 0.08  # top padding as fraction of body height
HEADROOM_MIN = 6      # px, at the 512px source scale


def bust_crop(path):
    im = Image.open(path).convert("RGBA")
    bbox = im.split()[3].getbbox()
    if not bbox:
        return None
    x0, y0, x1, y1 = bbox
    cx = (x0 + x1) // 2
    bh = y1 - y0
    side = int(SIDE_FRAC * bh)
    headroom = max(int(HEADROOM_FRAC * bh), HEADROOM_MIN)
    top = y0 - headroom
    left = cx - side // 2
    W, H = im.size
    left = max(0, min(left, W - side))
    top = max(0, min(top, H - side))
    return im.crop((left, top, left + side, top + side))


def job(i):
    src = PNG / f"{i:04d}.png"
    dst = OUT / f"{i:04d}.png"
    if dst.exists() and dst.stat().st_mtime >= src.stat().st_mtime:
        return i, "skip"
    crop = bust_crop(src)
    if crop is None:
        return i, "empty"
    crop.save(dst, optimize=True)
    return i, "ok"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--jobs", type=int, default=8)
    a = ap.parse_args()
    OUT.mkdir(exist_ok=True)
    ids = [int(p.stem) for p in PNG.glob("*.png")]
    ids.sort()
    workers = max(1, min(a.jobs, len(ids)))
    done = skip = 0
    if workers == 1:
        for i in ids:
            _, s = job(i)
            done += s != "skip"; skip += s == "skip"
    else:
        with mp.get_context("fork").Pool(workers) as pool:
            for k, (_, s) in enumerate(pool.imap_unordered(job, ids, chunksize=16), 1):
                done += s != "skip"; skip += s == "skip"
                if k % 500 == 0:
                    print(f"  {k}/{len(ids)}", file=sys.stderr)
    print(f"busts: {len(ids)} total · {done} written · {skip} skipped", file=sys.stderr)


if __name__ == "__main__":
    main()
