"""Per-bone twist (about the bone's own axis) versus swing, for the shipped V4
AKM / A762 grip and the accepted SVD / M4 references."""
import bpy, json, math, sys
from pathlib import Path
from mathutils import Vector, Quaternion

O = Path(__file__).parent; S = O.parent
FINGERS = ['thumb', 'index', 'middle', 'ring', 'pinky']
BONES = [f'{d}_{k}_l' for d in FINGERS for k in ('01', '02', '03')]


def split(delta):
    q = delta.to_quaternion(); q.normalize()
    a = Vector((0.0, 1.0, 0.0))
    p = a * Vector((q.x, q.y, q.z)).dot(a)
    if p.length < 1e-12:
        return 0.0, math.degrees(q.angle)
    tw = math.degrees(2.0 * math.atan2(p.length, q.w))
    if p.dot(a) < 0:
        tw = -tw
    swing = q @ Quaternion(a, math.radians(tw)).inverted()
    return tw, math.degrees(swing.angle)


def run(label, path, action, f):
    bpy.ops.wm.open_mainfile(filepath=str(path), use_scripts=False)
    rig = bpy.data.objects['SK_M4_Infima']
    a = rig.animation_data.action if action is None else bpy.data.actions[action]
    rig.animation_data.action = a; rig.animation_data.action_slot = a.slots[0]
    rest = {b.name: b.matrix_local.copy() for b in rig.data.bones}
    parents = {b.name: (b.parent.name if b.parent else None) for b in rig.data.bones}
    bpy.context.scene.frame_set(int(f), subframe=f % 1)
    bpy.context.view_layer.update()
    pose = {b.name: b.matrix.copy() for b in rig.pose.bones}
    out = {}
    for n in BONES + ['hand_l']:
        p = parents[n]
        rr = rest[p].inverted() @ rest[n] if p else rest[n]
        pr = pose[p].inverted() @ pose[n] if p else pose[n]
        tw, sw = split(rr.inverted() @ pr)
        out[n] = [round(tw, 1), round(sw, 1)]
    print('%-8s f%-4s %s' % (label, f, ' '.join('%s %+.0f/%.0f' % (n.replace('_l', ''), v[0], v[1])
                                                for n, v in out.items())), flush=True)
    return out


V4 = S / 'RifleMagazineGrip20260922/IndexClearanceV4'
CASES = [
    ('AKM', V4 / 'AKM/standard/base/A_AKM_reload.blend', None, 148),
    ('A762', V4 / 'A762/standard/base/A_A762_reload.blend', None, 148),
    ('SVD', S / 'SVDThumbUp20260923/SVD_base_Editable.blend', 'A_SVD_reload', 148),
    ('M4', S / 'ExtMagContact20260919/A_M4_ExtContact_reload.blend', None, 76),
]
res = {}
for tag, p, a, f in CASES:
    res[tag] = run(tag, p, a, f)
(O / 'twist_split.json').write_text(json.dumps(res, indent=1))
print('SPLIT_OK', flush=True)
