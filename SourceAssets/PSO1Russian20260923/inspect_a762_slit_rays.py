"""Find see-through slits at Body/Mount junction by camera-style rays."""
import bpy, json, math
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree

O = Path(r'D:\FPS3D\FPSGAME\SourceAssets\PSO1Russian20260923')
OUT = O / 'inspect_akm_a762'
DELTA = Vector((0.010, -0.015, 0.035))
AXIS_Z = 0.1024

bpy.ops.wm.open_mainfile(filepath=str(O / 'PSO1_A762_Editable.blend'))
body = bpy.data.objects['PSO_ScopeBody']
mount = bpy.data.objects['PSO_ScopeMount']
lens = bpy.data.objects['PSO_ScopeLens']

def parts(ob, skip_glass=False):
    mw = ob.matrix_world
    v = [mw @ x.co for x in ob.data.vertices]
    f = []
    for p in ob.data.polygons:
        mat = ob.data.materials[p.material_index] if ob.data.materials else None
        if skip_glass and mat and 'OpticalGlass' in mat.name:
            continue
        f.append(tuple(p.vertices))
    return v, f

bv, bf = parts(body)
mv, mf = parts(mount)
lv, lf = parts(lens, True)
opaque = BVHTree.FromPolygons(
    bv + mv + lv,
    bf + [tuple(len(bv)+i for i in face) for face in mf] + [tuple(len(bv)+len(mv)+i for i in face) for face in lf],
)
body_only = BVHTree.FromPolygons(bv, bf)
mount_only = BVHTree.FromPolygons(mv, mf)

# View from below-left (typical FP hollow sighting): rays upward into tube underside near mount
misses = []
hits_body_then_void = []
for yi in range(-12, 4):
    y = yi * 0.01
    for xi in range(0, 12):
        x = 0.005 + xi * 0.004  # mount side of tube
        # start below tube
        for zi, z in enumerate([0.02, 0.04, 0.055, 0.07]):
            origin = Vector((x, y, z)) + DELTA
            direction = Vector((0, 0, 1))  # look up into tube bottom
            h = opaque.ray_cast(origin, direction, 0.12)
            if h[0] is None:
                misses.append({'x': round(x, 4), 'y': round(y, 4), 'z': round(z, 4), 'dir': 'up'})
                continue
            # After first hit, continue; if next segment escapes through without second hit within tube, slit
            pos = h[0] + direction * 0.0008
            h2 = opaque.ray_cast(pos, direction, 0.08)
            # Also cast into tube from hit along +X (toward mount) and -X
            for dname, dvec in (('to_mount', Vector((1, 0, 0))), ('to_right', Vector((-1, 0, 0))), ('along_y', Vector((0, 1, 0)))):
                hh = opaque.ray_cast(h[0] + dvec * 0.0005, dvec, 0.03)
                if hh[0] is None:
                    # Confirm we are near the tube shell (first hit was body)
                    hb = body_only.ray_cast(origin, direction, 0.12)
                    hm = mount_only.ray_cast(origin, direction, 0.12)
                    hits_body_then_void.append({
                        'x': round(x, 4), 'y': round(y, 4), 'z_start': round(z, 4),
                        'hit_z': round((h[0] - DELTA).z, 4),
                        'escape': dname,
                        'first': 'body' if hb[0] is not None and (hm[0] is None or hb[3] <= hm[3]) else 'mount',
                    })

# Exterior side view rays: from +X (mount side) toward tube, then check if you can see sky through
side_through = []
for yi in range(-12, 6):
    y = yi * 0.01
    for zi in range(4, 14):
        z = zi * 0.01
        origin = Vector((0.07, y, z)) + DELTA
        direction = Vector((-1, 0, 0))
        # March through collecting hits
        pos = origin.copy()
        hit_count = 0
        last = None
        for _ in range(10):
            h = opaque.ray_cast(pos, direction, 0.15)
            if h[0] is None:
                break
            hit_count += 1
            last = h[0]
            pos = h[0] + direction * 0.0006
        # Odd hits or single hit means entered shell and exited to void on far side incorrectly for a closed tube
        # For a closed thin shell, looking through diameter should get 2 hits (near and far wall)
        if hit_count == 1:
            p = last - DELTA
            side_through.append({'y': round(y, 4), 'z': round(z, 4), 'hits': 1, 'exit_x': round(p.x, 4)})
        elif hit_count == 0:
            side_through.append({'y': round(y, 4), 'z': round(z, 4), 'hits': 0})

result = {
    'up_misses': len(misses),
    'up_miss_sample': misses[:20],
    'after_hit_escape': len(hits_body_then_void),
    'escape_sample': hits_body_then_void[:40],
    'side_single_or_zero_hits': len(side_through),
    'side_sample': side_through[:40],
}
(OUT / 'a762_slit_rays.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
print('A762_SLIT_RAYS', json.dumps({k: (v if not isinstance(v, list) else len(v)) for k, v in result.items()}), flush=True)
print('SAMPLE_ESCAPE', json.dumps(hits_body_then_void[:15]), flush=True)
print('SAMPLE_SIDE', json.dumps(side_through[:20]), flush=True)
