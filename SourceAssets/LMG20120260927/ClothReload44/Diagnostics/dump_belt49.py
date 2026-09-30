"""Belt49 cells in UE component cm (rest), registered to the UE reference skeleton by a
similarity fit of bone heads.  blender -b --factory-startup --python dump_belt49.py -- <fbx> <out.npz>"""
import bpy, sys, json
import numpy as np
from pathlib import Path

args = sys.argv[sys.argv.index('--') + 1:]
fbx, out = Path(args[0]), Path(args[1])
ROOT = Path('D:/FPS3D/FPSGAME/SourceAssets/LMG20120260927')
inputs = json.loads((ROOT / 'ClothFeed33' / 'inputs.json').read_text())['meshes']['201']
ue_rest = {n: np.array(v[:3]) for n, v in zip(inputs['names'], inputs['rest'])}
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=str(fbx), use_anim=False, ignore_leaf_bones=False, automatic_bone_orientation=False)
arm = next(o for o in bpy.context.scene.objects if o.type == 'ARMATURE')
src, dst = [], []
for b in arm.data.bones:
    if b.name in ue_rest:
        src.append(np.array(arm.matrix_world @ b.head_local)); dst.append(ue_rest[b.name])
src, dst = np.array(src), np.array(dst)
# similarity with reflection allowed (Umeyama)
ms, md = src.mean(0), dst.mean(0)
A, B = src - ms, dst - md
U, S, Vt = np.linalg.svd(B.T @ A)
Rm = U @ Vt
s = S.sum() / (A ** 2).sum()
t = md - s * Rm @ ms
err = np.linalg.norm((s * (Rm @ src.T)).T + t - dst, axis=1)
print('BELT49_FIT bones=%d scale=%.4f det=%.0f max_err_cm=%.4f' % (len(src), s, np.linalg.det(Rm), err.max()))
pos, cell, tris = [], [], []
for o in bpy.context.scene.objects:
    if o.type != 'MESH':
        continue
    names = [g.name for g in o.vertex_groups]
    deps = o.evaluated_get(bpy.context.evaluated_depsgraph_get())
    me = deps.to_mesh()
    base = len(pos)
    for poly in me.polygons:
        vs = list(poly.vertices)
        for k in range(1, len(vs) - 1):
            tris.append((base + vs[0], base + vs[k], base + vs[k + 1]))
    for v in me.vertices:
        p = np.array(o.matrix_world @ v.co)
        pos.append(s * Rm @ p + t)
        cell.append(names[0] if names else o.name)
    deps.to_mesh_clear()
np.savez(out, pos=np.array(pos), cell=np.array(cell), tris=np.array(tris), fit_err=err.max())
print('BELT49_SAVED', len(pos), sorted(set(cell)))
