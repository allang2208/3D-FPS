"""Install the two magazine icons at the UI's actual resolved keys."""
import unreal as u,json,shutil,hashlib
from pathlib import Path
O=Path(__file__).resolve().parent;P=O.parents[1]
D='/Game/UI/AttachmentIcons20260913/FramedFirearms';disk=P/'Content/ColdSteelData/AttachmentIcons20260913/FramedFirearms'
mapping={'ue_m24_magazine_false':'m24_factory_mag_5','magazine_m24_extended_mag_10':'m24_extended_mag_10'}
R={'complete':False,'saved':[],'mapping':mapping,'pngs':{},'shared_category':'category_magazine','runtime_tested':False}
dirty={p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
def record():(O/'icon_receipt.json').write_text(json.dumps(R,indent=2),encoding='utf-8')
for key,source in mapping.items():
 if D+'/T_'+key in dirty:raise RuntimeError('Unsaved icon '+key)
 path=O/'Icons'/(source+'.png')
 if not path.exists():raise RuntimeError('Missing finished icon '+str(path))
 target=disk/(key+'.png');backup=O/'BeforeIcons'/(key+'.png')
 if target.exists() and not backup.exists():backup.parent.mkdir(exist_ok=True);shutil.copy2(target,backup)
 shutil.copy2(path,target)
 task=u.AssetImportTask();task.filename=str(target);task.destination_path=D;task.destination_name='T_'+key
 task.automated=True;task.replace_existing=True;task.save=False;u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
 texture=u.load_asset(D+'/'+task.destination_name)
 if not texture:raise RuntimeError('Icon import failed '+key)
 for prop,value in {'lod_group':u.TextureGroup.TEXTUREGROUP_UI,'compression_settings':u.TextureCompressionSettings.TC_EDITOR_ICON,'srgb':True,'never_stream':True,'mip_gen_settings':u.TextureMipGenSettings.TMGS_NO_MIPMAPS,'max_texture_size':1024}.items():texture.set_editor_property(prop,value)
 if not u.EditorAssetLibrary.save_loaded_asset(texture,False):raise RuntimeError('Could not save '+key)
 R['saved'].append(texture.get_path_name());R['pngs'][key]={'path':str(target),'sha256':hashlib.sha256(target.read_bytes()).hexdigest(),'source':str(path)};record()
R['complete']=True;record();print('M24_MAGAZINE_ICONS_SAVED',len(R['saved']),flush=True)
