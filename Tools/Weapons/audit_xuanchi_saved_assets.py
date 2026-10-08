"""Read-only UE asset load/dependency check. Does not start PIE or save packages."""
import json
from pathlib import Path
import unreal

root = Path(unreal.Paths.project_dir())
output = root / 'Saved/XuanChiReview20261006'
catalog = json.loads((output / 'catalog-audit.json').read_text(encoding='utf-8'))
registry = unreal.AssetRegistryHelpers.get_asset_registry()
dependency_options = unreal.AssetRegistryDependencyOptions(
    include_soft_package_references=True, include_hard_package_references=True,
    include_searchable_names=False, include_soft_management_references=False,
    include_hard_management_references=False)
pending = list(catalog['asset_references'])
seen, records, failures = set(), [], []
while pending:
    path = pending.pop().split('.')[0]
    if path in seen:
        continue
    seen.add(path)
    if (root / 'Content' / path[6:]).is_dir():
        continue
    asset = unreal.load_asset(path)
    if asset is None:
        failures.append(path)
        continue
    record = {'asset': path, 'class': asset.get_class().get_name()}
    if isinstance(asset, unreal.MaterialInstanceConstant):
        parent = asset.get_editor_property('parent')
        record['parent'] = parent.get_path_name() if parent else None
        record['textures'] = {
            str(value.parameter_info.name): value.parameter_value.get_path_name() if value.parameter_value else None
            for value in asset.get_editor_property('texture_parameter_values')}
    if isinstance(asset, unreal.StaticMesh):
        record['material_slots'] = [
            slot.material_interface.get_path_name() if slot.material_interface else None
            for slot in asset.get_editor_property('static_materials')]
    records.append(record)
    for dependency in registry.get_dependencies(path, dependency_options):
        package = str(dependency)
        if package.startswith('/Game/') and package not in seen:
            pending.append(package)

result = {'complete': True, 'assets_loaded': len(records), 'load_failures': failures,
          'records': records, 'packages_saved': False, 'PIE_started': False,
          'visual_tested': False}
(output / 'saved-assets-audit.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print('XUANCHI_SAVED_ASSETS_AUDIT ' + json.dumps({k: v for k, v in result.items() if k != 'records'}))
if failures:
    raise RuntimeError('Saved assets failed to load: ' + ', '.join(failures))
