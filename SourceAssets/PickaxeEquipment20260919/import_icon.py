"""Install only the requested pickaxe inventory icon in the running editor."""
import json
import shutil
from pathlib import Path
import unreal as u

ROOT = Path(u.Paths.project_dir()).resolve()
HERE = ROOT/'SourceAssets/PickaxeEquipment20260919'
source = HERE/'pickaxe_upright.png'
destination = ROOT/'Content/ColdSteelData/ProductionTools/pickaxe_upright.png'
package = '/Game/ColdSteelData/ProductionTools/pickaxe_upright'
if u.get_editor_subsystem(u.LevelEditorSubsystem).is_in_play_in_editor():
    raise RuntimeError('Stop PIE before installing the pickaxe equipment update.')
if any(p.get_name()==package for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()):
    # UE can auto-import this task's new PNG while the editor is starting.
    # Save that owned texture before applying its final UI import settings.
    current = u.load_asset(package)
    if not current or not u.EditorAssetLibrary.save_loaded_asset(current,False):
        raise RuntimeError('Could not save the auto-imported pickaxe_upright texture.')
shutil.copy2(source,destination)
task = u.AssetImportTask()
task.filename = str(destination)
task.destination_path = '/Game/ColdSteelData/ProductionTools'
task.destination_name = 'pickaxe_upright'
task.automated = True
task.replace_existing = True
task.save = True
u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
if not task.imported_object_paths:
    raise RuntimeError('Pickaxe icon import did not produce a texture.')
texture = u.load_asset(package)
texture.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_EDITOR_ICON)
texture.set_editor_property('lod_group',u.TextureGroup.TEXTUREGROUP_UI)
texture.set_editor_property('mip_gen_settings',u.TextureMipGenSettings.TMGS_NO_MIPMAPS)
texture.set_editor_property('never_stream',True)
if not u.EditorAssetLibrary.save_loaded_asset(texture,False):
    raise RuntimeError('Could not save pickaxe icon.')
(HERE/'icon_import_receipt.json').write_text(json.dumps({'saved':list(task.imported_object_paths),
    'png':str(destination),'footprint':[2,3],'runtime_tested':False},indent=2),encoding='utf-8')
u.log('PICKAXE_EQUIPMENT_ICON_IMPORTED')
