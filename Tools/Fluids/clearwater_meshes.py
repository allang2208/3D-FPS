"""Generate the Clearwater water plane and seabed as OBJ files, ready to import into UE.

Geometry is written as plain OBJ rather than built through the editor's GeometryScript
bindings. Two reasons:
  * the grid is fully determined by arithmetic, so it can be generated and verified without
    opening Unreal at all;
  * the water surface needs real interior vertices. A single quad would interpolate the
    material's world-position offset across hundreds of metres and flatten the water into a
    mirror, which is the exact failure this project keeps hitting with flat water planes.

Units are centimetres, matching UE. Meshes are authored in UE's Z-up frame, and the OBJ
exporter negates Y on the way out so UE's importer (which converts Y-up -> Z-up) lands the
mesh back in the intended orientation.

Run standalone:
    python Tools/Fluids/clearwater_meshes.py
"""
import argparse
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'SourceAssets' / 'ClearwaterWater20260926' / 'meshes'

# How far the basin rim rises ABOVE the water plane (z = 0). This is what gives the player
# somewhere to stand: with the whole bed below the waterline the camera ends up submerged
# and every frame is the back face of the water surface. It also has to be tall enough that
# the player, standing on the rim, has their eye clearly above the surface -- the eye sits
# roughly 170 cm above the feet.
SHORE_HEIGHT_CM = 60.0


def write_obj(path, positions, uvs, faces, comment):
    """Write one mesh. `positions` are UE-space cm; Y is negated to compensate for UE's
    Y-up OBJ import so the imported asset matches the authored orientation."""
    lines = ['# ' + comment, '# units: centimetres, authored by Tools/Fluids/clearwater_meshes.py', 'o mesh']
    for x, y, z in positions:
        lines.append('v %.4f %.4f %.4f' % (x, -y, z))
    for u, v in uvs:
        lines.append('vt %.6f %.6f' % (u, v))
    for a, b, c, d in faces:
        # 1-based indices; quads keep the grid tidy and the importer triangulates.
        lines.append('f %d/%d %d/%d %d/%d %d/%d' % (a + 1, a + 1, b + 1, b + 1,
                                                    c + 1, c + 1, d + 1, d + 1))
    path.write_text('\n'.join(lines) + '\n', encoding='ascii')
    return len(positions), len(faces)


def grid(half_cm, quads, z_fn, tile_cm):
    """A (quads+1)^2 vertex grid spanning [-half, +half] in X and Y.

    UVs tile every `tile_cm` so the material's procedural detail keeps a world-constant
    size rather than stretching across the plane.
    """
    step = 2.0 * half_cm / quads
    positions, uvs = [], []
    for j in range(quads + 1):
        for i in range(quads + 1):
            x = -half_cm + i * step
            y = -half_cm + j * step
            positions.append((x, y, z_fn(x, y)))
            uvs.append((x / tile_cm, y / tile_cm))
    faces = []
    stride = quads + 1
    for j in range(quads):
        for i in range(quads):
            a = j * stride + i
            faces.append((a, a + 1, a + stride + 1, a + stride))
    return positions, uvs, faces


def value_noise(x, y, seed):
    """Deterministic hash-based value noise; no numpy, no external textures."""
    M = 0xFFFFFFFF

    def h(ix, iy):
        n = (ix * 374761393 + iy * 668265263 + seed * 2246822519) & M
        n = ((n ^ (n >> 13)) * 1274126177) & M
        return ((n ^ (n >> 16)) & 0xFFFF) / 65535.0

    ix, iy = math.floor(x), math.floor(y)
    fx, fy = x - ix, y - iy
    ux = fx * fx * (3.0 - 2.0 * fx)
    uy = fy * fy * (3.0 - 2.0 * fy)
    a = h(ix, iy)
    b = h(ix + 1, iy)
    c = h(ix, iy + 1)
    d = h(ix + 1, iy + 1)
    return (a * (1 - ux) + b * ux) * (1 - uy) + (c * (1 - ux) + d * ux) * uy


def seabed_height(x, y, half_cm, depth_cm):
    """A test basin in three explicit zones (all radii are fractions of half_cm):

      r <= 0.30   deep floor at -depth_cm (default 3 m). A standing player's eye
                  (~170 cm above the feet) goes under, which is what makes the
                  underwater post-process and the subsurface view testable at all.
      0.30-0.60   graded rise from the deep floor to the shelf.
      0.60-0.80   shallow shelf at ~-50 cm: knee-deep wading, eye well above the
                  surface, the place to watch the waterline and shore caustics.
      0.80-1.00   shore rise from the shelf to +SHORE_HEIGHT_CM at the rim, crossing
                  z = 0 at about r = 0.89. The PlayerStart (SHORE_STAND_X = 9600 on a
                  10000 half-extent, r = 0.96) lands on dry bed ~+49 cm with ~7 m of
                  dry ground before the waterline -- teleport arrivals never splash.

    This is not decoration. With a uniformly deep bed the player spawns, falls, and lands
    with their eye UNDER the surface, so every frame is the back face of a single-sided
    translucent plane -- which renders as literally pure black. The rim has to break the
    water plane at z = 0 so there is somewhere to stand and look across, and the shelf
    has to be shallow enough to wade for the shoreline behaviour to be observable.

    Parameter order is (half_cm, depth_cm): swapping them silently makes the normalised
    radius tiny, which drives the whole basin to full depth and reads as a bottomless pit.

    Returns centimetres; negative is below the water plane.
    """
    SHELF_DEPTH_CM = 50.0
    r = math.hypot(x, y) / max(half_cm, 1.0)
    # Deep bowl -> shelf: 0 inside r=0.30, 1 past r=0.60.
    rise = smoothstep(0.30, 0.60, r)
    z = -depth_cm + rise * (depth_cm - SHELF_DEPTH_CM)
    # Shelf -> rim shore: 0 before r=0.80, 1 at the rim.
    shore = smoothstep(0.80, 1.00, r)
    z += shore * (SHORE_HEIGHT_CM + SHELF_DEPTH_CM)
    # Procedural relief for the shelf and bowl to read as terrain. Damped BEFORE the
    # waterline (fully gone by r=0.88) so the shoreline stays a clean curve; the spawn
    # radius (0.96) is past the damp range, so the arrival bed height is deterministic.
    relief = (value_noise(x / 4200.0, y / 4200.0, 3) - 0.5) * 44.0
    relief += (value_noise(x / 1300.0, y / 1300.0, 11) - 0.5) * 16.0
    return z + relief * (1.0 - smoothstep(0.72, 0.88, r))


def smoothstep(edge0, edge1, x):
    t = (x - edge0) / max(edge1 - edge0, 1e-9)
    t = max(0.0, min(1.0, t))
    return t * t * (3.0 - 2.0 * t)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    # Quad spacing has to stay well under the shortest wave the spectrum carries (~2 m),
    # or the world-position offset aliases into visible faceting. 200 m across at 192
    # quads is 1.04 m per quad -- about two quads per wave -- and stays a sane triangle
    # count for a translucency-heavy surface.
    #
    # The plane OVERHANGS the basin rim so the waterline lands on the bed's own slope rather
    # than on the water plane's edge. Without the overhang the shore mounds poke up through
    # the water and the plane boundary is plainly visible.
    ap.add_argument('--plane-half', type=float, default=10600.0, help='water plane half extent, cm')
    ap.add_argument('--plane-quads', type=int, default=192, help='water plane subdivisions per side')
    ap.add_argument('--bed-half', type=float, default=10000.0, help='seabed half extent, cm')
    ap.add_argument('--bed-quads', type=int, default=96, help='seabed subdivisions per side')
    ap.add_argument('--depth', type=float, default=300.0,
                    help='deep-zone floor depth, cm (the shallow shelf is fixed at ~50)')
    args = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)

    # Water surface: dead flat at rest (local Z = 0). The waves live in the material's
    # world-position offset, so the CPU-side height query stays a constant.
    pos, uv, faces = grid(args.plane_half, args.plane_quads, lambda x, y: 0.0, 400.0)
    nv, nf = write_obj(OUT / 'clearwater_plane.obj', pos, uv, faces,
                       'Clearwater water surface (flat rest plane, 4 m UV tile)')

    # Seabed: a basin whose rim breaks the water plane, so there is a shore to stand on.
    posb, uvb, facesb = grid(args.bed_half, args.bed_quads,
                             lambda x, y: seabed_height(x, y, args.bed_half, args.depth), 900.0)
    nvb, nfb = write_obj(OUT / 'clearwater_seabed.obj', posb, uvb, facesb,
                         'Clearwater seabed basin (%.0f cm deep, rim +%.0f cm)'
                         % (args.depth, SHORE_HEIGHT_CM))

    rim_z = max(z for _, _, z in posb)
    inner_z = min(z for _, _, z in posb)
    # Radius at which the bed crosses the water plane, so the spawn can be placed on dry
    # ground rather than in the water.
    shore_r = None
    for r_frac in [i / 200.0 for i in range(1, 200)]:
        if seabed_height(r_frac * args.bed_half, 0.0, args.bed_half, args.depth) >= 0.0:
            shore_r = r_frac * args.bed_half
            break

    def bed_z(r_frac):
        return seabed_height(r_frac * args.bed_half, 0.0, args.bed_half, args.depth)

    print('CLEARWATER_MESHES ' + str({
        'plane': {'verts': nv, 'quads': nf, 'tris': nf * 2,
                  'half_cm': args.plane_half, 'spacing_cm': round(2 * args.plane_half / args.plane_quads, 2)},
        'seabed': {'verts': nvb, 'quads': nfb, 'tris': nfb * 2,
                   'half_cm': args.bed_half, 'spacing_cm': round(2 * args.bed_half / args.bed_quads, 2),
                   'rim_z_cm': round(rim_z, 1), 'deepest_z_cm': round(inner_z, 1),
                   'waterline_radius_cm': round(shore_r, 0) if shore_r else None,
                   # Zone probes on +X so the spawn/arrival dryness is part of the bake's
                   # own verification, not something discovered in-game.
                   'deep_bed_z_cm': round(bed_z(0.0), 1),
                   'shelf_bed_z_cm': round(bed_z(0.70), 1),
                   'spawn_bed_z_cm': round(bed_z(0.96), 1),
                   'spawn_dry_margin_cm': round((0.96 * args.bed_half) - (shore_r or 0.0), 0)},
        'out': str(OUT),
    }))


if __name__ == '__main__':
    main()
