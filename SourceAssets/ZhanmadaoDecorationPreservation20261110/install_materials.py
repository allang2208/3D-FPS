"""Save the seven affected Zhanmadao surfaces and check their material wiring."""
import json
import runpy
import shutil
from pathlib import Path
import unreal as u

P = Path(__file__).resolve().parent
ROOT = P.parents[1]
L = u.MaterialEditingLibrary
E = u.EditorAssetLibrary
recipe = runpy.run_path(str(P / 'decoration_material.py'))
catalog = json.loads((ROOT / 'Content/ColdSteelData/zhanmadao-modules.json').read_text(encoding='utf-8-sig'))
paths = sorted({path for part in catalog['slots']['blade_1'].values() for path in part.get('materials', {}).values()
                if path.rsplit('.', 1)[-1] in recipe['PROFILES']})
if len(paths) != len(recipe['PROFILES']):
    raise RuntimeError('Live blade catalog differs from the inspected seven surfaces')
if Path(u.Paths.project_dir()).resolve() != ROOT:
    raise RuntimeError('Use the active FPSGAME host')
if u.EditorLevelLibrary.get_pie_worlds(False):
    raise RuntimeError('PIE is running; preserve the current session')
packages = {path.split('.')[0] for path in paths}
if any(p.get_path_name() in packages for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()):
    raise RuntimeError('Preserve unsaved target material')
receipt = {'revision': recipe['REVISION'], 'materials': [], 'game_tested': False}
for path in paths:
    disk = ROOT / 'Content' / (path.split('.')[0].removeprefix('/Game/') + '.uasset')
    backup = P / 'BeforeAssets' / disk.relative_to(ROOT / 'Content')
    backup.parent.mkdir(parents=True, exist_ok=True)
    if not backup.exists():
        shutil.copy2(disk, backup)
    material = u.load_asset(path)
    emission = L.get_material_property_input_node(material, u.MaterialProperty.MP_EMISSIVE_COLOR)
    if not recipe['apply_decoration_protection'](material):
        raise RuntimeError('Expected a finish repair: ' + path)
    nodes = list(L.get_material_expressions(material))
    mask = next(n for n in nodes if str(n.get_editor_property('desc')) == recipe['REVISION'])
    fields = {}
    for node in nodes:
        desc = str(node.get_editor_property('desc'))
        if not desc.startswith(recipe['COMMON']['FINISH_PREFIX']):
            continue
        field = desc.removeprefix(recipe['COMMON']['FINISH_PREFIX'])
        if field in ['BASE_COLOR', 'ROUGHNESS', 'NORMAL', 'METALLIC', 'ANISOTROPY', 'TANGENT']:
            inputs = dict(zip(map(str, L.get_material_expression_input_names(node)), L.get_inputs_for_material_expression(material, node)))
            if inputs.get('Mask') != mask:
                raise RuntimeError('Unprotected channel: ' + path + ' ' + field)
            fields[field] = True
    if len(fields) != 6 or emission != L.get_material_property_input_node(material, u.MaterialProperty.MP_EMISSIVE_COLOR):
        raise RuntimeError('Incomplete PBR or changed rune emission: ' + path)
    errors = L.recompile_material(material)
    if errors:
        raise RuntimeError('Shader compilation failed: ' + str(errors))
    if not E.save_loaded_asset(material, False):
        raise RuntimeError('Save failed: ' + path)
    receipt['materials'].append({'asset': path, 'saved': True, 'protected_channels': list(fields),
                                 'rune_emission_preserved': True, 'shader_compile_errors': list(errors)})
    (P / 'material-receipt.json').write_text(json.dumps(receipt, indent=2) + '\n', encoding='utf-8')
    print('ZHANMADAO_DECORATION_SAVED', len(receipt['materials']), len(paths), path)
print('ZHANMADAO_DECORATION_COMPLETE', len(receipt['materials']))
