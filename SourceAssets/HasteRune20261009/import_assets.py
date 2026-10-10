"""Import and save only the new haste mask/icon through the serialized UE bridge."""
from pathlib import Path
import json
import unreal as u
P=Path(__file__).resolve().parent
L=u.EditorAssetLibrary
assets=[('T_Mask_haste_rune','/Game/Weapons/MeleeRunes20260915/SurfaceV2',False),('blade_2_haste_rune','/Game/ColdSteelData/AttachmentIcons20260913',True)]
saved=[]
for name,folder,icon in assets:
    path=folder+'/'+name
    old=u.load_asset(path) if L.does_asset_exist(path) else None
    if old and L.get_metadata_tag(old,'AuthoringRevision')!='HasteRune20261009':
        raise RuntimeError('Preserve existing unrelated asset: '+path)
    task=u.AssetImportTask()
    for key,value in {'filename':str(P/(name+'.png')),'destination_path':folder,'destination_name':name,'automated':True,'replace_existing':True,'save':False}.items():task.set_editor_property(key,value)
    u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    texture=u.load_asset(path)
    if not texture:raise RuntimeError('Texture import did not create '+path)
    if icon:
        texture.set_editor_property('srgb',True)
        texture.set_editor_property('lod_group',u.TextureGroup.TEXTUREGROUP_UI)
        texture.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_DEFAULT)
    else:
        donor=u.load_asset('/Game/Weapons/MeleeRunes20260915/SurfaceV2/T_Mask_conduction_rune')
        if not donor:raise RuntimeError('Existing rune sampler source missing')
        for key in ['compression_settings','lod_group','mip_gen_settings','filter']:
            texture.set_editor_property(key,donor.get_editor_property(key))
        texture.set_editor_property('srgb',False)
        texture.set_editor_property('address_x',u.TextureAddress.TA_CLAMP)
        texture.set_editor_property('address_y',u.TextureAddress.TA_CLAMP)
    L.set_metadata_tag(texture,'AuthoringRevision','HasteRune20261009')
    if not L.save_loaded_asset(texture,False):raise RuntimeError('Could not save '+path)
    saved.append(texture.get_path_name())
(P/'import_receipt.json').write_text(json.dumps({'complete':True,'saved_assets':saved,'runtime_tested':False},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('HASTE_RUNE_ASSETS_SAVED '+json.dumps(saved))
