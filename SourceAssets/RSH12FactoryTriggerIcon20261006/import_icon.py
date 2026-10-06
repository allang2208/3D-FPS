"""Replace the RSH factory-trigger icon only; no gameplay or native build."""
import json,shutil
from pathlib import Path
import unreal as u
O=Path(__file__).resolve().parent;P=O.parents[1]
name='ue_rsh12_trigger_false';source=O/(name+'.png')
folder='ColdSteelData/AttachmentIcons20260913/FramedFirearms'
package='/Game/'+folder+'/'+name
if '-run=pythonscript' not in u.SystemLibrary.get_command_line().lower():
    editor=u.get_editor_subsystem(u.UnrealEditorSubsystem)
    if editor and editor.get_game_world():raise RuntimeError('PIE blocks saving the RSH trigger icon texture')
if package in {p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}:
    raise RuntimeError('The RSH trigger icon texture has unsaved edits')
backup=O/'Before';backup.mkdir(exist_ok=True)
old=P/'Content'/folder/(name+'.uasset')
if old.exists() and not (backup/old.name).exists():shutil.copy2(old,backup/old.name)
task=u.AssetImportTask();task.filename=str(source);task.destination_path='/Game/'+folder;task.destination_name=name
task.automated=True;task.replace_existing=True;task.save=False
u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
texture=u.load_asset(package)
if not texture:raise RuntimeError('RSH factory trigger texture import failed')
texture.srgb=True;texture.lod_group=u.TextureGroup.TEXTUREGROUP_UI
texture.compression_settings=u.TextureCompressionSettings.TC_EDITOR_ICON
texture.never_stream=True;texture.mip_gen_settings=u.TextureMipGenSettings.TMGS_NO_MIPMAPS
if not u.EditorAssetLibrary.save_loaded_asset(texture,False):raise RuntimeError('RSH factory trigger texture save failed')
(O/'import_receipt.json').write_text(json.dumps({'complete':True,'weapon':'ue_rsh12','slot':'trigger','option':'false',
 'texture':texture.get_path_name(),'source':str(source),'png':str(P/'Content'/folder/(name+'.png')),
 'gameplay_changed':False,'runtime_tested':False},indent=2),encoding='utf8')
delivery=json.loads((O/'generation.json').read_text(encoding='utf8'))
delivery.update(status='png_replaced_ue_texture_saved',ue_texture_saved=True,texture=texture.get_path_name(),
                native_build_required=False,runtime_tested=False)
(O/'delivery.json').write_text(json.dumps(delivery,indent=2),encoding='utf8')
print('RSH_FACTORY_TRIGGER_ICON_SAVED',texture.get_path_name(),flush=True)
