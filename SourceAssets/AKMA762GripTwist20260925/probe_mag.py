"""Find where the magazine actually travels in the AKM / A762 reload clips, and
report the magazine's long axis at the hold frame."""
import bpy, json, sys
from pathlib import Path
from mathutils import Vector

O = Path(__file__).parent; S = O.parent
V4 = S / 'RifleMagazineGrip20260922/IndexClearanceV4'
CASES = {
    'AKM': V4 / 'AKM/standard/base/A_AKM_reload.blend',
    'A762': V4 / 'A762/standard/base/A_A762_reload.blend',
}
for gun, path in CASES.items():
    bpy.ops.wm.open_mainfile(filepath=str(path), use_scripts=False)
    r = bpy.data.objects['SK_M4_Infima']
    a = r.animation_data.action; r.animation_data.action = a; r.animation_data.action_slot = a.slots[0]
    sc = bpy.context.scene
    print('==', gun, a.name, 'range', list(a.frame_range), flush=True)
    prev = None
    moves = []
    for f in range(0, int(a.frame_range[1]) + 1, 8):
        sc.frame_set(f); bpy.context.view_layer.update()
        p = r.matrix_world @ r.pose.bones['WPN_SOCKET_Magazine'].matrix.translation
        if prev is not None:
            moves.append((f, round((p - prev).length * 1000, 1)))
        prev = p
    big = [m for m in moves if m[1] > 2.0]
    print('   frames with >2 mm/frame travel:', big[:20], flush=True)
    # long axis of the magazine at the hold frame
    hold = 148
    sc.frame_set(hold); bpy.context.view_layer.update()
    pts = []
    for o in sc.objects:
        if o.type == 'MESH' and ('Magazine' in o.name or 'magazine' in o.name):
            pts.extend(o.matrix_world @ v.co for v in o.data.vertices)
    if pts:
        c = sum(pts, Vector()) / len(pts)
        cov = [[0.0] * 3 for _ in range(3)]
        for p in pts:
            d = p - c
            for i in range(3):
                for j in range(3):
                    cov[i][j] += d[i] * d[j]
        # power iteration for the dominant axis
        v = Vector((0.3, 0.4, 0.8))
        for _ in range(300):
            w = Vector((sum(cov[i][j] * v[j] for j in range(3)) for i in range(3)))
            v = w.normalized()
        print('   mag meshes', len(pts), 'centre mm', [round(x * 1000, 1) for x in c],
              'long axis', [round(x, 3) for x in v], flush=True)
        # travel within 148..260
        p0 = None
        for f in (hold, 170, 190, 210, 230, 250):
            sc.frame_set(f); bpy.context.view_layer.update()
            q = r.matrix_world @ r.pose.bones['WPN_SOCKET_Magazine'].matrix.translation
            if p0 is None:
                p0 = q
            print('      f%-4d socket mm %s  delta %s' % (f, [round(x * 1000, 1) for x in q],
                                                          [round(x * 1000, 1) for x in (q - p0)]), flush=True)
print('PROBE_OK', flush=True)
