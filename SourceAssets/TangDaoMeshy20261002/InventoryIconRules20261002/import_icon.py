"""Reimport the TangDao inventory textures from the actual UE factory assembly."""
import hashlib
import json
import shutil
import struct
from pathlib import Path
import unreal as u

P = Path(__file__).resolve().parent
ROOT = P.parents[2]
FAMILY = P.parent
SOURCE = P / 'ue_tang_dao.png'
if Path(u.Paths.convert_relative_path_to_full(u.Paths.project_content_dir())).resolve() != ROOT / 'Content':
    raise RuntimeError('TangDao inventory icons require the FPSGAME host.')
data = SOURCE.read_bytes()
size = list(struct.unpack('>II', data[16:24]))
folder = '/Game/ColdSteelData/Icons'
names = ['ue_tang_dao', 'ue_tang_dao_surface_v2']
dirty = {p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
for name in names:
    if folder + '/' + name in dirty:
        raise RuntimeError('TangDao inventory texture has unsaved editor edits: ' + name)

receipt = {'definition': 'ue_tang_dao', 'source': str(SOURCE), 'size': size,
           'sha256': hashlib.sha256(data).hexdigest(), 'assets': [], 'complete': False,
           'production_source': 'saved UE factory assembly and current game materials',
           'runtime_tested': False}
for name in names:
    destination = ROOT / 'Content/ColdSteelData/Icons' / (name + '.png')
    shutil.copy2(SOURCE, destination)
    task = u.AssetImportTask()
    task.filename = str(destination)
    task.destination_path = folder
    task.destination_name = name
    task.automated = True
    task.replace_existing = True
    task.save = False
    u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    texture = u.load_asset(folder + '/' + name)
    if not texture:
        raise RuntimeError('TangDao inventory icon import failed: ' + name)
    texture.set_editor_property('lod_group', u.TextureGroup.TEXTUREGROUP_UI)
    texture.set_editor_property('compression_settings', u.TextureCompressionSettings.TC_EDITOR_ICON)
    texture.set_editor_property('mip_gen_settings', u.TextureMipGenSettings.TMGS_NO_MIPMAPS)
    texture.set_editor_property('never_stream', True)
    texture.set_editor_property('srgb', True)
    u.EditorAssetLibrary.set_metadata_tag(texture, 'TangDaoInventorySource',
                                         'ColdSteelWeaponIconCatalog -Definition=ue_tang_dao; 20261002')
    if not u.EditorLoadingAndSavingUtils.save_packages([texture.get_outermost()], False):
        raise RuntimeError('TangDao inventory icon save failed: ' + name)
    receipt['assets'].append(texture.get_path_name())
    (P / 'import_receipt.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

# Keep the existing live item key and its future SurfaceV2 publication source.
for folder_name in ['Icons', 'SurfaceV2/Icons']:
    shutil.copy2(SOURCE, FAMILY / folder_name / 'ue_tang_dao.png')
path = FAMILY / 'SurfaceV2/bindings.json'
bindings = json.loads(path.read_text(encoding='utf-8-sig'))
bindings['inventory_icon'] = 'Icons/ue_tang_dao_surface_v2.png'
bindings['inventory_icon_source'] = 'InventoryIconRules20261002/export_icon.ps1'
path.write_text(json.dumps(bindings, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
items_path = ROOT / 'Content/ColdSteelData/items.json'
items = json.loads(items_path.read_text(encoding='utf-8-sig'))
if items['ue_tang_dao'].get('ue_icon') != bindings['inventory_icon']:
    items['ue_tang_dao']['ue_icon'] = bindings['inventory_icon']
    temporary = items_path.with_suffix('.json.tangicon.tmp')
    temporary.write_text(json.dumps(items, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    temporary.replace(items_path)
receipt['complete'] = True
receipt['active_icon'] = bindings['inventory_icon']
(P / 'import_receipt.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
(FAMILY / 'SurfaceV2/inventory_import_receipt.json').write_text(json.dumps({
    'asset': receipt['assets'][-1], 'source': str(SOURCE), 'saved': True,
    'production_render': True, 'production_source': receipt['production_source'], 'tested': False,
    'receipt': str(P / 'import_receipt.json'),
}, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
(FAMILY / 'SurfaceV2/icons.json').write_text(json.dumps({
    'resolution': size, 'format': 'RGBA transparent PNG',
    'orientation': 'orthographic portrait; blade tip up; no mirroring',
    'production_source': 'current UE factory assembly',
    'production_recipe': str(P / 'export_icon.ps1'),
    'jobs': [{'filename': 'ue_tang_dao.png', 'slot': 'inventory', 'id': 'factory'}],
    'production_only': True,
}, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print('TANGDAO_INVENTORY_ICONS_IMPORTED_AND_SAVED ' + ', '.join(receipt['assets']))
