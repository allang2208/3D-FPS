"""Import crimson maps and save per-blade longitudinal rune materials."""
import json
import runpy
import shutil
from pathlib import Path
import unreal as u

P = Path(__file__).resolve().parent
ROOT = P.parents[1]
DATA = ROOT / 'Content/ColdSteelData'
E, L = u.EditorAssetLibrary, u.MaterialEditingLibrary
A = u.AssetToolsHelpers.get_asset_tools()
layout = runpy.run_path(str(P / 'rune_material.py'))
protection = runpy.run_path(str(P.parent / 'ChixiaoInlayPreservation20261110/inlay_material.py'))
tang = json.loads((DATA / 'tang-dao-modules.json').read_text(encoding='utf-8-sig'))
zhan = json.loads((DATA / 'zhanmadao-modules.json').read_text(encoding='utf-8-sig'))
temporal = json.loads((DATA / 'whirlwind-temporal-materials.json').read_text(encoding='utf-8-sig'))
D = '/Game/Weapons/TangDao20261002/Longitudinal20261110'
owned = {path.split('.')[0] for row in zhan['slots']['blade_1'].values() for path in row.get('materials', {}).values()
         if 'M_TangDaoBladeRuneSurface' in path}
owned |= {temporal[path].split('.')[0] for row in zhan['slots']['blade_1'].values()
          for path in row.get('materials', {}).values() if path in temporal and 'M_TangDaoBladeRuneSurface' in path}
texture_base = '/Game/Weapons/Zhanmadao20261018/ChixiaoBladeV1/Textures/T_Chixiao_'
owned |= {texture_base + key + '_V1' for key in ['BaseColor', 'ORM']}
if Path(u.Paths.project_dir()).resolve() != ROOT:
    raise RuntimeError('Use the active FPSGAME host')
if u.EditorLevelLibrary.get_pie_worlds(False):
    raise RuntimeError('PIE running; preserve session')
if any(p.get_path_name() in owned or p.get_path_name().startswith(D + '/')
       for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()):
    raise RuntimeError('Preserve unsaved target assets')
receipt = {'revision': layout['REV'], 'assets': [], 'tang_bindings': {}, 'temporal_bindings': {},
           'assets_complete': False, 'catalog_saved': False, 'game_tested': False}


def record():
    (P / 'material-receipt.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def backup(path):
    disk = ROOT / 'Content' / (path.split('.')[0].removeprefix('/Game/') + '.uasset')
    if disk.exists():
        target = P / 'BeforeAssets' / disk.relative_to(ROOT / 'Content')
        target.parent.mkdir(parents=True, exist_ok=True)
        if not target.exists():
            shutil.copy2(disk, target)


def save(asset):
    errors = list(L.recompile_material(asset) or []) if isinstance(asset, u.Material) else []
    if errors:
        raise RuntimeError('Shader compilation: ' + asset.get_path_name() + ' ' + str(errors))
    if not E.save_loaded_asset(asset, False):
        raise RuntimeError('Save failed: ' + asset.get_path_name())
    receipt['assets'].append({'asset': asset.get_path_name(), 'saved': True, 'compile_errors': errors})
    record()


for key in ['BaseColor', 'ORM']:
    path = texture_base + key + '_V1'
    backup(path)
    texture = u.load_asset(path)
    properties = {key: texture.get_editor_property(key) for key in
                  ['srgb', 'compression_settings', 'lod_group', 'never_stream', 'max_texture_size']}
    task = u.AssetImportTask()
    task.filename = str(P / 'Textures' / ('Chixiao_' + key + '_LongitudinalV2.png'))
    task.destination_path, task.destination_name = path.rsplit('/', 1)
    task.automated = True; task.replace_existing = True; task.replace_existing_settings = False
    task.save = False; task.factory = u.TextureFactory()
    A.import_asset_tasks([task])
    texture = u.load_asset(path)
    texture.set_editor_properties(properties)
    save(texture)

for choice, row in zhan['slots']['blade_1'].items():
    for path in row.get('materials', {}).values():
        if 'M_TangDaoBladeRuneSurface' not in path:
            continue
        for source in [path, temporal.get(path)]:
            if not source:
                continue
            backup(source)
            material = u.load_asset(source)
            if not layout['apply_layout'](material, 'zhanmadao/' + choice):
                raise RuntimeError('Missing rune graph: ' + source)
            save(material)
    print('ZHANMADAO_LONGITUDINAL_SAVED', choice)

for choice, row in tang['slots']['blade_1'].items():
    receipt['tang_bindings'][choice] = {'mesh': row['mesh'], 'materials': {}}
    for index, (slot, source) in enumerate(row['materials'].items()):
        name = 'M_TangDaoBladeRuneSurface_Longitudinal_' + choice + '_' + str(index) + '_V2'
        pair = []
        for is_temporal in [False, True]:
            path = D + '/' + name + ('_Whirlwind' if is_temporal else '')
            material = u.load_asset(path)
            if material and E.get_metadata_tag(material, 'DaoLongitudinalRevision') != layout['REV']:
                raise RuntimeError('Preserve an unowned target: ' + path)
            if material:
                backup(path)
            else:
                donor = temporal.get(source, source) if is_temporal else source
                material = E.duplicate_asset(donor, path)
            if not material:
                raise RuntimeError('Material duplication failed: ' + path)
            # TangDao's native warm dragon/root ornament shares the steel atlas.
            # Pure Yanling steel has no colored decoration to protect.
            if slot != 'M_TangDaoYanlingSteel':
                texture = 'T_TangDao_Tengyun_BaseColor' if choice == 'tengyun_dragon' else 'T_TangDao_BaseColor'
                protection['apply_surface_protection'](material, texture, 'DaoNativeDecoration20261110V2',
                    'return smoothstep(.002,.020,NativeColor.r-max(NativeColor.g,NativeColor.b))/3.;',
                    metadata='DaoNativeDecorationRevision')
            if not layout['apply_layout'](material, 'tang_dao/' + choice):
                raise RuntimeError('Missing TangDao rune graph: ' + path)
            save(material); pair.append(material.get_path_name())
        receipt['tang_bindings'][choice]['materials'][slot] = pair[0]
        receipt['temporal_bindings'][pair[0]] = pair[1]
    print('TANGDAO_LONGITUDINAL_SAVED', choice)
receipt['assets_complete'] = True; record()
runpy.run_path(str(P / 'catalog_extension.py'))['install']()
receipt['catalog_saved'] = True; record()
print('DAO_LONGITUDINAL_ASSETS_AND_CATALOG_SAVED', len(receipt['assets']))
