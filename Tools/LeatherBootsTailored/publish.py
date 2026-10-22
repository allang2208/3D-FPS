"""Publish the upgraded boot only; preserve gameplay values and every pants route."""
import copy,hashlib,json,shutil,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent));from boot_paths import *
sys.path.insert(0,str(P/'Tools/BrownLeatherSet'));from json_entries import replace
saved=read(R/'saved_assets.json');before=read(R/'inputs.json');check=read(R/'saved_check.json')
if not saved.get('completed') or not check.get('completed'):raise RuntimeError('Complete saved-asset checks before publication')
for profile in ('Jason','Jason_RobeInner'):
    author=R/'Authored/ue_leather_boots'/(profile+'.json')
    if saved['saved']['ue_leather_boots/'+profile]['author_sha256']!=hashlib.sha256(author.read_bytes()).hexdigest():raise RuntimeError('Unsaved author '+profile)
paths=[P/'Content/ColdSteelData/modular_outfits.json',P/'Content/ColdSteelData/items.json'];raw=[p.read_bytes() for p in paths];texts=[b.decode('utf-8-sig') for b in raw];cfg,catalog=[json.loads(t) for t in texts]
boot=copy.deepcopy(cfg['items']['ue_leather_boots']);new=saved['saved']['ue_leather_boots/Jason']['asset'];inner=saved['saved']['ue_leather_boots/Jason_RobeInner']['asset']
if boot['rig_meshes']['Jason'] not in (before['source_asset'],new):raise RuntimeError('Boot route changed during authoring')
boot['rig_meshes']['Jason']=new;boot['appearance_family']='LeatherBootsTailoredV2'
robe=copy.deepcopy(cfg['items']['ue_blue_mage_robe']);mapping=robe.setdefault('underlayer_meshes',{})
if new in mapping and mapping[new]!=inner:raise RuntimeError('Conflicting robe mapping')
mapping[new]=inner
definition=copy.deepcopy(catalog['ue_leather_boots'])
for k in ('world_mesh','ue_equipment_icon_mesh','ue_icon'):
    if definition.get(k)!=before['definition'].get(k) and not str(definition.get(k)).startswith((DEST,'Icons/LeatherBootsTailoredV2/')):raise RuntimeError('Display route changed during authoring')
definition.update(world_mesh=saved['displays']['pickup'],ue_equipment_icon_mesh=saved['displays']['icon'],ue_icon='Icons/LeatherBootsTailoredV2/ue_leather_boots.png',desc='深胡桃棕皮革长靴，弧形裁片和斜向活动褶自然衔接脚踝，暗钢双扣带、卷边内衬与细密双缝线配合叠层皮跟和沿条。')
for key,value in [('ue_leather_boots',boot),('ue_blue_mage_robe',robe)]:texts[0]=replace(texts[0],['items',key],value)
texts[1]=replace(texts[1],['ue_leather_boots'],definition)
updated=json.loads(texts[0]);catalog_after=json.loads(texts[1])
for item,row in cfg['items'].items():
    if item not in ('ue_leather_boots','ue_blue_mage_robe') and updated['items'][item]!=row:raise RuntimeError('Unrelated item mutation '+item)
for k,v in catalog['ue_leather_boots'].items():
    if k not in ('world_mesh','ue_equipment_icon_mesh','ue_icon','desc') and catalog_after['ue_leather_boots'][k]!=v:raise RuntimeError('Gameplay mutation '+k)
icon=P/'Content/ColdSteelData'/definition['ue_icon'];icon.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(R/'ue_leather_boots.png',icon)
if any(p.read_bytes()!=b for p,b in zip(paths,raw)):raise RuntimeError('Catalog changed during scoped publication; retry')
for p,b,t in zip(paths,raw,texts):
    backup=R/'Before'/p.name
    if not backup.exists():backup.parent.mkdir(parents=True,exist_ok=True);backup.write_bytes(b)
    p.write_bytes((b'\xef\xbb\xbf' if b.startswith(b'\xef\xbb\xbf') else b'')+t.encode('utf-8'))
write(R/'published.json',dict(completed=True,item='ue_leather_boots',mesh=new,robe_inner=inner,definition=definition,pants_routes_preserved=True,gameplay_values_preserved=True,runtime_tested=False))
write(R/'delivery.json',dict(completed=True,item='ue_leather_boots',revision='TailoredV2',root_cause='The prior revision joined the sole but retained a separately capped calf tube intersecting the upper. This produced a visible ankle cut and discontinuous shading.',reference=str(OLD/'LeatherBoots_Concept_v1.png'),changes=['One continuous outer upper from the sole through the ankle to the cuff; joined rim, inner lining and footbed','Curving quarter-panel seams, localized oblique leather folds, rounded anatomical toe and stacked leather heel','Darker walnut leather with coordinated patina/roughness, smoother grain, and aged solid buckle frames','Native skeleton and equipment attributes retained; geometry reconstructed'],sources=dict(blend=str(R/'LeatherBoots_Continuous_Editable.blend'),fbx=str(R/'Exports/Jason_LeatherBoots_Continuous.fbx')),geometry=read(R/'model_check.json')['source'],checks=dict(model=read(R/'model_check.json'),saved_ue=check,visual_review=dict(reviewer='assistant',scope='Blender Cycles render of actual geometry; single concept is a visual reference, not a dimensional reconstruction',views=['Boots_Detail.png','Boots_Back.png','Boots_Inner.png','Sole_Welt_Close.png','Ankle_Toe_Flex_Check.png'],runtime_tested=False)),assets=dict(wearable=new,robe_inner=inner,displays=saved['displays'],icon_texture=saved['icon_texture']),runtime_tested=False))
print('LEATHER_BOOTS_PUBLISHED wearable / robe inner / pickup / inventory',flush=True)
delivery=read(R/'delivery.json');delivery['checks']['current_trouser_hem_envelopes']=read(R/'trouser_fit_check.json');write(R/'delivery.json',delivery)
