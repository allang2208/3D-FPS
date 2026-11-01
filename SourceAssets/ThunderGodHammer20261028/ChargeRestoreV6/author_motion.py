"""Restore the uninterrupted V3 lift; join only the start of the V5 throw.

User chose the original charge plus a bounded entry adjustment. All throw
samples from 0.12 s onward and the complete weapon drive retain V5 data.
"""
import ast
import copy
import json
from pathlib import Path
import bpy
from mathutils import Matrix

P = Path(__file__).resolve().parent
R = P.parents[2]
OUT = P / 'Export'
OUT.mkdir(exist_ok=True)
FPS = 240
JOIN = .12
NAMES = ['A_ThunderHammer_ThrowCharge', 'A_ThunderHammer_ThrowRelease']

def read_source(path):
    bpy.ops.wm.open_mainfile(filepath=str(path))
    source_rig = bpy.data.objects['SK_RusticPickaxe_Rig']
    source_rig.data.pose_position = 'POSE'
    clips = {}
    for name in NAMES:
        action = bpy.data.actions[name]
        source_rig.animation_data.action = action
        source_rig.animation_data.action_slot = action.slots[0]
        rows = []
        for frame in range(round(action.frame_range[1]) + 1):
            bpy.context.scene.frame_set(frame)
            rows.append({b.name: b.matrix.copy() for b in source_rig.pose.bones})
        clips[name] = rows
    return clips

original = read_source(P.parent / 'ThrowRefineV3/ThunderHammer_ThrowRefineV3_Editable.blend')
current = read_source(P.parent / 'ThrowRefineV5/ThunderHammer_ThrowRefineV5_Editable.blend')
scene = bpy.context.scene
rig = bpy.data.objects['SK_RusticPickaxe_Rig']
rest = {b.name: b.matrix_local.copy() for b in rig.data.bones}
local_rest = {b.name: rest[b.parent.name].inverted() @ rest[b.name] if b.parent else rest[b.name]
              for b in rig.data.bones}
bpy.context.preferences.filepaths.save_version = 0

def ease(t):
    t = max(0., min(1., t))
    return t * t * t * (10. + t * (-15. + t * 6.))

def locals_of(pose):
    return {b.name: pose[b.parent.name].inverted() @ pose[b.name] if b.parent else pose[b.name]
            for b in rig.data.bones}

def join_pose(old, new, weight):
    # Blend native local chains, preserving bone lengths and quaternion shortest
    # paths. Do not blend the independent weapon drive or re-time either clip.
    a, b = locals_of(old), locals_of(new)
    out = {}
    for bone in rig.data.bones:
        n = bone.name
        if n.endswith(('_l', '_r')):
            pa, qa, sa = a[n].decompose()
            pb, qb, sb = b[n].decompose()
            local = Matrix.LocRotScale(pa.lerp(pb, weight), qa.slerp(qb, weight), sa.lerp(sb, weight))
        else:
            local = b[n]
        out[n] = out[bone.parent.name] @ local if bone.parent else local
    out['WPN_root'] = new['WPN_root'].copy()
    return out

charge = copy.deepcopy(original[NAMES[0]])
release = copy.deepcopy(current[NAMES[1]])
for frame in range(len(release)):
    t = frame / FPS
    if t >= JOIN:
        break
    release[frame] = join_pose(original[NAMES[1]][frame], current[NAMES[1]][frame], ease(t / JOIN))
# The full-charge frame is the exact arm pose at release entry.
for name in release[0]:
    if name.endswith(('_l', '_r')):
        release[0][name] = charge[-1][name].copy()

module = ast.parse((R / 'SourceAssets/SteelWarhammer20261014/SprintDragV1/author_sprint.py').read_text(encoding='utf-8'))
exec(compile(ast.Module(body=[n for n in module.body if isinstance(n, ast.FunctionDef)
                             and n.name in {'apply_pose', 'new_action', 'bake'}], type_ignores=[]), '<native_baker>', 'exec'))
for name, rows in zip(NAMES, [charge, release]):
    bake(name, rows, FPS)
rig.animation_data.action = bpy.data.actions[NAMES[0]]
rig.animation_data.action_slot = rig.animation_data.action.slots[0]
scene.frame_set(312)
bpy.ops.wm.save_as_mainfile(filepath=str(P / 'ThunderHammer_ChargeRestoreV6_Editable.blend'))
(P / 'motion.json').write_text(json.dumps({
    'revision': 'ChargeRestoreV6', 'fps': FPS, 'clips': NAMES,
    'keys': {n: len(rows) for n, rows in zip(NAMES, [charge, release])},
    'charge_source': 'ThrowRefineV3: original uninterrupted two-hand overhead lift',
    'release_source': 'ThrowRefineV5', 'release_entry_join_seconds': JOIN,
    'release_preserved_from_seconds': JOIN, 'release_event_seconds': .24,
    'weapon_drive': 'original per-frame tracks retained',
    'runtime_tested': False, 'preview_rendered': False
}, indent=2), encoding='utf-8')
print('THUNDER_CHARGE_RESTORE_V6_AUTHORED', flush=True)
