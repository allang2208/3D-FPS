"""Save the matching UI Texture2D and its loose Slate PNG."""
from pathlib import Path
import os,json,hashlib
import unreal as u
P=Path('D:/FPS3D/FPSGAME/SourceAssets/HighlandGaleWingFeather20261107');root=P.parents[1]
key='ue_highland_claymore_guard_highland_gale_wing';pkg='/Game/ColdSteelData/AttachmentIcons20260913/'+key
src=P/'Icon'/(key+'.png');dest=root/'Content/ColdSteelData/AttachmentIcons20260913'/(key+'.png')
ed=u.get_editor_subsystem(u.UnrealEditorSubsystem)
if ed and ed.get_game_world() is not None:raise RuntimeError('Preserving active PIE')
if any(p.get_path_name()==pkg for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()):raise RuntimeError('Preserving unsaved guard icon')
raw=src.read_bytes();before=dest.read_bytes()
task=u.AssetImportTask();task.filename=str(src);task.destination_path=pkg.rsplit('/',1)[0];task.destination_name=key;task.factory=u.TextureFactory();task.automated=True;task.replace_existing=True;task.save=False
u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task]);out=u.load_asset(pkg)
if not task.imported_object_paths or not isinstance(out,u.Texture2D):raise RuntimeError('Guard icon import failed')
out.set_editor_properties(dict(lod_group=u.TextureGroup.TEXTUREGROUP_UI,compression_settings=u.TextureCompressionSettings.TC_EDITOR_ICON,srgb=True,never_stream=True,mip_gen_settings=u.TextureMipGenSettings.TMGS_NO_MIPMAPS,address_x=u.TextureAddress.TA_CLAMP,address_y=u.TextureAddress.TA_CLAMP))
u.EditorAssetLibrary.set_metadata_tag(out,'HighlandIconRevision','GaleFeatherSolid20261107R2')
if not u.EditorAssetLibrary.save_loaded_asset(out,False):raise RuntimeError('Guard icon save failed')
if dest.read_bytes()!=before:raise RuntimeError('Another user updated the PNG')
tmp=dest.with_suffix('.gale-feather.tmp');tmp.write_bytes(raw);os.replace(tmp,dest)
(P/'saved-icon.json').write_text(json.dumps({'texture':out.get_path_name(),'loose_png':str(dest),'sha256':hashlib.sha256(raw).hexdigest(),'saved':True},indent=2))
print('FEATHER_ICON_SAVED')
