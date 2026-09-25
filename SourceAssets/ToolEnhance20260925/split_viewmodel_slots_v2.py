"""v2 viewmodel split: semantic Metal/Wood rule (same as world v2), replayed in rig space.

World-equivalent z for a tool face is (R^-1 @ polygon.center).z + grip_z, with R the
WPN_root rest matrix; the pickaxe uses the connected-component metallic/chroma rule and
the axe the per-face chroma/metallic rule, both gated by that z.  Slot order [Wood, Metal].
Outputs overwrite ToolEnhance20260925/Viewmodel/Export/SK_*.fbx and the split blends.

Blender --background --python split_viewmodel_slots_v2.py -- axe|pick
"""
import bpy
import bmesh
import json
import sys
import numpy as np
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
OUT = HERE / 'Viewmodel'
(OUT / 'Export').mkdir(parents=True, exist_ok=True)

AXE_INPUT = ROOT / 'SourceAssets/BattleAxeReplace20260919/Input/Meshy_AI_Weathered_Battle_Axe_0918025738_texture_fbx'
CONFIG = {
    'axe': {
        'blend': ROOT / 'SourceAssets/BattleAxeReplace20260919/Viewmodel/BattleAxe_SingleHand_Editable.blend',
        'tool': 'Harvest_Axe', 'grip_z': -0.26,
        'metallic': AXE_INPUT / 'Meshy_AI_Weathered_Battle_Axe_0918025738_texture_metallic.png',
        'basecolor': AXE_INPUT / 'Meshy_AI_Weathered_Battle_Axe_0918025738_texture.png',
        'channel': 0, 'rule': 'face', 'z_gate': 0.195, 'chroma_max': 0.20, 'metal_seed': 0.2,
        'fbx': OUT / 'Export/SK_Harvest_Axe.fbx',
        'out_blend': OUT / 'BattleAxe_SingleHand_Split.blend',
        'path_mode': None,
    },
    'pick': {
        'blend': ROOT / 'SourceAssets/RusticPickaxe20260919/RusticPickaxe_TwoHand_Editable.blend',
        'tool': 'Harvest_Pickaxe', 'grip_z': -0.26,
        'metallic': ROOT / 'SourceAssets/RusticPickaxe20260919/Textures/MetallicRoughness.jpg',
        'basecolor': ROOT / 'SourceAssets/RusticPickaxe20260919/Textures/BaseColor.jpg',
        'channel': 2, 'rule': 'component', 'z_gate': 0.33,
        'comp_metallic_min': 0.15, 'comp_chroma_max': 0.16,
        'fbx': OUT / 'Export/SK_RusticPickaxe.fbx',
        'out_blend': OUT / 'RusticPickaxe_TwoHand_Split.blend',
        'path_mode': 'STRIP',
    },
}

target = sys.argv[sys.argv.index('--') + 1]
cfg = CONFIG[target]


def load_raw(path):
    img = bpy.data.images.load(str(path), check_existing=False)
    img.colorspace_settings.name = 'Non-Color'
    w, h = int(img.size[0]), int(img.size[1])
    buf = np.empty(w * h * 4, dtype=np.float32)
    img.pixels.foreach_get(buf)
    return np.flipud(buf.reshape(h, w, 4)), w, h


def sample(buf, w, h, uv):
    u = np.clip(uv[:, 0], 0., 1.)
    v = np.clip(uv[:, 1], 0., 1.)
    x = np.minimum((u * (w - 1)).astype(np.int64), w - 1)
    y = np.minimum(((1.0 - v) * (h - 1)).astype(np.int64), h - 1)
    return buf[y, x, 0:3].astype(np.float64)


bpy.ops.wm.open_mainfile(filepath=str(cfg['blend']))
scene = bpy.context.scene
scene.frame_set(0)
tool = bpy.data.objects[cfg['tool']]
rig = tool.parent
if rig is None or rig.type != 'ARMATURE':
    raise SystemExit('tool %s is not parented to an armature' % cfg['tool'])
inverse = rig.data.bones['WPN_root'].matrix_local.inverted()

mbuf, mw, mh = load_raw(cfg['metallic'])
cbuf, cw, ch = load_raw(cfg['basecolor'])

mesh = tool.data
if len(mesh.materials) != 1:
    raise SystemExit('expected a single tool material, got %d' % len(mesh.materials))
uv = mesh.uv_layers.active.data
uvc = np.empty((len(mesh.polygons), 2), dtype=np.float64)
wz = np.empty(len(mesh.polygons), dtype=np.float64)
for p in mesh.polygons:
    acc = np.zeros(2)
    for li in p.loop_indices:
        acc += uv[li].uv
    uvc[p.index] = acc / max(1, len(p.loop_indices))
    wz[p.index] = (inverse @ p.center).z + cfg['grip_z']
metal_px = sample(mbuf, mw, mh, uvc)[:, cfg['channel']]
base_px = sample(cbuf, cw, ch, uvc)
chroma = base_px[:, 0] - base_px[:, 2]

if cfg['rule'] == 'face':
    mask = (wz >= cfg['z_gate']) & ((chroma < cfg['chroma_max']) | (metal_px > cfg['metal_seed']))
    detail = {}
else:
    bm = bmesh.new()
    bm.from_mesh(mesh)
    bm.faces.ensure_lookup_table()
    adj = [[] for _ in range(len(bm.faces))]
    for e in bm.edges:
        ls = e.link_faces
        for i in range(len(ls)):
            for j in range(i + 1, len(ls)):
                adj[ls[i].index].append(ls[j].index)
                adj[ls[j].index].append(ls[i].index)
    bm.free()
    seen = [-1] * len(mesh.polygons)
    cid = 0
    for i in range(len(mesh.polygons)):
        if seen[i] >= 0:
            continue
        stack = [i]
        seen[i] = cid
        while stack:
            cur = stack.pop()
            for nb in adj[cur]:
                if seen[nb] < 0:
                    seen[nb] = cid
                    stack.append(nb)
        cid += 1
    comp = np.array(seen)
    metal_comps = []
    detail = []
    for c in range(cid):
        m = comp == c
        if m.sum() < 4:
            continue
        mmean = float(metal_px[m].mean())
        cmean = float(chroma[m].mean())
        zmin = float(wz[m].min())
        is_metal = mmean >= cfg['comp_metallic_min'] and cmean <= cfg['comp_chroma_max'] and zmin >= cfg['z_gate']
        if is_metal:
            metal_comps.append(c)
        if zmin >= cfg['z_gate'] - 0.05:
            detail.append({'comp': c, 'faces': int(m.sum()), 'metallic': round(mmean, 4),
                           'chroma': round(cmean, 4), 'wzmin': round(zmin, 4), 'metal': bool(is_metal)})
    mask = np.isin(comp, metal_comps) if metal_comps else np.zeros(len(mesh.polygons), dtype=bool)

if mask.sum() == 0:
    raise SystemExit('empty metal mask for ' + target)

wood = mesh.materials[0]
wood.name = 'Wood'
leftover = bpy.data.materials.get('Metal')
if leftover and leftover.users == 0:
    bpy.data.materials.remove(leftover)
metal = bpy.data.materials.new('Metal')
mesh.materials.append(metal)
metal_faces = 0
for polygon in mesh.polygons:
    if mask[polygon.index]:
        polygon.material_index = 1
        metal_faces += 1
total = len(mesh.polygons)

arms = next(o for o in scene.objects if o.type == 'MESH' and o != tool)
rig.data.pose_position = 'REST'
bpy.ops.object.select_all(action='DESELECT')
for obj in (arms, tool, rig):
    obj.hide_set(False)
    obj.select_set(True)
bpy.context.view_layer.objects.active = rig
kwargs = dict(filepath=str(cfg['fbx']), use_selection=True,
              object_types={'ARMATURE', 'MESH'}, axis_forward='-Y', axis_up='Z',
              add_leaf_bones=False, bake_anim=False, mesh_smooth_type='FACE', use_tspace=True)
if cfg['path_mode']:
    kwargs['path_mode'] = cfg['path_mode']
bpy.ops.export_scene.fbx(**kwargs)
rig.data.pose_position = 'POSE'
bpy.ops.wm.save_as_mainfile(filepath=str(cfg['out_blend']))

report = {'target': target, 'rule': cfg['rule'], 'z_gate': cfg['z_gate'], 'faces': total,
          'metal_faces': metal_faces, 'metal_fraction': round(metal_faces / total, 4),
          'slots': [m.name for m in mesh.materials], 'fbx': str(cfg['fbx']),
          'blend': str(cfg['out_blend']), 'detail': detail}
(HERE / ('viewmodel-split-v2-%s.json' % target)).write_text(json.dumps(report, indent=2), encoding='utf-8')
print('VIEWMODEL_SPLIT_V2', target, metal_faces, '/', total, flush=True)
