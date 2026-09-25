"""Search the thumb root direction for the highest, straightest extension that
still lies alongside the magazine (not splayed away from it)."""
import bpy, json, math, sys
from pathlib import Path
from mathutils import Vector, Matrix

O = Path(__file__).parent; S = O.parent
V4 = S / 'RifleMagazineGrip20260922/IndexClearanceV4'
CASES = (('AKM', 'AKM/standard/base/A_AKM_reload.blend'), ('A762', 'A762/standard/base/A_A762_reload.blend'))
FLEX = (8, 6)


def quats(a, b, c, d):
    return {'thumb_01_l': Matrix.Rotation(math.radians(a), 4, 'Z').to_quaternion() @
                          Matrix.Rotation(math.radians(b), 4, 'X').to_quaternion(),
            'thumb_02_l': Matrix.Rotation(math.radians(c), 4, 'Z').to_quaternion(),
            'thumb_03_l': Matrix.Rotation(math.radians(d), 4, 'Z').to_quaternion()}


for gun, rel in CASES:
    bpy.ops.wm.open_mainfile(filepath=str(V4 / rel), use_scripts=False)
    r = bpy.data.objects['SK_M4_Infima']
    a = r.animation_data.action; r.animation_data.action = a; r.animation_data.action_slot = a.slots[0]
    sc = bpy.context.scene
    sc.frame_set(148); bpy.context.view_layer.update()
    base = {b.name: b.matrix_basis.copy() for b in r.pose.bones}
    r.animation_data_clear()
    for n, m in base.items():
        r.pose.bones[n].matrix_basis = m
    bpy.context.view_layer.update()
    W = r.matrix_world
    mag_y = (W.to_3x3() @ r.pose.bones['WPN_SOCKET_Magazine'].matrix.to_3x3() @ Vector((0, 1, 0))).normalized()
    if mag_y.z < 0:
        mag_y = -mag_y
    rest_tip = None
    rows = []
    for a_ in range(-40, 61, 10):
        for b_ in range(-40, 61, 10):
            for n, q in quats(a_, b_, FLEX[0], FLEX[1]).items():
                pb = r.pose.bones[n]
                loc, _, scale = pb.matrix_basis.decompose()
                pb.matrix_basis = Matrix.LocRotScale(loc, q, scale)
            bpy.context.view_layer.update()
            P = {b.name: b.matrix.copy() for b in r.pose.bones}
            head = W @ P['thumb_01_l'].translation
            tip = W @ P['thumb_03_l'] @ Vector((0, r.data.bones['thumb_03_l'].length, 0))
            d = (tip - head).normalized()
            ang = math.degrees(math.acos(max(-1, min(1, d.dot(mag_y)))))
            rows.append({'a': a_, 'b': b_, 'tip_z_mm': round(tip.z * 1000, 1), 'ang': round(ang, 1),
                         'along_mm': round((tip - head).dot(mag_y) * 1000, 1),
                         'tip_mm': [round(x * 1000, 1) for x in tip]})
            for n in ('thumb_01_l', 'thumb_02_l', 'thumb_03_l'):
                pb = r.pose.bones[n]
                loc, _, scale = pb.matrix_basis.decompose()
                pb.matrix_basis = Matrix.LocRotScale(loc, base[n].to_quaternion(), scale)
            bpy.context.view_layer.update()
    rows.sort(key=lambda x: -x['tip_z_mm'])
    ok = [x for x in rows if x['ang'] <= 80]
    print('==', gun, 'top by tip height (angle to mag axis <= 80 deg):', flush=True)
    for x in ok[:8]:
        print('   a=%4d b=%4d  tip_z %8.1f mm  angle %5.1f  along-mag %6.1f mm' %
              (x['a'], x['b'], x['tip_z_mm'], x['ang'], x['along_mm']), flush=True)
    print('   (unconstrained best tip_z: %s)' % [{k: x[k] for k in ('a', 'b', 'tip_z_mm', 'ang')} for x in rows[:3]], flush=True)
print('SEARCH_OK', flush=True)
