"""Print the rest head/tail of the thumb bones and the tip/base of the actual
thumb skin, so the visually meaningful thumb direction is unambiguous."""
import bpy, math
from pathlib import Path
from mathutils import Vector, Quaternion, Matrix

O = Path(__file__).parent; S = O.parent
PARTS = ['thumb_01_l', 'thumb_02_l', 'thumb_03_l']
path = S / 'RifleMagazineGrip20260922/IndexClearanceV4/AKM/standard/base/A_AKM_reload.blend'
bpy.ops.wm.open_mainfile(filepath=str(path), use_scripts=False)
r = bpy.data.objects['SK_M4_Infima']
arms = bpy.data.objects['SK_Manny_Arms_Export']
a = r.animation_data.action
r.animation_data.action = a; r.animation_data.action_slot = a.slots[0]
sc = bpy.context.scene
sc.frame_set(148); bpy.context.view_layer.update()


def report(tag):
    P = {b.name: b.matrix.copy() for b in r.pose.bones}
    print('--', tag, flush=True)
    for n in PARTS:
        h = P[n].translation
        t = P[n] @ Vector((0, r.data.bones[n].length, 0))
        print('   %s head %s tail %s  offset_to_next %s' % (
            n, [round(x * 1000, 1) for x in h], [round(x * 1000, 1) for x in t],
            [round(x * 1000, 1) for x in (P[PARTS[PARTS.index(n) + 1]].translation - t)] if n != PARTS[-1] else '-'), flush=True)
    # thumb skin extremes along the chain: nearest vertices to each bone head/tail
    dg = bpy.context.evaluated_depsgraph_get()
    e = arms.evaluated_get(dg); me = e.to_mesh(); M = e.matrix_world
    groups = [g.name for g in arms.vertex_groups]
    pts = []
    for v in me.vertices:
        best, w = None, 0.0
        for g in v.groups:
            if g.weight > w:
                best, w = groups[g.group], g.weight
        if best in PARTS:
            pts.append((best, M @ v.co))
    e.to_mesh_clear()
    for n in PARTS:
        sel = [p for b, p in pts if b == n]
        if not sel:
            continue
        c = sum(sel, Vector()) / len(sel)
        print('   %s skin verts %4d centroid %s' % (n, len(sel), [round(x * 1000, 1) for x in c]), flush=True)
    allp = [p for b, p in pts]
    c = sum(allp, Vector()) / len(allp)
    far = max(allp, key=lambda p: (p - c).length)
    print('   thumb skin centroid %s  extreme %s' % ([round(x * 1000, 1) for x in c],
                                                     [round(x * 1000, 1) for x in far]), flush=True)


for n in PARTS:
    pb = r.pose.bones[n]
    loc, _, scale = pb.matrix_basis.decompose()
    pb.matrix_basis = Matrix.LocRotScale(loc, Quaternion(), scale)
bpy.context.view_layer.update()
report('rest (identity thumb basis)')
for n in PARTS:
    pb = r.pose.bones[n]
    loc, _, scale = pb.matrix_basis.decompose()
    pb.matrix_basis = Matrix.LocRotScale(loc, Quaternion(), scale)
bpy.context.view_layer.update()
report('clip shipped thumb basis')
print('HEADS_OK', flush=True)
