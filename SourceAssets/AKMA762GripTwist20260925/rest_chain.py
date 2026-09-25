"""Rest geometry of the left thumb chain: per-segment directions, the chord, and
their relation to the magazine axis at the grip frame."""
import bpy, math, json
from pathlib import Path
from mathutils import Vector, Quaternion, Matrix

O = Path(__file__).parent; S = O.parent
PARTS = ['thumb_01_l', 'thumb_02_l', 'thumb_03_l']
CASES = {
    'AKM': S / 'RifleMagazineGrip20260922/IndexClearanceV4/AKM/standard/base/A_AKM_reload.blend',
    'A762': S / 'RifleMagazineGrip20260922/IndexClearanceV4/A762/standard/base/A_A762_reload.blend',
}
for gun, path in CASES.items():
    bpy.ops.wm.open_mainfile(filepath=str(path), use_scripts=False)
    r = bpy.data.objects['SK_M4_Infima']
    a = r.animation_data.action
    r.animation_data.action = a; r.animation_data.action_slot = a.slots[0]
    sc = bpy.context.scene
    sc.frame_set(148); bpy.context.view_layer.update()
    for n in PARTS:
        pb = r.pose.bones[n]
        loc, _, scale = pb.matrix_basis.decompose()
        pb.matrix_basis = Matrix.LocRotScale(loc, Quaternion(), scale)
    bpy.context.view_layer.update()
    P = {b.name: b.matrix.copy() for b in r.pose.bones}
    head = P['thumb_01_l'].translation
    segs = []
    for n in PARTS:
        d = (P[n].to_3x3() @ Vector((0, 1, 0))).normalized()
        segs.append(d)
    tip = P['thumb_03_l'] @ Vector((0, r.data.bones['thumb_03_l'].length, 0))
    ch = (tip - head).normalized()
    ang = lambda a, b: math.degrees(math.acos(max(-1, min(1, a.dot(b)))))
    print('%s rest chain:' % gun, flush=True)
    for i, n in enumerate(PARTS):
        print('   %s dir %s len %.1f mm  vs root %5.1f deg  vs chord %5.1f deg'
              % (n, [round(x, 3) for x in segs[i]], r.data.bones[n].length * 1000,
                 ang(segs[i], segs[0]), ang(segs[i], ch)), flush=True)
    print('   chord %s len %.1f mm  vs root %5.1f deg' % ([round(x, 3) for x in ch],
          (tip - head).length * 1000, ang(ch, segs[0])), flush=True)
    # where the mag axis sits relative to the rest root direction
    restb = r.data.bones['WPN_SOCKET_Magazine'].matrix_local
    D = r.matrix_world @ P['WPN_SOCKET_Magazine'] @ restb.inverted() @ r.matrix_world.inverted()
    mags = [o for o in sc.objects if o.type == 'MESH' and gun.upper() in o.name.upper() and 'MAG' in o.name.upper()]
    dg = bpy.context.evaluated_depsgraph_get()
    mv = []
    for o in mags:
        if any(m.type == 'ARMATURE' for m in o.modifiers):
            e = o.evaluated_get(dg); me = e.to_mesh(); M = e.matrix_world
            mv.extend(M @ v.co for v in me.vertices); e.to_mesh_clear()
        else:
            mv.extend(D @ (o.matrix_world @ v.co) for v in o.data.vertices)
    c = sum(mv, Vector()) / len(mv)
    xx = xy = xz = yy = yz = zz = 0.0
    for p in mv:
        d = p - c
        xx += d.x * d.x; xy += d.x * d.y; xz += d.x * d.z; yy += d.y * d.y; yz += d.y * d.z; zz += d.z * d.z
    M = Matrix(((xx, xy, xz), (xy, yy, yz), (xz, yz, zz)))
    v = Vector((M[0][0], M[1][0], M[2][0]))
    for i in (1, 2):
        w = Vector((M[0][i], M[1][i], M[2][i]))
        if w.length > v.length:
            v = w
    axis = v.normalized()
    if (P['WPN_root'].translation - c).dot(axis) < 0:
        axis = -axis
    Wa = r.matrix_world.to_3x3()
    axis = (Wa.inverted() @ (Wa @ axis)).normalized()
    rootw = Wa @ segs[0]
    axisw = Wa @ axis
    if axisw.z < 0:
        axisw = -axisw
    print('   mag axis %s  vs rest root %5.1f deg  vs rest chord %5.1f deg' %
          ([round(x, 3) for x in axis], ang(axis, segs[0]), ang(axis, ch)), flush=True)
print('REST_OK', flush=True)
