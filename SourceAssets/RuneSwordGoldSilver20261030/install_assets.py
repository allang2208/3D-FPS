"""Background production import. Saves only the new silver rune instance and icon."""
from pathlib import Path
import json
import unreal as u

P=Path(__file__).resolve().parent
ROOT=P.parents[1]
E=u.MaterialEditingLibrary
L=u.EditorAssetLibrary
D='/Game/Weapons/AzureRunesword20260913/SilverRune20261030'
source='/Game/Weapons/AzureRunesword20260913/NativeRuneGold20260922/MI_AzureRunesword_NativeGold'
destination=D+'/MI_AzureRunesword_NativeSilver'
mi=u.load_asset(destination) or L.duplicate_asset(source,destination)
if not mi:raise RuntimeError('Native rune instance unavailable')
# Same native masks, PBR, common blade/guard phase and soft fading emission.
# Explicit overrides on the child instance prevent gold defaults leaking into silver.
colors={'GoldColor':(.48,.51,.56,1.),'GlowColor':(.82,.87,.94,1.)}
available={str(name) for name in E.get_vector_parameter_names(mi)}
for name,rgba in colors.items():
    if name not in available:
        raise RuntimeError('Missing native rune parameter: '+name)
    # UE 5.8 MaterialEditingLibrary.cpp sets the value but always returns false.
    E.set_material_instance_vector_parameter_value(mi,name,u.LinearColor(*rgba))
E.set_material_instance_scalar_parameter_value(mi,'GoldAmount',1.)
E.set_material_instance_scalar_parameter_value(mi,'GlowStrength',.58)
E.update_material_instance(mi)
L.set_metadata_tag(mi,'RuneSemanticId','silver_glow_rune')
L.set_metadata_tag(mi,'NativeGlyphs','Original UV0 blade and guard masks; shared phase retained')
if not L.save_loaded_asset(mi,False):raise RuntimeError('Silver material was not saved')

name='blade_2_silver_glow_rune'
asset_dir='/Game/ColdSteelData/AttachmentIcons20260913'
task=u.AssetImportTask()
task.filename=str(ROOT/'Content/ColdSteelData/AttachmentIcons20260913'/(name+'.png'))
task.destination_path=asset_dir
task.destination_name=name
task.automated=True
task.replace_existing=True
task.save=False
u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
icon=u.load_asset(asset_dir+'/'+name)
if not icon:raise RuntimeError('Silver icon import failed')
icon.set_editor_property('lod_group',u.TextureGroup.TEXTUREGROUP_UI)
icon.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_EDITOR_ICON)
icon.set_editor_property('srgb',True)
icon.set_editor_property('never_stream',True)
icon.set_editor_property('mip_gen_settings',u.TextureMipGenSettings.TMGS_NO_MIPMAPS)
if not L.save_loaded_asset(icon,False):raise RuntimeError('Silver icon was not saved')
(P/'asset-receipt.json').write_text(json.dumps({'saved_assets':[mi.get_path_name(),icon.get_path_name()],
 'native_mask_source':source,'silver_linear_colors':colors,'gameplay_tested':False,
 'editor_gui_opened':False},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('SILVER_RUNE_ASSETS_SAVED')
