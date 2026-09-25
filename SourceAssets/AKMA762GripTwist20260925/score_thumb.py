"""Score thumb candidates by alignment with the magazine axis (thumb extends along
the magazine towards its feed end) and by how far the tip travels that way."""
import bpy, json, math, sys
from pathlib import Path
from mathutils import Vector, Matrix

O = Path(__file__).parent; S = O.parent
V4 = S / 'RifleMagazineGrip20260922/IndexClearanceV4'
CANDIDATES = [
    ('cur', None), ('z0x0', (0, 0, 6, 5)), ('zp20', (20, 0, 6, 5)), ('zn20', (-20, 0, 6, 5)),
    ('xp20', (0, 20, 6, 5)), ('xn20', (0, -20, 6, 5)), ('zp_xp', (20, 20, 6, 5)),
    ('zn_xp', (-20, 20, 6, 5)), ('zp_xn', (20, -20, 6, 5)),
]


def quats(par):
    a, b, c, d = par
    return {'thumb_01_l': Matrix.Rotation(math.radians(a), 4, 'Z').to_quaternion() @
                          Matrix.Rotation(math.radians(b), 4, 'X').to_quaternion(),
            'thumb_02_l': Matrix.Rotation(math.radians(c), 4, 'Z').to_quaternion(),
            'thumb_03_l': Matrix.Rotation(math.radians(d), 4, 'Z').to_quaternion()}


for gun, rel, hold in (('AKM', 'AKM/standard/base/A_AKM_reload.blend', 148),
                       ('A762', 'A762/standard/base/A_A762_reload.blend', 148)):
    print('==', gun, flush=True)
    for tag, par in CANDIDATES:
        bpy.ops.wm.open_mainfile(filepath=str(V4 / rel), use_scripts=False)
        r = bpy.data.objects['SK_M4_Infima']
        a = r.animation_data.action; r.animation_data.action = a; r.animation_data.action_slot = a.slots[0]
        sc = bpy.context.scene
        sc.frame_set(hold); bpy.context.view_layer.update()
        base = {b.name: b.matrix_basis.copy() for b in r.pose.bones}
        r.animation_data_clear()
        for n, m in base.items():
            r.pose.bones[n].matrix_basis = m
        bpy.context.view_layer.update()
        if par is not None:
            for n, q in quats(par).items():
                pb = r.pose.bones[n]
                loc, _, scale = pb.matrix_basis.decompose()
                pb.matrix_basis = Matrix.LocRotScale(loc, q, scale)
            bpy.context.view_layer.update()
        P = {b.name: b.matrix.copy() for b in r.pose.bones}
        W = r.matrix_world
        # magazine axis: the carrier bone's own Y direction, signed towards the feed end
        mag_y = (W.to_3x3() @ P['WPN_SOCKET_Magazine'].to_3x3() @ Vector((0, 1, 0))).normalized()
        if mag_y.z < 0:
            mag_y = -mag_y
        head = W @ P['thumb_01_l'].translation
        tip = W @ P['thumb_03_l'] @ Vector((0, r.data.bones['thumb_03_l'].length, 0))
        d = (tip - head).normalized()
        ang = math.degrees(math.acos(max(-1, min(1, d.dot(mag_y)))))
        reach = (tip - head).dot(mag_y) * 1000
        print('   %-6s thumb-vs-mag-axis %6.1f deg   tip travel along axis %6.1f mm   tip z %7.1f mm'
              % (tag, ang, reach, tip.z * 1000), flush=True)
print('SCORE_OK', flush=True)
