"""Replace only the saved Conical Seat UI texture with the V2 generated icon."""
import json
from pathlib import Path
import unreal as u
P=Path(__file__).resolve().parent;ROOT=P.parents[2]
if Path(u.Paths.project_dir()).resolve()!=ROOT:raise RuntimeError('Wrong project')
D='/Game/Weapons/CommonHammerSeats20261107/ConicalSeatV1';NAME='head_mount_conical_seat';PATH=D+'/'+NAME
E=u.EditorAssetLibrary;A=u.AssetToolsHelpers.get_asset_tools()
old=u.load_asset(PATH)
if not old or E.get_metadata_tag(old,'ConicalSeatOwner')!='ConicalHammerSeat20261107_BuildV1':
    raise RuntimeError('Original owned icon is missing or belongs to another task')
task=u.AssetImportTask();task.filename=str(P/(NAME+'.png'));task.destination_path=D;task.destination_name=NAME
task.automated=True;task.replace_existing=True;task.replace_existing_settings=True;task.save=False
A.import_asset_tasks([task]);icon=u.load_asset(PATH)
if not icon:raise RuntimeError('Icon import did not produce a texture')
icon.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_EDITOR_ICON)
icon.set_editor_property('lod_group',u.TextureGroup.TEXTUREGROUP_UI)
icon.set_editor_property('srgb',True);icon.set_editor_property('never_stream',True)
icon.set_editor_property('mip_gen_settings',u.TextureMipGenSettings.TMGS_NO_MIPMAPS)
icon.set_editor_property('max_texture_size',1024)
E.set_metadata_tag(icon,'ConicalSeatOwner','ConicalHammerSeat20261107_BuildV1')
E.set_metadata_tag(icon,'ConicalSeatIconRevision','IconV2_Imagegen_20261107')
if not E.save_loaded_asset(icon,False):raise RuntimeError('Cannot save replaced icon')
(P/'import_receipt.json').write_text(json.dumps({'complete':True,'asset':icon.get_path_name(),'source':task.filename,'revision':'IconV2',
    'generator':'built-in imagegen','models_modified':False,'materials_modified':False,'game_tested':False,'editor_ui_started':False},ensure_ascii=False,indent=2),encoding='utf-8')
print('CONICAL_SEAT_ICON_V2_IMPORTED_AND_SAVED')
