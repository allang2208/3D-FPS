"""Import only these six blade models/icons; merge blade_1 options into live catalogs."""
from pathlib import Path
from datetime import datetime
import copy
import json
import shutil
import unreal as u

P = Path(__file__).resolve().parent
ROOT = P.parents[1]
L = u.EditorAssetLibrary
A = u.AssetToolsHelpers.get_asset_tools()
if u.get_editor_subsystem(u.LevelEditorSubsystem).is_in_play_in_editor():
    raise RuntimeError('End PIE before importing blade variants; keep the editor open.')
rows = json.loads((P / 'variants.json').read_text(encoding='utf-8'))
stamp = datetime.now().strftime('%Y%m%d-%H%M%S')
backup = P / 'Before' / stamp
backup.mkdir(parents=True, exist_ok=True)
receipt = {'time': datetime.now().isoformat(), 'assets': [], 'catalogs': [],
           'runtime_tests': 'Not run; user will test.',
           'trace_policy': 'Copy factory trace points; existing range multiplier remains the sole modifier.'}
receipt_path = P / ('install_receipt-' + stamp + '.json')


def record():
    receipt_path.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


u.SystemLibrary.execute_console_command(None, 'Interchange.FeatureFlags.Import.FBX 0')
for row in rows:
    donor = u.load_asset(row['donor'])
    if not donor:
        raise RuntimeError('Factory blade missing: ' + row['donor'])
    family = 'FrostCrystalSword20260915' if row['weapon'] == 'ue_frost_crystal_sword' else 'AzureRunesword20260913'
    destination = '/Game/Weapons/' + family + '/BladeVariants20260922'
    opt = u.FbxImportUI()
    opt.automated_import_should_detect_type = False
    opt.mesh_type_to_import = u.FBXImportType.FBXIT_STATIC_MESH
    opt.import_as_skeletal = False
    opt.import_mesh = True
    opt.import_materials = False
    opt.import_textures = False
    opt.import_animations = False
    data = opt.static_mesh_import_data
    data.combine_meshes = True
    data.auto_generate_collision = False
    data.generate_lightmap_u_vs = False
    data.normal_import_method = u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS
    data.vertex_color_import_option = u.VertexColorImportOption.REPLACE
    task = u.AssetImportTask()
    task.filename = str(P / 'Export' / (row['mesh'] + '.fbx'))
    task.destination_path = destination
    task.destination_name = row['mesh']
    task.automated = True
    task.replace_existing = True
    task.save = False
    task.options = opt
    A.import_asset_tasks([task])
    asset = u.load_asset(destination + '/' + row['mesh'])
    if not asset or not task.imported_object_paths:
        raise RuntimeError('Blade import failed: ' + row['mesh'])
    # Same topology/material indices as the factory; use its current UE finish bindings.
    asset.set_editor_property('static_materials', donor.get_editor_property('static_materials'))
    L.set_metadata_tag(asset, 'BladeVariantRevision', '20260922-V1')
    L.set_metadata_tag(asset, 'FactorySource', row['donor'])
    if not L.save_loaded_asset(asset, False):
        raise RuntimeError('Cannot save blade: ' + row['mesh'])
    entry = dict(weapon=row['weapon'], option=row['option'], mesh=asset.get_path_name(), mesh_saved=True)
    receipt['assets'].append(entry)
    record()
    row['asset'] = asset.get_path_name()

    png = ROOT / 'Content/ColdSteelData/AttachmentIcons20260913' / row['icon']
    if png.exists():
        shutil.copy2(png, backup / png.name)
    icon_asset = '/Game/ColdSteelData/AttachmentIcons20260913/' + png.stem
    existing_package = png.with_suffix('.uasset')
    if existing_package.exists():
        shutil.copy2(existing_package, backup / existing_package.name)
    shutil.copy2(P / 'Icons' / row['icon'], png)
    result = u.ModelingService.import_texture(str(png), icon_asset, True, 'Default', True)
    if not result.success:
        raise RuntimeError(result.message)
    texture = u.load_asset(icon_asset)
    texture.set_editor_property('compression_settings', u.TextureCompressionSettings.TC_EDITOR_ICON)
    texture.set_editor_property('lod_group', u.TextureGroup.TEXTUREGROUP_UI)
    texture.set_editor_property('mip_gen_settings', u.TextureMipGenSettings.TMGS_NO_MIPMAPS)
    texture.set_editor_property('srgb', True)
    if not L.save_loaded_asset(texture, False):
        raise RuntimeError('Cannot save icon: ' + icon_asset)
    entry.update(icon=texture.get_path_name(), icon_saved=True)
    record()

labels = {
    'extended_edge': '延展剑尖 · 修长刃形',
    'heavy_spine': '加厚剑脊 · 宽阔刃面',
    'feather_edge': '收窄削薄 · 轻巧刃形',
}
for filename in dict.fromkeys(row['catalog'] for row in rows):
    path = ROOT / 'Content/ColdSteelData' / filename
    # Read immediately before merging; preserve every other slot and concurrent addition.
    catalog = json.loads(path.read_text(encoding='utf-8'))
    shutil.copy2(path, backup / filename)
    choices = catalog['slots']['blade_1']
    for row in rows:
        if row['catalog'] != filename:
            continue
        spec = copy.deepcopy(choices['factory'])
        spec.update(mesh=row['asset'], rune_dimensions_cm=row['rune_dimensions_cm'],
                    appearance=labels[row['option']])
        choices[row['option']] = spec
    path.write_text(json.dumps(catalog, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    receipt['catalogs'].append(str(path))
    record()
receipt['complete'] = True
record()
print('SIX_SWORD_BLADE_VARIANTS_INSTALLED ' + str(receipt_path))
