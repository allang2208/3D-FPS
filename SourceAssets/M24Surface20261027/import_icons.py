"""Publish approved framed art, the actual load keys and saved UI textures."""
import unreal as u,json,shutil,hashlib
from pathlib import Path
O=Path(__file__).resolve().parent;P=O.parents[1];E=u.EditorAssetLibrary;A=u.AssetToolsHelpers.get_asset_tools()
directory=P/'Content/ColdSteelData/AttachmentIcons20260913/FramedFirearms'
mapping={}
for slot,key in [('optic','m24_custom_scope_6x'),('muzzle','m24_factory_suppressor'),('stock','m24_cheekrest')]:
    mapping[slot+'_'+key]=key;mapping['ue_m24_'+slot+'_false']=key
mapping['optic_m24_palma_iron']='m24_palma_iron'
R={'complete':False,'saved':[],'mapping':mapping,'shared_categories':['category_optic','category_muzzle','category_stock'],'shared_none':'tactical_false','runtime_tested':False,'pngs':{}}
def record():(O/'icon_receipt.json').write_text(json.dumps(R,indent=2),encoding='utf-8')
dirty={p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
dest='/Game/UI/AttachmentIcons20260913/FramedFirearms'
for name,key in mapping.items():
    if dest+'/T_'+name in dirty:raise RuntimeError('Icon has unsaved editor changes: '+name)
    target=directory/(name+'.png');before=O/'BeforeIcons'/(name+'.png');before.parent.mkdir(exist_ok=True)
    if target.exists() and not before.exists():shutil.copy2(target,before)
    shutil.copy2(O/'Icons'/(key+'.png'),target)
    t=u.AssetImportTask();t.filename=str(target);t.destination_path=dest;t.destination_name='T_'+name;t.automated=True;t.replace_existing=True;t.save=False;A.import_asset_tasks([t])
    tex=u.load_asset(dest+'/'+t.destination_name)
    if not tex:raise RuntimeError('Texture import failed '+name)
    for prop,value in {'lod_group':u.TextureGroup.TEXTUREGROUP_UI,'compression_settings':u.TextureCompressionSettings.TC_EDITOR_ICON,'srgb':True,'never_stream':True,'mip_gen_settings':u.TextureMipGenSettings.TMGS_NO_MIPMAPS,'max_texture_size':1024}.items():tex.set_editor_property(prop,value)
    if not E.save_loaded_asset(tex,False):raise RuntimeError('Texture save failed '+name)
    R['saved'].append(tex.get_path_name());R['pngs'][name]={'path':str(target),'sha256':hashlib.sha256(target.read_bytes()).hexdigest(),'source':str(O/'Icons'/(key+'.png'))};record()
R['complete']=True;record();print('M24_STANDARD_ICONS_SAVED',len(R['saved']),flush=True)
