"""Save revision-owned empty shirt/carrier pickup, display mesh, and UI texture."""
import json,importlib.util,hashlib,gc
from pathlib import Path
import unreal as u
P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/ModernTacticalSet20261113/CombatShirtR1';DEST='/Game/Characters/ModularOutfit20260924/ModernTacticalSet20261113/CombatShirtR1'
E=u.EditorAssetLibrary;A=u.AssetToolsHelpers.get_asset_tools();L=u.MaterialEditingLibrary
def read(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def module(name,file):
    spec=importlib.util.spec_from_file_location(name,str(P/file));m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
def load(p):
    a=u.load_asset(p)
    if not a:raise RuntimeError('Missing artwork material '+p)
    return a
io=module('combat_static','Tools/ChainmailPants/save_assets.py');io.DEST=DEST
builder=module('combat_static_buffers','Tools/FieldHat/save_icon.py')
art=read(R/'artwork.json');result={}
for kind,file in [('pickup',art['pickup']),('display',art['icon']['display'])]:
    d=read(file);name='MI_CombatKnit_'+kind;mi=u.load_asset(DEST+'/Materials/'+name) or A.create_asset(name,DEST+'/Materials',u.MaterialInstanceConstant,u.MaterialInstanceConstantFactoryNew());L.set_material_instance_parent(mi,load(DEST+'/Materials/M_CombatFabric'))
    if kind=='pickup':
        body=read(R/'Inputs/Body_Jason.json');bones={b['name']:b for b in body['bones']};offset=art['pickup_origin_offset'];origin=[v-o for v,o in zip(bones['pelvis']['position'],offset)];height=(bones['clavicle_l']['position'][2]+bones['clavicle_r']['position'][2])*.5-bones['pelvis']['position'][2];top=151.2-offset[2]
    else:origin=[0,0,0];height=10000.;top=10000.
    L.set_material_instance_vector_parameter_value(mi,'Origin',u.LinearColor(*origin,1))
    for key,value in dict(TorsoMode=1,ShoulderHeight=height,CollarTop=top).items():L.set_material_instance_scalar_parameter_value(mi,key,value)
    L.update_material_instance(mi)
    if not E.save_loaded_asset(mi,False):raise RuntimeError('Cannot save '+name)
    mats=[mi if 'MI_CombatTorso_' in path else load(path) for path in d['materials']]
    dm=builder.dynamic(d);result[kind]=io.static(dm,DEST+'/Display/SM_CombatShirtCarrier_'+kind,mats);del dm,d;gc.collect();u.SystemLibrary.collect_garbage()
file=Path(art['icon']['png']);task=u.AssetImportTask();task.filename=str(file);task.destination_path=DEST+'/Display';task.destination_name='T_CombatShirtCarrier_Icon';task.automated=True;task.replace_existing=True;task.save=False;A.import_asset_tasks([task]);texture=load(DEST+'/Display/T_CombatShirtCarrier_Icon')
for key,value in dict(srgb=True,compression_settings=u.TextureCompressionSettings.TC_EDITOR_ICON,lod_group=u.TextureGroup.TEXTUREGROUP_UI,mip_gen_settings=u.TextureMipGenSettings.TMGS_NO_MIPMAPS).items():texture.set_editor_property(key,value)
if not E.save_loaded_asset(texture,False):raise RuntimeError('UI texture save')
result.update(completed=True,texture=texture.get_path_name(),artwork_sha256=hashlib.sha256((R/'artwork.json').read_bytes()).hexdigest());(R/'artwork-saved.json').write_text(json.dumps(result,indent=2));print('TS01_COMBAT_ARTWORK_SAVED',flush=True)
