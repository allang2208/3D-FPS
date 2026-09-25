"""List mesh objects skinned to the magazine socket bone (name, verts, size) so a
clean magazine body can be picked for axis measurement."""
import bpy
from pathlib import Path
from mathutils import Vector

O = Path(__file__).parent; S = O.parent
CASES = [
    ('AKM', S / 'RifleMagazineGrip20260922/IndexClearanceV4/AKM/standard/base/A_AKM_reload.blend'),
    ('A762', S / 'RifleMagazineGrip20260922/IndexClearanceV4/A762/standard/base/A_A762_reload.blend'),
    ('SVD', S / 'SVDThumbUp20260923/SVD_base_Editable.blend'),
]
for tag, path in CASES:
    bpy.ops.wm.open_mainfile(filepath=str(path), use_scripts=False)
    sc = bpy.context.scene
    mb = [b.name for b in bpy.data.objects['SK_M4_Infima'].pose.bones if 'Magazine' in b.name]
    print('== %s mag bones %s' % (tag, mb), flush=True)
    for o in sc.objects:
        if o.type != 'MESH':
            continue
        gs = [g.name for g in o.vertex_groups]
        hit = [g for g in gs if g in mb]
        if not hit and not any(k in o.name.lower() for k in ('mag', 'drum', 'ammo')):
            continue
        pts = [o.matrix_world @ v.co for v in o.data.vertices]
        if not pts:
            continue
        mn = Vector((min(p[i] for p in pts) for i in range(3)))
        mx = Vector((max(p[i] for p in pts) for i in range(3)))
        size = (mx - mn) * 1000
        print('   %-34s verts %5d  vgroups(mag) %-24s  size_mm [%6.1f %6.1f %6.1f]  centre [%7.1f %7.1f %7.1f]'
              % (o.name, len(pts), ','.join(hit) or '-', size.x, size.y, size.z,
                 ((mn + mx) / 2).x * 1000, ((mn + mx) / 2).y * 1000, ((mn + mx) / 2).z * 1000), flush=True)
print('PROBE_OK', flush=True)
