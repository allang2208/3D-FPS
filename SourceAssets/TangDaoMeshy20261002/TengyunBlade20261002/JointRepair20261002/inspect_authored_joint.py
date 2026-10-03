"""Diagnose the reported joint on the repaired authored mesh, without rendering."""
import bpy, bmesh, json
from pathlib import Path
P = Path(__file__).resolve().parent
T = P.parent
bpy.ops.wm.open_mainfile(filepath=str(T/'TangDao_TengyunBlade_Editable.blend'))
obj = bpy.data.objects['SM_TangDao_Blade_tengyun_dragon_LOD0']
bm = bmesh.new()
bm.from_mesh(obj.data)
report = {'material_slots': [m.name for m in obj.data.materials],
    'old_surface_faces': sum(1 for f in obj.data.polygons
        if obj.data.materials[f.material_index].name == 'M_TangDaoSurface'),
    'boundary_edges': sum(e.is_boundary for e in bm.edges),
    'non_manifold_edges': sum(not e.is_manifold for e in bm.edges),
    'min_z_cm': min(v.co.z for v in bm.verts)*100,
    'max_z_cm': max(v.co.z for v in bm.verts)*100,
    'uv_min_v': min(v.uv.y for v in obj.data.uv_layers[0].data),
    'uv_max_v': max(v.uv.y for v in obj.data.uv_layers[0].data),
    'scope': 'reported blade-to-guard residual geometry only', 'runtime_tested': False}
bm.free()
(P/'authored-joint.json').write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
print('TENGYUN_JOINT_AUTHORED', json.dumps(report, ensure_ascii=False), flush=True)
