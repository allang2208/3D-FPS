"""Save the empty, actual GAME garment/carrier artwork and pickup."""
import json,importlib.util,gc
from pathlib import Path
import unreal as u
P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/ModernTacticalSet20261113/CombatShirtR3';DEST='/Game/Characters/ModularOutfit20260924/ModernTacticalSet20261113/CombatShirtR3';E=u.EditorAssetLibrary;A=u.AssetToolsHelpers.get_asset_tools()
def read(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def module(name,file):
    spec=importlib.util.spec_from_file_location(name,str(P/file));m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
io=module('combat3_static','Tools/ChainmailPants/save_assets.py');io.DEST=DEST;builder=module('combat3_buffers','Tools/FieldHat/save_icon.py');saved={}
for prefix,filename,label in [('', 'artwork.json','CombatShirtCarrier'),('pants_','lower-artwork.json','CombatTrousers')]:
    art=read(R/filename)
    for kind,file in [('pickup',art['pickup']),('display',art['icon']['display'])]:
        d=read(file);mats=[u.load_asset(p) for p in d['materials']]
        if not all(mats):raise RuntimeError('Missing production PBR '+kind)
        dm=builder.dynamic(d);saved[prefix+kind]=io.static(dm,DEST+'/Display/SM_'+label+'_'+kind,mats);del d,dm;gc.collect();u.SystemLibrary.collect_garbage()
    task=u.AssetImportTask();task.filename=art['icon']['png'];task.destination_path=DEST+'/Display';task.destination_name='T_'+label+'_Icon';task.automated=True;task.replace_existing=True;task.save=False;A.import_asset_tasks([task]);texture=u.load_asset(DEST+'/Display/T_'+label+'_Icon')
    for key,value in dict(srgb=True,compression_settings=u.TextureCompressionSettings.TC_EDITOR_ICON,lod_group=u.TextureGroup.TEXTUREGROUP_UI,mip_gen_settings=u.TextureMipGenSettings.TMGS_NO_MIPMAPS).items():texture.set_editor_property(key,value)
    if not E.save_loaded_asset(texture,False):raise RuntimeError('Inventory image save')
    saved[prefix+'texture']=texture.get_path_name()
saved['completed']=True;(R/'artwork-saved.json').write_text(json.dumps(saved,indent=2));print('TS01_COMBAT3_ARTWORK_SAVED',flush=True)
