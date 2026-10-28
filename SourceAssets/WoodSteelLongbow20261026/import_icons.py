"""Publish the four owned game icons and save their UE texture assets."""
from pathlib import Path
import json, shutil
import unreal as u
P=Path(__file__).parent
root=Path('D:/FPS3D/FPSGAME/Content')
receipt=P/'icon-import-receipt.json'
r=json.loads(receipt.read_text()) if receipt.exists() else {'saved':{}}
rows=[(P/'Icons/bow_woodsteel.png','ColdSteelData/Icons','bow_woodsteel')]
rows += [(P/'Icons/Framed'/('factory_'+slot+'.png'),'ColdSteelData/AttachmentIcons20260913/FramedBows','bow_woodsteel_'+slot+'_false') for slot in ['riser','grip','arrow_rest']]
E=u.EditorAssetLibrary
for src,folder,name in rows:
    assetpath='/Game/'+folder+'/'+name
    if name in r['saved']:continue
    if E.does_asset_exist(assetpath):raise RuntimeError('Preserving existing unowned icon '+assetpath)
    target=root/folder/(name+'.png');target.parent.mkdir(parents=True,exist_ok=True)
    shutil.copy2(src,target)
    task=u.AssetImportTask();task.filename=str(target);task.destination_path='/Game/'+folder
    task.destination_name=name;task.automated=True;task.save=False
    u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    tex=u.load_asset(assetpath)
    if not tex:raise RuntimeError('Icon import failed '+name)
    tex.lod_group=u.TextureGroup.TEXTUREGROUP_UI
    tex.compression_settings=u.TextureCompressionSettings.TC_EDITOR_ICON
    tex.mip_gen_settings=u.TextureMipGenSettings.TMGS_NO_MIPMAPS
    tex.srgb=True;tex.max_texture_size=1024
    if not u.EditorLoadingAndSavingUtils.save_packages([tex.get_outermost()],False):raise RuntimeError('Icon save failed '+name)
    r['saved'][name]=tex.get_path_name()
    receipt.write_text(json.dumps(r,indent=2),encoding='utf-8')
r['complete']=True;receipt.write_text(json.dumps(r,indent=2),encoding='utf-8')
print('WOOD_STEEL_LONGBOW_ICONS_SAVED')
