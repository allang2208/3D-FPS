"""Compare the AKM magazine proxy with the gun's own magazine geometry."""
import bpy, json
from pathlib import Path
from mathutils import Vector

O = Path(__file__).parent; S = O.parent
CASES = [
    ('AKM', S / 'RifleMagazineGrip20260922/IndexClearanceV4/AKM/standard/base/A_AKM_reload.blend'),
    ('AKM_ext', S / 'RifleMagazineGrip20260922/IndexClearanceV4/AKM/extended/base/A_AKM_ExtContact_reload.blend'),
    ('A762', S / 'RifleMagazineGrip20260922/IndexClearanceV4/A762/standard/base/A_A762_reload.blend'),
]


def box(pts):
    mn = Vector((min(p[i] for p in pts) for i in range(3)))
    mx = Vector((max(p[i] for p in pts) for i in range(3)))
    return [round((mx[i] - mn[i]) * 1000, 1) for i in range(3)], [round(((mn[i] + mx[i]) / 2) * 1000, 1) for i in range(3)]


for tag, path in CASES:
    bpy.ops.wm.open_mainfile(filepath=str(path), use_scripts=False)
    r = bpy.data.objects['SK_M4_Infima']
    sc = bpy.context.scene
    sc.frame_set(148); bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get()
    print('==', tag, flush=True)
    for o in sc.objects:
        if o.type != 'MESH':
            continue
        if not (any(g.name == 'WPN_SOCKET_Magazine' for g in o.vertex_groups)
                or ('MAG' in o.name.upper()) or ('DRUM' in o.name.upper())):
            continue
        e = o.evaluated_get(dg); me = e.to_mesh(); M = e.matrix_world
        groups = [g.name for g in o.vertex_groups]
        allp, magp = [], []
        for v in me.vertices:
            p = M @ v.co
            allp.append(p)
            for g in v.groups:
                if groups[g.group] == 'WPN_SOCKET_Magazine' and g.weight > 0.5:
                    magp.append(p); break
        if allp:
            sz, c = box(allp)
            print('   %-32s all verts %5d size %s centre %s' % (o.name, len(allp), sz, c), flush=True)
        if magp:
            sz, c = box(magp)
            print('   %-32s MAG-weighted %5d size %s centre %s' % ('', len(magp), sz, c), flush=True)
        e.to_mesh_clear()
print('PROBE3_OK', flush=True)
