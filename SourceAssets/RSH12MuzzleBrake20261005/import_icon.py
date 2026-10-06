"""Save the finished exclusive icon in the actual framed firearm lookup folder."""
import json,shutil
from pathlib import Path
import unreal as u
O=Path(__file__).resolve().parent;P=O.parents[1]
name='ue_rsh12_muzzle_rsh12_large_caliber_brake'
source=O/(name+'.png');folder='ColdSteelData/AttachmentIcons20260913/FramedFirearms'
if '-run=pythonscript' not in u.SystemLibrary.get_command_line().lower():
    editor=u.get_editor_subsystem(u.UnrealEditorSubsystem)
    if editor and editor.get_game_world():raise RuntimeError('PIE blocks RSH icon import')
package='/Game/'+folder+'/'+name
dirty={p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
if package in dirty:raise RuntimeError('RSH icon has unsaved edits; not replacing')
backup=O/'Before';backup.mkdir(exist_ok=True)
for suffix in ('.png','.uasset'):
    current=P/'Content'/folder/(name+suffix)
    if current.exists() and not (backup/current.name).exists():shutil.copy2(current,backup/current.name)
task=u.AssetImportTask();task.filename=str(source);task.destination_path='/Game/'+folder;task.destination_name=name
task.automated=True;task.replace_existing=True;task.save=False;u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
tex=u.load_asset(task.destination_path+'/'+name)
if not tex:raise RuntimeError('Icon texture import failed')
tex.srgb=True;tex.lod_group=u.TextureGroup.TEXTUREGROUP_UI
tex.compression_settings=u.TextureCompressionSettings.TC_EDITOR_ICON
tex.never_stream=True;tex.mip_gen_settings=u.TextureMipGenSettings.TMGS_NO_MIPMAPS
if not u.EditorAssetLibrary.save_loaded_asset(tex,False):raise RuntimeError('Icon texture save failed')
destination=P/'Content'/folder/source.name;shutil.copy2(source,destination)
(O/'icon_receipt.json').write_text(json.dumps(dict(source=str(source),png=str(destination),texture=tex.get_path_name(),runtime_tested=False),indent=2),encoding='utf8')
print('RSH_MUZZLE_BRAKE_ICON_SAVED',tex.get_path_name(),flush=True)
