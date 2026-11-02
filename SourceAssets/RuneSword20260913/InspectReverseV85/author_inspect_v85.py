"""V85 Inspect: BV1hCJFzQEyR #10 绕手 (file 76.00-76.27 s) played in reverse = counter-clockwise, keyed per frame.

blender -b --factory-startup --python author_inspect_v85.py -- [--long-grip] [--no-export]
Source: the accepted WristLocked V4 idle of each grip; V7 surface for contacts (V9 differs by <= 3 mm).
Writes ExportV85[/LongGrip]/A_RuneSword_Inspect.fbx, authoring_v85[_long_grip].json and the editable Blend.
"""
import json
import sys
from pathlib import Path

import bpy
from mathutils import Matrix, Vector

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
import v85_keys as C  # noqa: E402
import v85_setup  # noqa: E402
from v85_frame import Solver  # noqa: E402
from v85_solve import solve  # noqa: E402

VARIANT = 'LongGrip' if '--long-grip' in sys.argv else 'Standard'
CLIP = 'A_RuneSword_Inspect'
OUT = HERE / 'ExportV85' / ('LongGrip' if VARIANT == 'LongGrip' else '')
BLEND = HERE / ('AzureRunesword_InspectReverseV85' + ('_LongGrip' if VARIANT == 'LongGrip' else '') + '.blend')

c = v85_setup.load(VARIANT)
S = Solver(c)
rig = c.rig
c.source_action.name = 'RETAINED_V4_Idle'
c.source_action.use_fake_user = True
action = c.source_action.copy()
action.name = CLIP
action.use_fake_user = True
rig.animation_data.action = action
rig.animation_data.action_slot = action.slots[0]
for layer in action.layers:
    for strip in layer.strips:
        for bag in strip.channelbags:
            for curve in list(bag.fcurves):
                bag.fcurves.remove(curve)

order, pending = [], set(c.names)
while pending:
    for n in list(pending):
        if c.parent[n] is None or c.parent[n] not in pending:
            order.append(n)
            pending.remove(n)

end_frame = int(round(C.END * C.TEMPO * C.FPS))
prev_q, rows = {}, []
for frame in range(end_frame + 1):
    t = frame / (C.FPS * C.TEMPO)  # R5: motion time; the clip plays it at 1 / TEMPO
    pose, row = solve(S, t)
    row['motion_s'], row['seconds'] = row['seconds'], round(frame / C.FPS, 4)
    world = {}
    for n in order:
        b = rig.pose.bones[n]
        b.rotation_mode = 'QUATERNION'
        pm = world.get(c.parent[n], Matrix.Identity(4))
        loc, q, sc = (c.local_rest[n].inverted() @ (pm.inverted() @ pose[n])).decompose()
        if n in prev_q and q.dot(prev_q[n]) < 0.0:
            q.negate()
        prev_q[n] = q.copy()
        b.location, b.rotation_quaternion, b.scale = loc, q, c.idle_local[n][2]
        world[n] = pm @ c.local_rest[n] @ Matrix.LocRotScale(loc, q, sc)
        for ch in ('location', 'rotation_quaternion', 'scale'):
            b.keyframe_insert(ch, frame=frame, group=n)
    rows.append(row)

for layer in action.layers:
    for strip in layer.strips:
        for bag in strip.channelbags:
            for curve in bag.fcurves:
                for key in curve.keyframe_points:
                    key.interpolation = 'LINEAR'
c.scene.render.fps, c.scene.render.fps_base = int(C.FPS), 1.0
c.scene.frame_start, c.scene.frame_end = 0, end_frame
c.scene.frame_set(0)
if '--no-export' not in sys.argv:
    OUT.mkdir(parents=True, exist_ok=True)
    bpy.ops.object.select_all(action='DESELECT')
    rig.hide_set(False)
    rig.select_set(True)
    bpy.context.view_layer.objects.active = rig
    bpy.ops.export_scene.fbx(
        filepath=str(OUT / (CLIP + '.fbx')), use_selection=True, object_types={'ARMATURE'},
        axis_forward='-Y', axis_up='Z', add_leaf_bones=False, bake_anim=True,
        bake_anim_use_all_actions=False, bake_anim_use_nla_strips=False, bake_anim_simplify_factor=0)

live = [r for r in rows if not r.get('idle_hold')]
end_err = max((world[n].translation - c.idle[n].translation).length for n in ('hand_r', 'hand_l', 'WPN_root'))
report = {
    'revision': 'InspectReverseV85', 'variant': VARIANT, 'idle_source': str(c.source),
    'reference': 'BV1hCJFzQEyR #10 绕手, file 76.00-76.30 s, frames played in reverse (counter-clockwise)',
    'seconds': round(C.END * C.TEMPO, 4), 'fps': C.FPS, 'tempo': C.TEMPO,
    'spin_window_s': [round(C.SPIN_START * C.TEMPO, 4), round(C.SPIN_END * C.TEMPO, 4)],
    'spin_axis': [round(v, 4) for v in c.spin_axis], 'roll_inplane_deg': c.roll_inplane_deg,
    'contacts': {k: {kk: (round(vv, 5) if isinstance(vv, float) else (list(vv) if isinstance(vv, Vector) else vv))
                     for kk, vv in v.items()} for k, v in c.contacts.items()},
    'min_tip_depth_m': min(r['tip_depth_m'] for r in live),
    'min_blade_in_view_depth_m': min([r['blade_in_view_min_depth_m'] for r in live
                                      if r['blade_in_view_min_depth_m'] is not None] or [None]),
    'max_wrist_bend_r_deg': max(r['wrist_bend_r_deg'] for r in live),
    'max_wrist_trim_r_deg': max(r['wrist_trim_r_deg'] for r in live),
    'max_abs_elbow_axial_r_deg': max(abs(r['elbow_axial_r_deg']) for r in live),
    'hand_roll_v9_r_range_deg': [min(r['hand_roll_v9_r_deg'] for r in live), max(r['hand_roll_v9_r_deg'] for r in live)],
    'max_reach_clamp_m': max(r['reach_clamp_m'] for r in live),
    'max_hilt_in_hand_free_mm': max([r['clear_hand']['hilt_max_mm'] for r in live if r['grip'] < 0.999] or [0.0]),
    'keys': [dict(k, t=round(k['t'] * C.TEMPO, 4)) for k in C.KEYS],  # clip time
    'idle_hilt_in_hand_mm': next(r['clear_hand']['hilt_max_mm'] for r in live if r['grip'] >= 0.999),
    'max_guard_in_hand_mm': max(r['clear_hand']['guard_max_mm'] for r in live),
    'max_sword_in_forearm_mm': max(max(r['clear_forearm']['hilt_max_mm'], r['clear_forearm']['guard_max_mm']) for r in live),
    'max_shoulder_r_delta_m': max(r['shoulder_r_delta_m'] for r in live),
    'end_translation_error_m': round(end_err, 6),
    'twist_rule': 'V9: lowerarm_twist_01 100 %, lowerarm_twist_02 50 % of hand roll vs lowerarm and bind',
    'testing': 'Authoring metrics only; no game or editor test. User tests.',
    'samples': rows,
}
(HERE / ('authoring_v85' + ('_long_grip' if VARIANT == 'LongGrip' else '') + '.json')).write_text(
    json.dumps(report, indent=1, ensure_ascii=False), encoding='utf-8')
if '--no-export' not in sys.argv:
    bpy.ops.file.pack_all()
    bpy.ops.wm.save_as_mainfile(filepath=str(BLEND))
else:
    (HERE / 'Work').mkdir(exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(HERE / 'Work' / ('preview_%s.blend' % VARIANT)))
print('INSPECT_REVERSE_V85_AUTHORED', VARIANT, end_frame, {k: v for k, v in report.items() if k not in ('samples', 'contacts')})
