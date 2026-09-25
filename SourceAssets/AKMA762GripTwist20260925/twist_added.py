"""How much roll the aimed-up thumb adds relative to the round-1 pose.

The three skinned thumb segment centroids span a plane; its normal encodes the
roll of the thumb about its own axis.  Rotating round-1's normal by the same
minimal-arc swing that takes round-1's visible thumb direction to the new one and
comparing with the new normal gives the roll the pass actually introduced -
should be near zero, since the aim is a minimal-arc (roll-free) correction.
"""
import bpy, json, math
from pathlib import Path
from mathutils import Vector, Matrix, Quaternion

O = Path(__file__).parent; S = O.parent
PARTS = ['thumb_01_l', 'thumb_02_l', 'thumb_03_l']
FRAME = 148
FIT = json.loads((O / 'thumb_fit.json').read_text())
TGT = json.loads((O / 'thumb_target2.json').read_text())
CASES = {
    'AKM': S / 'RifleMagazineGrip20260922/IndexClearanceV4/AKM/standard/base/A_AKM_reload.blend',
    'A762': S / 'RifleMagazineGrip20260922/IndexClearanceV4/A762/standard/base/A_A762_reload.blend',
}
out = {}
for gun, path in CASES.items():
    bpy.ops.wm.open_mainfile(filepath=str(path), use_scripts=False)
    r = bpy.data.objects['SK_M4_Infima']
    arms = bpy.data.objects['SK_Manny_Arms_Export']
    a = r.animation_data.action
    r.animation_data.action = a; r.animation_data.action_slot = a.slots[0]
    sc = bpy.context.scene
    sc.frame_set(FRAME); bpy.context.view_layer.update()
    keep = {n: (lambda dd: (dd[0], dd[2]))(r.pose.bones[n].matrix_basis.decompose()) for n in PARTS}

    def cents():
        dg = bpy.context.evaluated_depsgraph_get()
        e = arms.evaluated_get(dg); me = e.to_mesh(); M = e.matrix_world
        groups = [g.name for g in arms.vertex_groups]
        acc = {p: [] for p in PARTS}
        for v in me.vertices:
            best, w = None, 0.0
            for g in v.groups:
                if g.weight > w:
                    best, w = groups[g.group], g.weight
            if best in acc:
                acc[best].append(M @ v.co)
        e.to_mesh_clear()
        return {p: sum(pts, Vector()) / len(pts) for p, pts in acc.items()}

    def set_thumb(root, c, d):
        for n, q in (('thumb_01_l', root),
                     ('thumb_02_l', Matrix.Rotation(math.radians(c), 4, 'Z').to_quaternion()),
                     ('thumb_03_l', Matrix.Rotation(math.radians(d), 4, 'Z').to_quaternion())):
            r.pose.bones[n].matrix_basis = Matrix.LocRotScale(keep[n][0], q, keep[n][1])
        bpy.context.view_layer.update()

    p1 = FIT[gun]['params']
    set_thumb(Matrix.Rotation(math.radians(p1['a_z']), 4, 'Z').to_quaternion() @
              Matrix.Rotation(math.radians(p1['b_x']), 4, 'X').to_quaternion(), p1['c_02'], p1['d_03'])
    c1 = cents()
    d1 = (c1['thumb_03_l'] - c1['thumb_01_l']).normalized()
    n1 = (c1['thumb_02_l'] - c1['thumb_01_l']).cross(c1['thumb_03_l'] - c1['thumb_01_l']).normalized()
    t = TGT[gun]
    set_thumb(Quaternion(t['root_quat_wxyz']), t['c_02'], t['d_03'])
    c2 = cents()
    d2 = (c2['thumb_03_l'] - c2['thumb_01_l']).normalized()
    n2 = (c2['thumb_02_l'] - c2['thumb_01_l']).cross(c2['thumb_03_l'] - c2['thumb_01_l']).normalized()
    swing = d1.rotation_difference(d2)
    moved = (swing.to_matrix() @ n1).normalized()
    added = math.degrees(math.acos(max(-1, min(1, moved.dot(n2)))))
    out[gun] = {'swing_deg': round(math.degrees(swing.angle), 2),
                'added_roll_deg': round(added, 2),
                'roll_note': 'angle between the swung round-1 thumb plane normal and the new one'}
    print('%s: visible swing %.2f deg, roll added about the thumb axis %.2f deg' % (gun, out[gun]['swing_deg'], added), flush=True)
(O / 'twist_added.json').write_text(json.dumps(out, indent=1))
print('TWIST_ADDED_OK', flush=True)
