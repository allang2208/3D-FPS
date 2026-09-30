"""Dump a UE skeletal FBX into UE component-space centimetres for offline checks.

Read only. The Blender import frame is registered to the saved UE reference
skeleton (ClothFeed33 inputs.json) by a similarity fit of bone heads, so no
axis/unit convention is assumed.
Usage: blender -b --factory-startup --python dump_fbx.py -- <fbx> <out.npz>
"""
import bpy, sys, json
import numpy as np
from pathlib import Path

args = sys.argv[sys.argv.index('--') + 1:]
fbx, out = Path(args[0]), Path(args[1])
ROOT = Path('D:/FPS3D/FPSGAME/SourceAssets/LMG20120260927')
inputs = json.loads((ROOT / 'ClothFeed33' / 'inputs.json').read_text())['meshes']['201']
ue_rest = {n: np.array(v[:3]) for n, v in zip(inputs['names'], inputs['rest'])}

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=str(fbx), use_anim=False, ignore_leaf_bones=False,
                         automatic_bone_orientation=False)
arm = next(o for o in bpy.context.scene.objects if o.type == 'ARMATURE')
# UE FBX in Blender: metres with Y reflected. Verify on every shared bone.
Rm, scale, t = np.diag([100.0, -100.0, 100.0]), 1.0, np.zeros(3)
errs = [np.linalg.norm(Rm @ np.array(arm.matrix_world @ b.head_local) - ue_rest[b.name])
        for b in arm.data.bones if b.name in ue_rest]
print('DUMP_FIT bones=%d max_err_cm=%.4f' % (len(errs), max(errs)))

bone_names = [b.name for b in arm.data.bones]
bidx = {n: i for i, n in enumerate(bone_names)}
P, T, TM, BI, BW, mats = [], [], [], [], [], []
base = 0
for o in bpy.context.scene.objects:
    if o.type != 'MESH':
        continue
    me = o.data
    me.calc_loop_triangles()
    mw = np.array(o.matrix_world)
    co = np.array([v.co for v in me.vertices])
    co = (mw[:3, :3] @ co.T).T + mw[:3, 3]
    co = (scale * (Rm @ co.T)).T + t
    groups = {g.index: g.name for g in o.vertex_groups}
    bi = np.zeros((len(me.vertices), 8), np.int32)
    bw = np.zeros((len(me.vertices), 8), np.float32)
    for v in me.vertices:
        ws = sorted(((g.weight, groups[g.group]) for g in v.groups if g.weight > 0 and groups.get(g.group) in bidx), reverse=True)[:8]
        s = sum(w for w, _ in ws) or 1.0
        for k, (w, n) in enumerate(ws):
            bi[v.index, k] = bidx[n]
            bw[v.index, k] = w / s
    slot_names = [(m.name if m else '') for m in me.materials]
    local = {}
    for k, n in enumerate(slot_names):
        if n not in mats:
            mats.append(n)
        local[k] = mats.index(n)
    tris = np.array([lt.vertices[:] for lt in me.loop_triangles], np.int64)[:, ::-1]  # reflection flips winding
    tm = np.array([local.get(lt.material_index, 0) for lt in me.loop_triangles], np.int32)
    P.append(co.astype(np.float32)); T.append(tris + base); TM.append(tm); BI.append(bi); BW.append(bw)
    base += len(co)
    print('DUMP_MESH', o.name, len(co), len(tris))
np.savez_compressed(out, pos=np.concatenate(P), tris=np.concatenate(T), tri_mat=np.concatenate(TM),
                    bone_idx=np.concatenate(BI), bone_w=np.concatenate(BW),
                    bones=np.array(bone_names), mats=np.array(mats))
print('DUMP_SAVED', out, base, len(mats))
