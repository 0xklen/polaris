#!/usr/bin/env python3
"""Turn a Polaris form PNG into a 3D-printable STL relief + a heightmap JSON
for a 3D preview.

Usage:
    python3 tools/to_stl.py nft/png/0001.png out/0001
        -> writes out/0001.stl (binary) and out/0001.hmap.json

The output is a square medallion: a 2 mm base plate with the character raised
as a relief (1.5-4.5 mm tall), sized ~50 mm across. Flat on the print bed.
"""
import json, math, struct, sys, os
from PIL import Image

N = 48            # grid resolution (48 x 48 cells)
PLATE_MM = 50.0   # medallion size
BASE_MM = 2.0     # base plate thickness
RELIEF_MIN = 1.5  # min relief height over the base
RELIEF_MAX = 3.0  # extra relief scaled by brightness


def height_at(h, i, j, n):
    """Bilinear-ish sample of the height field at grid node (i, j)."""
    def sample(x, y):
        x = min(max(x, 0), n - 1)
        y = min(max(y, 0), n - 1)
        return h[y][x]
    x0, y0 = i - 0.5, j - 0.5
    x1, y1 = min(x0 + 1, n - 1), min(y0 + 1, n - 1)
    fx, fy = x0 - math.floor(x0), y0 - math.floor(y0)
    a = sample(math.floor(x0), math.floor(y0))
    b = sample(math.ceil(x0), math.floor(y0))
    c = sample(math.floor(x0), math.ceil(y0))
    d = sample(math.ceil(x0), math.ceil(y0))
    top = a + (b - a) * fx
    bot = c + (d - c) * fx
    return top + (bot - top) * fy


def build_heights(png_path):
    im = Image.open(png_path).convert("RGBA").resize((N, N), Image.LANCZOS)
    px = im.load()
    h = [[0.0] * N for _ in range(N)]
    for j in range(N):
        for i in range(N):
            r, g, b, a = px[i, j]
            if a < 128:
                z = BASE_MM
            else:
                gray = (r + g + b) / 3.0
                z = BASE_MM + RELIEF_MIN + (gray / 255.0) * RELIEF_MAX
            h[j][i] = z
    return h


def write_stl(verts, tris, out_path):
    def normal(a, b, c):
        ax, ay, az = verts[a]
        bx, by, bz = verts[b]
        cx, cy, cz = verts[c]
        ux, uy, uz = bx - ax, by - ay, bz - az
        vx, vy, vz = cx - ax, cy - ay, cz - az
        nx = uy * vz - uz * vy
        ny = uz * vx - ux * vz
        nz = ux * vy - uy * vx
        L = math.sqrt(nx * nx + ny * ny + nz * nz) or 1.0
        return (nx / L, ny / L, nz / L)

    with open(out_path, "wb") as f:
        f.write(b"POLARIS FORM relief - 3D printable medallion" + b"\x00" * 36)
        f.write(struct.pack("<I", len(tris)))
        for (a, b, c) in tris:
            nx, ny, nz = normal(a, b, c)
            f.write(struct.pack("<3f", nx, ny, nz))
            for idx in (a, b, c):
                f.write(struct.pack("<3f", *verts[idx]))
            f.write(struct.pack("<H", 0))


def gen(png_path, out_prefix):
    h = build_heights(png_path)
    cell = PLATE_MM / N
    side = N + 1
    verts = []
    for j in range(side):
        for i in range(side):
            z = height_at(h, i, j, N)
            verts.append((i * cell, j * cell, z))
    off = side * side
    for j in range(side):
        for i in range(side):
            verts.append((i * cell, j * cell, 0.0))

    tris = []
    # top surface
    for j in range(N):
        for i in range(N):
            a = j * side + i
            b = j * side + i + 1
            c = (j + 1) * side + i
            d = (j + 1) * side + i + 1
            tris.append((a, c, b))
            tris.append((b, c, d))
    # bottom surface
    for j in range(N):
        for i in range(N):
            a = off + j * side + i
            b = off + j * side + i + 1
            c = off + (j + 1) * side + i
            d = off + (j + 1) * side + i + 1
            tris.append((a, b, c))
            tris.append((b, d, c))
    # side walls
    for i in range(N):
        a, b = i, i + 1
        c, d = off + i, off + i + 1
        tris.append((a, c, b)); tris.append((b, c, d))       # j = 0
        a, b = N * side + i, N * side + i + 1
        c, d = off + N * side + i, off + N * side + i + 1
        tris.append((a, b, c)); tris.append((b, d, c))       # j = N
    for j in range(N):
        a, b = j * side, (j + 1) * side
        c, d = off + j * side, off + (j + 1) * side
        tris.append((a, b, c)); tris.append((b, d, c))       # i = 0
        a, b = j * side + N, (j + 1) * side + N
        c, d = off + j * side + N, off + (j + 1) * side + N
        tris.append((a, c, b)); tris.append((b, c, d))       # i = N

    write_stl(verts, tris, out_prefix + ".stl")
    # preview heightmap: 48x48 flat list of heights (mm)
    with open(out_prefix + ".hmap.json", "w") as f:
        json.dump({"n": N, "plate": PLATE_MM,
                   "base": BASE_MM, "h": [v for row in h for v in row]}, f)
    print(f"wrote {out_prefix}.stl ({len(tris)} tris) and {out_prefix}.hmap.json")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    gen(sys.argv[1], sys.argv[2])
