"""Read existing campfire assets for native placement; no rendering or package writes."""
import json
from pathlib import Path
import unreal as u

root = Path(u.Paths.project_dir()) / 'SourceAssets/Campfire20261012'
root.mkdir(parents=True, exist_ok=True)
report = {'meshes': [], 'blueprint_components': []}
for style in ('Stylized', 'Polygonal', 'Dummy'):
    path = f'/Game/EasyBuildingSystem/Meshes/Props/{style}/SM_{style}_Campfire'
    mesh = u.load_asset(path)
    if not mesh:
        continue
    bounds = mesh.get_bounds()
    body = mesh.get_editor_property('body_setup')
    report['meshes'].append({
        'path': mesh.get_path_name(),
        'origin': [bounds.origin.x, bounds.origin.y, bounds.origin.z],
        'extent': [bounds.box_extent.x, bounds.box_extent.y, bounds.box_extent.z],
        'materials': [s.material_interface.get_path_name() if s.material_interface else None for s in mesh.static_materials],
        'collision': str(body.get_editor_property('collision_trace_flag')) if body else None,
    })
bp = u.load_class(None, '/Game/EasyBuildingSystem/Blueprints/BuildingObjects/Placeable/BP_EBS_Building_Campfire.BP_EBS_Building_Campfire_C')
if bp:
    default = u.get_default_object(bp)
    for comp in default.get_components_by_class(u.SceneComponent):
        report['blueprint_components'].append({'name': comp.get_name(), 'class': comp.get_class().get_name(),
            'location': str(comp.get_editor_property('relative_location')), 'scale': str(comp.get_editor_property('relative_scale3d'))})
for path in ['/Game/EasyBuildingSystem/Effects/PS_CampFire', '/Game/Props/RomanColumn20260915/NS_TorchFlame']:
    asset = u.load_asset(path)
    report[path] = asset.get_class().get_name() if asset else None
(root / 'asset-sources.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
print('CAMPFIRE_SOURCE_ASSETS ' + json.dumps(report, ensure_ascii=False))
