"""Author the closed-bolt continuous fill on the repaired native Super90 rig."""
import bpy, json, sys
from pathlib import Path
from mathutils import Quaternion

P = Path(r'D:/FPS3D/FPSGAME')
O = Path(__file__).parent
S = P / 'SourceAssets/BenelliM4Super9020261006'
bpy.ops.wm.open_mainfile(filepath=str(S / 'Super90_Gameplay_Editable.blend'))
rig = bpy.data.objects['SK_Super90']
scene = bpy.context.scene
scene.render.fps = 60

def sample(name):
    action = bpy.data.actions[name]
    rig.animation_data.action = action
    rig.animation_data.action_slot = action.slots[0]
    rows = []
    for frame in range(round(action.frame_range[0]), round(action.frame_range[1]) + 1):
        scene.frame_set(frame)
        bpy.context.view_layer.update()
        rows.append({b.name: b.matrix_basis.decompose() for b in rig.pose.bones})
    return rows

full = sample('A_Super90_reload_full')
single = sample('A_Super90_reload_one')
idle = sample('A_Super90_idle')[0]
# Seven original insertions at frames 44 + 50*n. At frame 360 the empty
# clip starts its bolt release; normal reload instead uses the single-feed
# return from frame 60. The support hand remains on its authored gun grip.
rows = full[:361]
for frame in range(1, len(single) - 60):
    weight = 1.0 - min(1.0, frame / 12.0)
    weight = weight * weight * (3.0 - 2.0 * weight)
    row = {}
    for name, (pos, rot, scale) in single[60 + frame].items():
        p0, q0, s0 = single[60][name]
        pa, qa, sa = full[360][name]
        offset = Quaternion((1, 0, 0, 0)).slerp(qa @ q0.inverted(), weight)
        row[name] = (pos + (pa - p0) * weight, offset @ rot, scale + (sa - s0) * weight)
    rows.append(row)
for row in rows:
    row['WPN_bolt'] = tuple(v.copy() for v in idle['WPN_bolt'])
# Maintain quaternion hemisphere continuity in the newly baked local tracks.
for index in range(1, len(rows)):
    for name in rows[index]:
        if rows[index - 1][name][1].dot(rows[index][name][1]) < 0:
            rows[index][name][1].negate()

sys.path.insert(0, str(P / 'SourceAssets/M1911RevolverInspect20260927'))
import author_support as support
support.DURATION = (len(rows) - 1) / 60
action = support.bake_action(rig, scene, 'A_Super90_reload_continuous', rows, list(range(len(rows))))
bpy.ops.object.select_all(action='DESELECT')
rig.hide_set(False)
rig.select_set(True)
bpy.context.view_layer.objects.active = rig
fbx = O / 'A_Super90_reload_continuous.fbx'
bpy.ops.export_scene.fbx(filepath=str(fbx), use_selection=True, object_types={'ARMATURE'},
    axis_forward='-Y', axis_up='Z', add_leaf_bones=False, bake_anim=True,
    bake_anim_use_all_actions=False, bake_anim_use_nla_strips=False, bake_anim_simplify_factor=0)
bpy.context.preferences.filepaths.save_version = 0
bpy.ops.wm.save_as_mainfile(filepath=str(O / 'Super90_ContinuousReload_Editable.blend'))
receipt = {'clips': {'reload_continuous': {'fbx': str(fbx), 'frames': len(rows),
    'duration': support.DURATION}}, 'source': str(S / 'Super90_Gameplay_Editable.blend'),
    'feed_contacts_frames': [44 + 50 * n for n in range(7)], 'tail_begin_frame': 360,
    'bolt_closed': True, 'mesh_bind_changed': False, 'runtime_tested': False}
(O / 'authoring_receipt.json').write_text(json.dumps(receipt, indent=2), encoding='utf-8')
print('SUPER90_CONTINUOUS_RELOAD_AUTHORED', len(rows), flush=True)
