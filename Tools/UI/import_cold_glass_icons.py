"""UE commandlet: import reviewed icons and compose away their near-black backdrop."""
from pathlib import Path
import json
import unreal

root = Path(unreal.Paths.project_dir())
source = root / 'SourceAssets/GunsmithComponentIcons20260912/Candidates/cold-steel-v1'
dest = '/Game/UI/GunsmithWorkbench/ColdGlass'
assets = unreal.AssetToolsHelpers.get_asset_tools()
lib = unreal.MaterialEditingLibrary
unreal.EditorAssetLibrary.make_directory(dest)
manifest = json.loads((source / 'manifest.json').read_text(encoding='utf-8'))
textures = []
for entry in manifest['images']:
    slot = 'foregrip' if entry['key'] == 'barrel' else entry['key']
    task = unreal.AssetImportTask()
    task.set_editor_property('filename', str(source / entry['filename']))
    task.set_editor_property('destination_path', dest)
    task.set_editor_property('destination_name', 'T_Category_' + slot)
    task.set_editor_property('automated', True)
    task.set_editor_property('replace_existing', True)
    task.set_editor_property('save', True)
    assets.import_asset_tasks([task])
    texture = unreal.load_asset(dest + '/T_Category_' + slot)
    assert isinstance(texture, unreal.Texture2D), slot
    texture.set_editor_property('compression_settings', unreal.TextureCompressionSettings.TC_EDITOR_ICON)
    texture.set_editor_property('lod_group', unreal.TextureGroup.TEXTUREGROUP_UI)
    texture.set_editor_property('srgb', True)
    texture.set_editor_property('never_stream', True)
    unreal.EditorAssetLibrary.save_loaded_asset(texture)
    textures.append(texture)

name = 'M_CategoryIcon'
material = unreal.load_asset(dest + '/' + name) or assets.create_asset(name, dest, unreal.Material, unreal.MaterialFactoryNew())
lib.delete_all_material_expressions(material)
material.set_editor_property('material_domain', unreal.MaterialDomain.MD_UI)
material.set_editor_property('blend_mode', unreal.BlendMode.BLEND_TRANSLUCENT)
tex = lib.create_material_expression(material, unreal.MaterialExpressionTextureSampleParameter2D)
tex.set_editor_property('parameter_name', 'IconTexture')
tex.set_editor_property('texture', textures[0])
subtract = lib.create_material_expression(material, unreal.MaterialExpressionSubtract)
subtract.set_editor_property('const_b', 0.012)
multiply = lib.create_material_expression(material, unreal.MaterialExpressionMultiply)
multiply.set_editor_property('const_b', 100.0)
opacity = lib.create_material_expression(material, unreal.MaterialExpressionClamp)
assert lib.connect_material_expressions(tex, 'R', subtract, 'A')
assert lib.connect_material_expressions(subtract, '', multiply, 'A')
assert lib.connect_material_expressions(multiply, '', opacity, '')
assert lib.connect_material_property(tex, 'RGB', unreal.MaterialProperty.MP_EMISSIVE_COLOR)
assert lib.connect_material_property(opacity, '', unreal.MaterialProperty.MP_OPACITY)
lib.recompile_material(material)
unreal.EditorAssetLibrary.save_loaded_asset(material)
report = dict(icon_count=len(textures), material=material.get_path_name(), icons=[x.get_path_name() for x in textures], method='UI material near-black luminance key; reviewed source PNGs unchanged')
output = root / 'Saved/ColdGlassIntegration20260912'
output.mkdir(parents=True, exist_ok=True)
(output / 'import-result.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
unreal.log('COLD_GLASS_IMPORT_COMPLETE ' + json.dumps(report))
