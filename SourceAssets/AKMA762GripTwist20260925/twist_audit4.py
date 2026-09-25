"""Twist audit v4, on the clips that actually ship (IndexClearanceV4 outputs).

Reports per sampled frame: the angle each left-hand/finger bone deviates from its
rest local orientation, the wrist bend and the roll of the hand about the fore arm
axis; the accepted SVD and M4 grips are measured the same way for reference.
"""
import bpy, json, math, sys
from pathlib import Path
from mathutils import Vector, Quaternion

O = Path(__file__).parent; S = O.parent
GROUPS = {
    'thumb': ['thumb_01_l', 'thumb_02_l', 'thumb_03_l'],
    'index': ['index_01_l', 'index_02_l', 'index_03_l'],
    'middle': ['middle_01_l', 'middle_02_l', 'middle_03_l'],
    'ring': ['ring_01_l', 'ring_02_l', 'ring_03_l'],
    'pinky': ['pinky_01_l', 'pinky_02_l', 'pinky_03_l'],
}
FINGERS = [n for v in GROUPS.values() for n in v]


def signed_roll(axis, ref, cur):
    ref = ref - axis * ref.dot(axis)
    cur = cur - axis * cur.dot(axis)
    if ref.length < 1e-9 or cur.length < 1e-9:
        return 0.0
    ref.normalize(); cur.normalize()
    ang = math.degrees(ref.angle(cur))
    return -ang if ref.cross(cur).dot(axis) < 0 else ang


def run(label, path, action, frames):
    bpy.ops.wm.open_mainfile(filepath=str(path), use_scripts=False)
    rig = bpy.data.objects['SK_M4_Infima']
    a = rig.animation_data.action if action is None else bpy.data.actions[action]
    rig.animation_data.action = a; rig.animation_data.action_slot = a.slots[0]
    rest = {b.name: b.matrix_local.copy() for b in rig.data.bones}
    parents = {b.name: (b.parent.name if b.parent else None) for b in rig.data.bones}
    out = {'action': a.name, 'frames': {}}
    for f in frames:
        bpy.context.scene.frame_set(int(f), subframe=f % 1)
        bpy.context.view_layer.update()
        pose = {b.name: b.matrix.copy() for b in rig.pose.bones}
        rec = {'angles': {}, 'twist': {}}
        for n in FINGERS + ['hand_l', 'lowerarm_l', 'upperarm_l']:
            if n not in pose:
                continue
            p = parents[n]
            rr = rest[p].inverted() @ rest[n] if p else rest[n]
            pr = pose[p].inverted() @ pose[n] if p else pose[n]
            q = (rr.inverted() @ pr).to_quaternion()
            rec['angles'][n] = round(math.degrees(q.angle), 2)
        def seg(ctx, tip):
            return (pose[tip].translation - pose[ctx].translation).normalized()
        fa_r = (rest['hand_l'].translation - rest['lowerarm_l'].translation).normalized()
        fa_p = seg('lowerarm_l', 'hand_l')
        rec['twist']['grip_roll'] = round(signed_roll(fa_r, rest['pinky_01_l'].translation - rest['index_01_l'].translation,
                                                      fa_p.rotation_difference(fa_r) @ (pose['pinky_01_l'].translation - pose['index_01_l'].translation)), 2)
        hr = (rest['middle_01_l'].translation - rest['hand_l'].translation).normalized()
        hp = seg('hand_l', 'middle_01_l')
        rec['twist']['wrist_bend_rest'] = round(math.degrees(hr.angle(fa_r)), 2)
        rec['twist']['wrist_bend_pose'] = round(math.degrees(hp.angle(fa_p)), 2)
        out['frames'][str(f)] = rec
    return out


V4 = S / 'RifleMagazineGrip20260922/IndexClearanceV4'
CASES = [
    ('AKM_std', V4 / 'AKM/standard/base/A_AKM_reload.blend', None, [100, 148, 200]),
    ('AKM_ext', V4 / 'AKM/extended/base/A_AKM_ExtContact_reload.blend', None, [100, 148, 200]),
    ('A762', V4 / 'A762/standard/base/A_A762_reload.blend', None, [100, 148, 200]),
    ('SVD_ok', S / 'SVDThumbUp20260923/SVD_base_Editable.blend', 'A_SVD_reload', [100, 148, 200]),
    ('M4_ok', S / 'ExtMagContact20260919/A_M4_ExtContact_reload.blend', None, [61, 76, 95]),
]
report = {}
for label, path, act, frames in CASES:
    if not path.exists():
        print('MISSING', label, path, flush=True); continue
    report[label] = run(label, path, act, frames)
    for f, rec in report[label]['frames'].items():
        a = rec['angles']; t = rec['twist']
        print('%-8s f%-4s wrist %5.1f->%5.1f (delta %5.1f)  roll %7.2f | thumb %s | index %s | middle %s | ring %s | pinky %s'
              % (label, f, t['wrist_bend_rest'], t['wrist_bend_pose'], t['wrist_bend_pose'] - t['wrist_bend_rest'],
                 t['grip_roll'],
                 '/'.join('%.0f' % a[n] for n in GROUPS['thumb']),
                 '/'.join('%.0f' % a[n] for n in GROUPS['index']),
                 '/'.join('%.0f' % a[n] for n in GROUPS['middle']),
                 '/'.join('%.0f' % a[n] for n in GROUPS['ring']),
                 '/'.join('%.0f' % a[n] for n in GROUPS['pinky'])), flush=True)
(O / 'twist_audit4.json').write_text(json.dumps(report, indent=1))
print('TWIST4_OK', flush=True)
