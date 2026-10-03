"""Read only the saved blade shape involved in the user's distortion report."""
import bpy, bmesh, json
from pathlib import Path
P = Path(__file__).resolve().parent
T = P.parent
bpy.ops.wm.open_mainfile(filepath=str(T/'TangDao_TengyunBlade_Editable.blend'))
obj = bpy.data.objects['SM_TangDao_Blade_tengyun_dragon_LOD0']
mesh = obj.data
bm = bmesh.new()
bm.from_mesh(mesh)
root = [v.co for v in mesh.vertices if v.co.z < .14]
flat_root_loops = [i for face in mesh.polygons
    if all(.016 < mesh.vertices[v].co.z < .14
        and abs(abs(mesh.vertices[v].co.y)-.0035) < 1e-8 for v in face.vertices)
    for i in face.loop_indices]
normals = mesh.corner_normals
report = {'revision':'TangDaoTengyunPlanarSolidV4_20261002',
    'root_total_thickness_mm': (max(v.y for v in root)-min(v.y for v in root))*1000,
    'root_broad_plane_normal_deviation': max(
        (abs(normals[i].vector.x)+abs(normals[i].vector.z) for i in flat_root_loops),default=0),
    'boundary_edges':sum(e.is_boundary for e in bm.edges),
    'non_manifold_edges':sum(not e.is_manifold for e in bm.edges),
    'material_slots':[m.name for m in mesh.materials],
    'min_z_cm':min(v.co.z for v in mesh.vertices)*100,
    'max_z_cm':max(v.co.z for v in mesh.vertices)*100,
    'scope':'saved source geometry for the reported warp and uneven root',
    'runtime_tested':False,'rendered':False}
bm.free()
(P/'authored-geometry.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('TENGYUN_PLANAR_SAVED_SHAPE',json.dumps(report,ensure_ascii=False),flush=True)
