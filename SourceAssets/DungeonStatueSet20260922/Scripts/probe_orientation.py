"""Decide whether a statue's yaw correction actually reached the exported FBX.

Eyeballing thumbnails proved unreliable, so this compares the raw source OBJ with the
normalised FBX numerically: an odd multiple of 90 deg about Z flips the sign of the
upper-body centroid offset relative to the whole-model centroid (and swaps X/Y for
90 deg). Signed offsets are printed for both, and the verdict is computed.

Run:
    "E:/Program Files/Blender Foundation/Blender 5.1/blender.exe" --background --factory-startup \
        --python <this file> -- <case_root> <key>
"""
import json
import sys
from pathlib import Path

import bpy
from mathutils import Vector


def centroid(objs):
    total = Vector((0, 0, 0))
    count = 0
    for o in objs:
        mw = o.matrix_world
        for v in o.data.vertices:
            total += mw @ v.co
            count += 1
    return total / max(count, 1)


def slice_centroid(objs, zmin, zmax):
    total = Vector((0, 0, 0))
    count = 0
    for o in objs:
        mw = o.matrix_world
        for v in o.data.vertices:
            p = mw @ v.co
            if zmin <= p.z <= zmax:
                total += p
                count += 1
    return (total / count) if count else None


def profile(objs):
    pts = [o.matrix_world @ Vector(c) for o in objs for c in o.bound_box]
    zmin = min(p.z for p in pts)
    zmax = max(p.z for p in pts)
    h = zmax - zmin
    all_c = centroid(objs)
    upper = slice_centroid(objs, zmin + 0.60 * h, zmin + 0.80 * h)
    lower = slice_centroid(objs, zmin + 0.05 * h, zmin + 0.30 * h)
    return {
        'all': [round(v, 4) for v in all_c],
        'upper_offset': [round(upper[i] - all_c[i], 4) for i in range(3)] if upper else None,
        'lower_offset': [round(lower[i] - all_c[i], 4) for i in range(3)] if lower else None,
    }


def main():
    args = sys.argv[sys.argv.index("--") + 1:]
    case = Path(args[0])
    key = args[1]
    cfg = json.loads((case / 'Config' / 'statues.json').read_text(encoding='utf-8-sig'))
    statue = next(s for s in cfg['statues'] if s['key'] == key)

    src = sorted((case / 'Source' / key).rglob('*.obj'))[0]
    fbx = case / 'Authored' / (statue['mesh_name'] + '.fbx')

    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.wm.obj_import(filepath=str(src), forward_axis='NEGATIVE_Y', up_axis='Z')
    raw = profile([o for o in bpy.context.scene.objects if o.type == 'MESH'])

    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=str(fbx))
    final = profile([o for o in bpy.context.scene.objects if o.type == 'MESH'])

    out = {'key': key, 'yaw_in_config': statue.get('yaw_deg', 0.0),
           'source_upper_offset': raw['upper_offset'], 'final_upper_offset': final['upper_offset'],
           'source_lower_offset': raw['lower_offset'], 'final_lower_offset': final['lower_offset']}
    su, fu = raw['upper_offset'], final['upper_offset']
    if su and fu:
        out['upper_dx_sign_flip'] = (su[0] > 0) != (fu[0] > 0)
        out['upper_dy_sign_flip'] = (su[1] > 0) != (fu[1] > 0)
    print('ORIENT_PROBE ' + json.dumps(out))


main()
