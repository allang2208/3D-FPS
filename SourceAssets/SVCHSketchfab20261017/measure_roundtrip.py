"""Measure the FBX round trip for both the accepted SVD and the new SVCh.

The project rule is `(x, -y, z)` from the Blender export scene to UE. Instead of
trusting that, this imports the *exported* FBX back into Blender (default importer
reproduces the export scene) and prints the bboxes of the arm mesh and the weapon
parts, so the actual mapping can be read off and compared with the UE dump.
"""
import sys
from pathlib import Path

import bpy
import io_scene_fbx.import_fbx as ifbx

ifbx.blen_read_light = lambda *a, **k: None

FILES = {
    'svd': Path('D:/FPS3D/FPSGAME/SourceAssets/SVDCompletion20260923/Authored/SK_SVD_Manny.fbx'),
    'svch': Path('D:/FPS3D/FPSGAME/SourceAssets/SVCHSketchfab20261017/Exports/SK_SVCH_Manny.fbx'),
}


def bbox(objs):
    import mathutils
    pts = [o.matrix_world @ v.co for o in objs for v in o.data.vertices]
    if not pts:
        return None
    lo = [min(p[i] for p in pts) for i in range(3)]
    hi = [max(p[i] for p in pts) for i in range(3)]
    return [round(v, 3) for v in lo], [round(v, 3) for v in hi]


for key, path in FILES.items():
    if not path.exists():
        print('MISSING', key, path, flush=True)
        continue
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=str(path))
    meshes = [o for o in bpy.context.scene.objects if o.type == 'MESH']
    print('=== %s  (%d meshes)' % (key, len(meshes)), flush=True)
    arm = [o for o in meshes if 'Arms' in o.name or 'Manny' in o.name]
    gun = [o for o in meshes if o not in arm]
    if arm:
        print('   arms  bbox', bbox(arm), flush=True)
    if gun:
        print('   gun   bbox', bbox(gun), flush=True)
    for o in sorted(gun, key=lambda x: x.name)[:8]:
        print('     %-30s %s' % (o.name, bbox([o])), flush=True)
