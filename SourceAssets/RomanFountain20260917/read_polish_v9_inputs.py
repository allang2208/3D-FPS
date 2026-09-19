"""Read current construction inputs needed by the scoped V9 authoring script."""
import json
from pathlib import Path
import unreal as u
root = '/Game/Props/RomanFountain20260917'
mesh = u.load_asset(root+'/SM_RomanFountain_20')
palette = u.load_asset('/Game/Building/Voxels/Rounded/DA_VoxelBuildPalette')
result = {'materials':[mesh.get_material(i).get_path_name() if mesh.get_material(i) else None for i in range(len(mesh.get_editor_property('static_materials')))]}
for entry in palette.get_editor_property('components'):
    if str(entry.get_editor_property('id')) == 'roman_fountain':
        result['palette'] = entry.export_text()
        surface = entry.get_editor_property('surface')
        result['surface'] = surface.get_path_name()
        if isinstance(surface, u.MaterialInstance):
            surface = surface.get_editor_property('parent')
        result['parent'] = surface.get_path_name()
        result['tangent_space_normal'] = surface.get_editor_property('tangent_space_normal')
        result['expressions'] = [{'type':e.get_class().get_name(), 'name':e.get_name()} for e in u.MaterialEditingLibrary.get_material_expressions(surface)]
result['vibe3d_available'] = hasattr(u, 'ModelingService')
out = Path(u.Paths.project_saved_dir())/'FountainPolishV9'
out.mkdir(parents=True, exist_ok=True)
(out/'authoring-inputs.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
print('FOUNTAIN_V9_INPUTS '+json.dumps(result))
