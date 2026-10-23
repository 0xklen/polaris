#!/usr/bin/env python3
"""Polaris forms - animated pixel characters from the Universal LPC spritesheet set.

    python tools/lpc_gen.py --limit 6 --sheet /tmp/sheet.png     # preview
    python tools/lpc_gen.py --supply 4000                        # the collection

A token = one body + one item per slot (eyes, hair, torso, legs, feet ...), each item with
its own colour variant. Layers are composited per animation frame in zPos order and written
as an animated GIF plus a still hero frame.

Asset source: sanderfrenken/Universal-LPC-Spritesheet-Character-Generator (cloned at ~/repos/lpc).
Those assets are CC-BY-SA 3.0 / GPL 3.0 / OGA-BY 3.0 — attribution is mandatory and share-alike
applies. credits.json records the authors per layer so the notice can ship with the collection.
"""
import argparse, hashlib, json, pathlib, random, sys
from PIL import Image

ROOT = pathlib.Path(__file__).resolve().parent.parent
LPC = pathlib.Path.home() / "repos/lpc"
DEFS = LPC / "sheet_definitions"
SHEETS = LPC / "spritesheets"
OUT = ROOT / "nft"

FRAME = 64
COLS = 13
# animation row per facing (see sources/custom-animations.js)
ROW = {"n": 7, "w": 8, "s": 9, "e": 10}
WALK_FRAMES = 8

# slots we compose, in paint order (zPos from the definitions overrides this)
SLOTS = ["body", "head", "eyes", "hair", "clothes", "legs", "shoes", "hat", "beard", "mustache"]
BODIES = ["male", "female", "teen", "muscular", "pregnant"]

# the head shape follows the body build: human male/female/child heads
HEAD_BY_BODY = {
    "male": "heads_human_male",
    "female": "heads_human_female",
    "teen": "heads_human_child",
    "muscular": "heads_human_male",
    "pregnant": "heads_human_female",
}


def load_definitions():
    out = []
    for p in sorted(DEFS.glob("*.json")):
        try:
            d = json.loads(p.read_text())
        except Exception:
            continue
        if d.get("type_name") not in SLOTS:
            continue
        d["_stem"] = p.stem
        out.append(d)
    return out


def layer_file(layer, body, variant):
    """Resolve a definition layer to a PNG on disk, or None."""
    base = layer.get(body) or layer.get("male")
    if not base:
        return None
    base = base.strip("/")
    stem = SHEETS / base
    # a directory of variants, or a direct png
    if stem.suffix == ".png":
        return stem if stem.exists() else None
    if variant:
        cand = stem / f"{variant}.png"
        if cand.exists():
            return cand
    if (stem / "walk.png").exists():
        return stem / "walk.png"
    # single-file item sitting next to the directory
    sibling = stem.parent / f"{stem.name}.png"
    if sibling.exists():
        return sibling
    return None


def catalog():
    """One entry per composable (definition, body, variant) with its zPos and credits."""
    items = []
    for d in load_definitions():
        slot = d["type_name"]
        for key in [k for k in d if k.startswith("layer_")]:
            layer = d[key] or {}
            zpos = layer.get("zPos", 0)
            variants = d.get("variants") or [None]
            for body in BODIES:
                # head shape must match the body build (human head per build)
                if slot == "head" and HEAD_BY_BODY.get(body) != d.get("_stem"):
                    continue
                for variant in variants or [None]:
                    f = layer_file(layer, body, variant)
                    if not f:
                        continue
                    # non-human skeletons: fur_*, zombie and skeleton bodies/heads are a
                    # different shape and hats/hair float above them; skip them so
                    # every face keeps a real skin colour
                    if slot in ("body", "head") and variant:
                        v = variant.lower()
                        if "fur" in v or v in ("zombie", "skeleton"):
                            continue
                    items.append({
                        "slot": slot, "name": d.get("name", key), "body": body,
                        "variant": variant, "file": str(f), "z": zpos,
                        "credits": d.get("credits", []),
                    })
    return items



# Colour coherence: a token picks one hue family and its clothing/hats/shoes are drawn
# from that family plus ink, so a character reads as designed rather than randomly recoloured.
FAMILIES = {
    "ink":    ["black", "charcoal", "gray", "dark_gray", "light_gray", "bluegray", "ash", "silver", "white", "steel"],
    "warm":   ["red", "maroon", "crimson", "cerise", "rose", "pink", "orange", "gold", "yellow", "tan",
               "brown", "chocolate", "chestnut", "amber", "apricot", "carrot", "brass", "bronze"],
    "cold":   ["blue", "teal", "navy", "cyan", "sky", "cobalt", "cerulean", "azure", "aegean", "turquoise", "platinum"],
    "green":  ["green", "olive", "forest", "lime", "mint", "emerald", "jade"],
    "violet": ["purple", "violet", "plum", "lavender", "indigo", "magenta", "amethyst", "orchid"],
}
COVERING_HATS = ("barbuta", "helm", "sallet", "armet", "bascinet", "kettle", "close", "full helm", "great")

HAIR_FAMILY = ["black", "dark_gray", "gray", "light_gray", "ash", "white", "brown", "chestnut",
               "chocolate", "blonde", "ashblonde", "brunette", "red", "auburn", "silver", "tan"]


def variant_fits(variant, family):
    if not variant:
        return True
    v = variant.lower()
    if family == "hair":
        return any(k in v for k in HAIR_FAMILY)
    keys = FAMILIES[family] + FAMILIES["ink"]
    return any(k in v for k in keys)


def hash32(x):
    x &= 0xFFFFFFFF
    x ^= x >> 16
    x = (x * 0x7FEB352D) & 0xFFFFFFFF
    x ^= x >> 15
    x = (x * 0x846CA68B) & 0xFFFFFFFF
    x ^= x >> 16
    return x


def walk_strip(path, facing="s"):
    """Crop just the frames of one walk row from a full spritesheet."""
    im = Image.open(path).convert("RGBA")
    y = ROW[facing] * FRAME
    return im.crop((0, y, COLS * FRAME, y + FRAME))


def compose(token, by_slot, facing="s"):
    """Composite one character's walk row into 9 frames."""
    row = Image.new("RGBA", (COLS * FRAME, FRAME), (0, 0, 0, 0))
    layers = sorted(token["layers"], key=lambda l: l["z"])
    for l in layers:
        row.alpha_composite(walk_strip(l["file"], facing), (0, 0))
    return [row.crop((i * FRAME, 0, (i + 1) * FRAME, FRAME)) for i in range(WALK_FRAMES)]


def build_token(i, by_slot, rnd):
    body = rnd.choice(BODIES)
    family = rnd.choice(list(FAMILIES))
    layers, traits = [], []
    hat_name = ""
    body_variant = None
    for slot in SLOTS:
        pool = by_slot.get((slot, body)) or by_slot.get((slot, "male")) or []
        if not pool:
            continue
        # facial hair only reads on adult male builds, and never under a closed helmet
        if slot in ("beard", "mustache"):
            if body not in ("male", "muscular"):
                continue
            if any(k in hat_name.lower() for k in COVERING_HATS):
                continue
        if slot == "body":
            # skin tone is its own axis: pick any body colour, independent of the
            # clothing palette, so faces read as real skin rather than all-black
            pick = rnd.choice(pool)
            body_variant = pick["variant"]
        elif slot == "head":
            # the head must carry the same skin colour as the body
            same = [x for x in pool if x["variant"] == body_variant]
            pick = rnd.choice(same or pool)
        else:
            want = "hair" if slot == "hair" else family
            fitted = [x for x in pool if variant_fits(x["variant"], want)]
            pick = rnd.choice(fitted or pool)
        if slot == "hat":
            hat_name = pick["name"]
        layers.append({"slot": slot, "file": pick["file"], "z": pick["z"],
                       "name": pick["name"], "variant": pick["variant"],
                       "credits": pick["credits"]})
        # head shape is implied by the body build; no separate trait row
        if slot != "head":
            traits.append({"trait_type": slot.capitalize(),
                           "value": pick["name"] + (f" ({pick['variant']})" if pick["variant"] else "")})
    traits.append({"trait_type": "Palette", "value": family})
    return {"id": i, "body": body, "layers": layers, "attributes": traits}



def by_slot_lists(by_slot):
    return {f"{k[0]}|{k[1]}": v for k, v in by_slot.items()}


def render(tok, bs, look):
    """Composite, write gif + still, return metadata."""
    by_slot = {tuple(k.split("|")): v for k, v in bs.items()}
    frames = compose(tok, by_slot, look["facing"])
    big = look["scale"]
    frames_big = [f.resize((FRAME * big, FRAME * big), Image.NEAREST) for f in frames]
    if look["gray"]:
        from PIL import ImageOps
        frames_big = [ImageOps.grayscale(f).convert("RGBA") for f in frames_big]
    i = tok["id"]
    frames_big[0].save(OUT / "gif" / f"{i:04d}.gif", save_all=True, append_images=frames_big[1:],
                       duration=look["duration"], loop=0, optimize=True, disposal=2)
    hero = frames_big[0] if not look["scale_png"] else frames[0].resize(
        (FRAME * look["scale_png"], FRAME * look["scale_png"]), Image.NEAREST)
    if look["gray"] and look["scale_png"]:
        from PIL import ImageOps
        hero = ImageOps.grayscale(hero).convert("RGBA")
    hero.save(OUT / "png" / f"{i:04d}.png", optimize=True)
    # QC: a valid sprite occupies the head band and the feet band of the frame
    qc = frames[0].split()[3]
    head = qc.crop((18, 26, 46, 44))
    feet = qc.crop((18, 52, 46, 64))
    ok = (sum(1 for a in head.getdata() if a > 0) > 40 and
          sum(1 for a in feet.getdata() if a > 0) > 8)
    if not ok:
        (OUT / "gif" / f"{i:04d}.gif").unlink(missing_ok=True)
        (OUT / "png" / f"{i:04d}.png").unlink(missing_ok=True)
    return {"id": i, "name": f"Polaris Form #{i}", "body": tok["body"], "ok": ok,
            "image": f"nft/png/{i:04d}.png", "animation_url": f"nft/gif/{i:04d}.gif",
            "attributes": tok["attributes"]}


def _render_job(job):
    return render(*job)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--supply", type=int, default=4000)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--sheet", default="")
    ap.add_argument("--facing", default="s")
    ap.add_argument("--scale", type=int, default=3)
    ap.add_argument("--duration", type=int, default=110)
    ap.add_argument("--gray", action="store_true")
    ap.add_argument("--jobs", type=int, default=8)
    ap.add_argument("--scale-png", type=int, default=0)
    a = ap.parse_args()

    items = catalog()
    by_slot = {}
    for it in items:
        by_slot.setdefault((it["slot"], it["body"]), []).append(it)
    print(f"catalog: {len(items)} composable layers across {len(by_slot)} slot/body buckets", file=sys.stderr)
    for slot in SLOTS:
        n = len({it['file'] for it in items if it['slot'] == slot})
        print(f"  {slot:8} {n:5} files", file=sys.stderr)
    if not items:
        return 1

    n = a.limit or a.supply
    OUT.mkdir(exist_ok=True)
    (OUT / "gif").mkdir(exist_ok=True)
    (OUT / "png").mkdir(exist_ok=True)

    LOOK = {"scale": a.scale, "scale_png": a.scale_png, "duration": a.duration,
            "gray": a.gray, "facing": a.facing}

    # 1. assign unique trait sets up front (cheap, single process)
    tokens, seen = [], set()
    for i in range(1, n + 1):
        for attempt in range(80):
            tok = build_token(i, by_slot, random.Random(hash32(i * 7919 + attempt * 2654435761)))
            key = "|".join(f"{t_['trait_type']}:{t_['value']}" for t_ in tok["attributes"])
            if key not in seen:
                break
        seen.add(key)
        tok["key"] = key
        tokens.append(tok)
    print(f"trait sets: {len({t_['key'] for t_ in tokens})} unique of {len(tokens)}", file=sys.stderr)

    # 2. render in parallel, then repair anything that failed the head/feet QC
    workers = max(1, min(a.jobs, n))
    bs = by_slot_lists(by_slot)

    def render_batch(toks, label):
        jobs = [(tk, bs, LOOK) for tk in toks]
        out = []
        if workers == 1:
            for job in jobs:
                out.append(render(*job))
        else:
            import multiprocessing as mp
            with mp.get_context("fork").Pool(workers) as pool:
                for k, m in enumerate(pool.imap_unordered(_render_job, jobs, chunksize=8), 1):
                    out.append(m)
                    if k % 500 == 0:
                        print(f"  {label} {k}/{len(jobs)}", file=sys.stderr)
        return out

    meta = render_batch(tokens, "rendered")
    for rnd_i in range(1, 4):
        bad = sorted(m["id"] for m in meta if not m.get("ok", True))
        if not bad:
            break
        print(f"  QC failed on {len(bad)} tokens, re-rolling (round {rnd_i})", file=sys.stderr)
        retry = []
        for tid in bad:
            for attempt in range(1, 90):
                cand = build_token(tid, by_slot, random.Random(hash32(tid * 7919 + attempt * 2654435761 + rnd_i)))
                key = "|".join(f"{t_['trait_type']}:{t_['value']}" for t_ in cand["attributes"])
                if key not in seen:
                    seen.add(key)
                    retry.append(cand)
                    break
        if not retry:
            break
        fixed = {m["id"]: m for m in render_batch(retry, "repaired")}
        meta = [fixed.get(m["id"], m) if not m.get("ok", True) else m for m in meta]

    still = [m["id"] for m in meta if not m.get("ok", True)]
    if still:
        print(f"  WARNING: {len(still)} tokens still failed QC: {still[:10]}", file=sys.stderr)
        meta = [m for m in meta if m.get("ok", True)]
    for m in meta:
        m.pop("ok", None)
    meta.sort(key=lambda m: m["id"])

    (OUT / "metadata.json").write_text(json.dumps(meta, indent=1))

    # credits: every author/licence that actually got used
    used = {}
    for tok in meta:
        pass
    creds = {}
    for it in items:
        for c in it["credits"]:
            for author in c.get("authors", []):
                creds.setdefault(author, set()).update(c.get("licenses", []))
    (OUT / "credits.json").write_text(json.dumps({k: sorted(v) for k, v in creds.items()}, indent=1))
    print(f"tokens {len(meta)} · {len(set(json.dumps(m['attributes']) for m in meta))} unique trait sets", file=sys.stderr)

    if a.sheet:
        cols = 5
        cell = FRAME * a.scale
        rows = (min(n, 15) + cols - 1) // cols
        sheet = Image.new("RGBA", (cols * cell, rows * cell), (255, 255, 255, 255))
        for k in range(min(n, 15)):
            f = Image.open(OUT / "png" / f"{k+1:04d}.png").convert("RGBA")
            sheet.paste(f, ((k % cols) * cell, (k // cols) * cell), f)
        sheet.save(a.sheet)
        print("sheet", a.sheet, file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
