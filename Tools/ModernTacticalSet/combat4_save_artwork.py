"""Save revised four item displays, pickups and UI textures in the R4 stage."""
import json,importlib.util,gc,os
from pathlib import Path
import unreal as u
P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/ModernTacticalSet20261113/CombatShirtR4';DEST='/Game/Characters/ModularOutfit20260924/ModernTacticalSet20261113/CombatShirtR4';E=u.EditorAssetLibrary;A=u.AssetToolsHelpers.get_asset_tools()
def read(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def module(name,file):
    spec=importlib.util.spec_from_file_location(name,str(P/file));m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
io=module('r4_static','Tools/ChainmailPants/save_assets.py');io.DEST=DEST;builder=module('r4_buffers','Tools/FieldHat/save_icon.py');saved=read(R/'artwork-saved.json').get('items',{}) if (R/'artwork-saved.json').exists() else {}
for item,art in read(R/'artwork.json')['items'].items():
    if os.environ.get('TS01_R4_ART_KIND') and art['kind']!=os.environ['TS01_R4_ART_KIND']:continue
    saved[item]={};label=art['kind']
    for kind,file in [('pickup',art['pickup']),('display',art['icon']['display'])]:
        d=read(file);mats=[u.load_asset(p) for p in d['materials']]
        if not all(mats):raise RuntimeError('Missing actual PBR '+label)
        dm=builder.dynamic(d);saved[item][kind]=io.static(dm,DEST+'/Display/SM_TS01_'+label+'_'+kind,mats);del d,dm;gc.collect();u.SystemLibrary.collect_garbage()
    task=u.AssetImportTask();task.filename=art['icon']['png'];task.destination_path=DEST+'/Display';task.destination_name='T_TS01_'+label+'_Icon';task.automated=True;task.replace_existing=True;task.save=False;A.import_asset_tasks([task]);texture=u.load_asset(DEST+'/Display/T_TS01_'+label+'_Icon')
    for key,value in dict(srgb=True,compression_settings=u.TextureCompressionSettings.TC_EDITOR_ICON,lod_group=u.TextureGroup.TEXTUREGROUP_UI,mip_gen_settings=u.TextureMipGenSettings.TMGS_NO_MIPMAPS).items():texture.set_editor_property(key,value)
    if not E.save_loaded_asset(texture,False):raise RuntimeError('UI texture save')
    saved[item]['texture']=texture.get_path_name();print('R4_ART_SAVED',item,flush=True)
(R/'artwork-saved.json').write_text(json.dumps(dict(completed=True,items=saved),indent=2),encoding='utf-8')
