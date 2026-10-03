"""Inspect only the Tengyun/factory blade root and its hilt interface."""
import bpy, bmesh, json
from pathlib import Path

P = Path(__file__).resolve().parent
T = P.parent
bpy.ops.wm.open_mainfile(filepath=str(T.parent/'SurfaceV2/TangDao_SurfaceV2_Editable.blend'))
report = {'factory_parts': [], 'cross_sections_cm': []}
for name in ['SM_TangDao_Blade_factory', 'SM_TangDao_Guard_factory']:
    obj = bpy.data.objects[name]
    coords = [obj.matrix_world @ v.co for v in obj.data.vertices]
    report['factory_parts'].append({'name': name,
        'min_cm': [min(p[i] for p in coords)*100 for i in range(3)],
        'max_cm': [max(p[i] for p in coords)*100 for i in range(3)],
        'materials': [m.name for m in obj.data.materials]})
source = bpy.data.objects['SM_TangDao_Blade_factory']
for z in [.01401, .0145, .016, .02, .03, .04, .06, .08, .14]:
    bm = bmesh.new()
    bm.from_mesh(source.data)
    cut = bmesh.ops.bisect_plane(bm, geom=list(bm.verts)+list(bm.edges)+list(bm.faces),
        dist=1e-8, plane_co=(0, 0, z), plane_no=(0, 0, 1), clear_outer=True)
    edges = [e for e in bm.edges if e.is_boundary and all(abs(v.co.z-z)<2e-6 for v in e.verts)]
    verts = list({v for e in edges for v in e.verts})
    report['cross_sections_cm'].append({'z_cm': z*100, 'edges': len(edges), 'verts': len(verts),
        'min_cm': [min(v.co[i] for v in verts)*100 for i in range(3)] if verts else [],
        'max_cm': [max(v.co[i] for v in verts)*100 for i in range(3)] if verts else []})
    bm.free()
bpy.ops.wm.open_mainfile(filepath=str(T/'TangDao_TengyunBlade_Editable.blend'))
obj = bpy.data.objects['SM_TangDao_Blade_tengyun_dragon_LOD0']
for index, mat in enumerate(obj.data.materials):
    faces = [f for f in obj.data.polygons if f.material_index == index]
    verts = {v for f in faces for v in f.vertices}
    report.setdefault('tengyun_material_regions', []).append({'slot': mat.name, 'faces': len(faces),
        'min_z_cm': min(obj.data.vertices[v].co.z for v in verts)*100,
        'max_z_cm': max(obj.data.vertices[v].co.z for v in verts)*100})
(P/'diagnosis-before.json').write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
print('TENGYUN_JOINT_DIAGNOSIS', json.dumps(report, ensure_ascii=False), flush=True)
