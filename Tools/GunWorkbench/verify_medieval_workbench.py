"""Final read-back verification for the medieval workbench hand-off (read-only)."""
import json
from pathlib import Path
import unreal as u

OUT = Path('D:/FPS3D/FPSGAME/SourceAssets/GunWorkbenchMedieval20260928/Receipts/verify.json')
res = {}

palette = u.load_asset('/Game/Building/Voxels/Rounded/DA_VoxelBuildPalette')
entry = next(e for e in palette.get_editor_property('components')
             if str(e.get_editor_property('id')) == 'gun_workbench_table')
mesh = entry.get_editor_property('mesh')
res['palette_mesh'] = mesh.get_path_name()

b = mesh.get_bounds()
res['mesh_bounds_cm'] = {
    'origin': [round(b.origin.x, 1), round(b.origin.y, 1), round(b.origin.z, 1)],
    'extent': [round(b.box_extent.x, 1), round(b.box_extent.y, 1), round(b.box_extent.z, 1)],
}
res['slots'] = [
    {'slot': str(s.material_slot_name),
     'material': s.material_interface.get_path_name() if s.material_interface else None}
    for s in mesh.get_editor_property('static_materials')]
try:
    res['nanite'] = bool(mesh.get_editor_property('nanite_settings').is_enabled)
except Exception as ex:
    res['nanite'] = 'read_error:' + str(ex)[:60]

for name in ('M_GWLeather', 'M_GWClay'):
    mat = u.load_asset('/Game/Building/GunWorkbenchMedieval20260928/Materials/' + name)
    if not mat:
        res[name] = 'MISSING'
        continue
    used = None
    try:
        used = bool(mat.get_editor_property('bUsedWithNanite'))
    except Exception:
        pass
    res[name] = {'nanite_flag': used,
                 'shading_model': str(mat.get_editor_property('shading_model'))}

OUT.write_text(json.dumps(res, ensure_ascii=False, indent=2), encoding='utf-8')
print('VERIFY_WRITTEN ' + json.dumps(res, ensure_ascii=False))
