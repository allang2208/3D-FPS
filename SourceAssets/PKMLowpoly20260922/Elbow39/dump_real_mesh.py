"""Dump the real V7 PKM arm mesh and the two rigs' rest data.

The V7 mesh is the surface written into the PKM base viewmodel, so it is the
arm the player actually sees.  The authoring blends (Wrist12 / Reload16) carry
the animation but bind a different arm object; this dump lets us pose the real
mesh with the real weights instead of rendering the authoring stand-in.
"""
import json
from pathlib import Path

import bpy
import numpy as np

ROOT = Path(r'D:\FPS3D\FPSGAME\SourceAssets\PKMLowpoly20260922')
OUT = ROOT / 'Elbow39'
OUT.mkdir(parents=True, exist_ok=True)

V7 = Path(r'D:\FPS3D\FPSGAME\SourceAssets\ModularOutfit20260925'
          r'\BarePalmV7\Editable\PKM_BareArmsV7.blend')
SRC = ROOT / 'Wrist12' / 'PKM_WristContact_Editable.blend'

CHAIN = ['clavicle_l', 'upperarm_l', 'upperarm_twist_01_l', 'upperarm_twist_02_l',
         'lowerarm_l', 'lowerarm_twist_01_l', 'lowerarm_twist_02_l', 'hand_l']


def bone_rest(rig):
    return {b.name: np.array(b.matrix_local) for b in rig.data.bones}


# ---- V7 mesh + native rig -------------------------------------------------
bpy.ops.wm.open_mainfile(filepath=str(V7))
rig = bpy.data.objects['PKM_NativeReference']
mesh_ob = bpy.data.objects['PKM_BareArmsV6']
me = mesh_ob.data
me.calc_loop_triangles()

groups = {g.index: g.name for g in mesh_ob.vertex_groups}
bones = [b.name for b in rig.data.bones]
bone_index = {n: i for i, n in enumerate(bones)}

verts = np.empty(len(me.vertices) * 3, dtype=np.float32)
me.vertices.foreach_get('co', verts)
verts = verts.reshape(-1, 3)

w_idx = np.full((len(me.vertices), 4), -1, dtype=np.int32)
w_val = np.zeros((len(me.vertices), 4), dtype=np.float32)
for v in me.vertices:
    entries = sorted(((g.weight, groups[g.group]) for g in v.groups), reverse=True)[:4]
    for k, (weight, name) in enumerate(entries):
        w_idx[v.index, k] = bone_index[name]
        w_val[v.index, k] = weight

tris = np.array([t.vertices for t in me.loop_triangles], dtype=np.int32)

rest_v7 = np.stack([np.array(rig.data.bones[n].matrix_local) for n in bones])
rest_v7_local = np.stack([
    np.array((rig.data.bones[n].parent.matrix_local.inverted()
              @ rig.data.bones[n].matrix_local)
             if rig.data.bones[n].parent else rig.data.bones[n].matrix_local)
    for n in bones])

np.savez_compressed(
    OUT / 'v7_mesh.npz',
    verts=verts, tris=tris, w_idx=w_idx, w_val=w_val,
    rest=rest_v7, rest_local=rest_v7_local,
    bones=np.array(bones, dtype=object),
    obj_world=np.array(mesh_ob.matrix_world),
    rig_world=np.array(rig.matrix_world),
    parents=np.array([(rig.data.bones[n].parent.name if rig.data.bones[n].parent else '')
                      for n in bones], dtype=object),
)

summary = {
    'v7_verts': int(len(verts)),
    'v7_tris': int(len(tris)),
    'v7_bones': len(bones),
    'mesh_obj_world_scale': [float(s) for s in mesh_ob.matrix_world.to_scale()],
    'v7_chain_rest_heads': {n: [float(x) for x in rest_v7[bone_index[n]][:3, 3]] for n in CHAIN},
}

# ---- authoring rig rest ---------------------------------------------------
bpy.ops.wm.open_mainfile(filepath=str(SRC))
rig2 = bpy.data.objects['PKM_Manny_Rig']
names2 = [b.name for b in rig2.data.bones]
rest2 = np.stack([np.array(rig2.data.bones[n].matrix_local) for n in names2])
np.savez_compressed(
    OUT / 'author_rig.npz',
    rest=rest2, bones=np.array(names2, dtype=object),
    rig_world=np.array(rig2.matrix_world),
)

summary['author_bones'] = len(names2)
(OUT / 'dump_summary.json').write_text(
    json.dumps(summary, indent=2, ensure_ascii=False), encoding='utf-8')
print('DUMP_DONE', flush=True)
print(json.dumps(summary, indent=2))