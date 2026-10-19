"""Publish only the new ST6 pieces and the requested capri waist revision."""
import json,copy,shutil,importlib.util,hashlib
from pathlib import Path
P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/ST6LowerSet20261018';D=P/'Content/ColdSteelData'
spec=importlib.util.spec_from_file_location('st6_json_entries',str(P/'Tools/BrownLeatherSet/json_entries.py'));entries=importlib.util.module_from_spec(spec);spec.loader.exec_module(entries)
saved=json.loads((R/'saved_assets.json').read_text());models=saved['meshes']
if not saved.get('completed'):raise RuntimeError('ST6 assets have not finished saving')
for file,sha in saved.get('source_sha256',{}).items():
    if hashlib.sha256(Path(file).read_bytes()).hexdigest()!=sha:raise RuntimeError('Unsaved source: '+file)
paths=[D/'items.json',D/'modular_outfits.json'];raw=[p.read_bytes() for p in paths];text=[b.decode('utf-8-sig') for b in raw];catalog,config=[json.loads(t) for t in text]
native=json.loads((R/'native_reference.json').read_text());body=json.loads((D/'player_body.json').read_text(encoding='utf-8-sig'))
profile=config['profiles'][body['body_mesh']]
if profile.get('native_bare_skin',profile['base'])!=native['source']:raise RuntimeError('Native body changed while authoring; preserve this set for adaptation')
family='ST6LowerSet20261018'
items={};recipes={}
for key,name,slot,defense,price,label,desc in [
 ('ue_st6_tactical_pants','ST6 战术长裤','pants',10,42,'ST6Trousers','深灰防撕裂长裤，贴合腰围与收束裤腿，黑色嵌入式护膝配卡其包边。与硬壳手套、ST6 上衣及战术靴配套。'),
 ('ue_st6_tactical_boots','ST6 战术靴','boots',8,45,'ST6Boots','卡其皮革与深灰织物拼接战术靴，黑色护趾、后跟和踝部支撑，系带鞋面与防滑齿纹鞋底。')]:
    if key in config['items'] and config['items'][key].get('appearance_family')!=family:raise RuntimeError('Another definition owns '+key)
    item=dict(id=key,name=name,category='equipment',type='裤装' if slot=='pants' else '鞋靴',equipSlot=slot,stack_max=1,maxStack=1,price=price,grid_w=2,grid_h=3,defense={'base':defense},desc=desc,
        ue_icon='Icons/ST6LowerSet20261018/'+key+'.png',icon_fallback='裤' if slot=='pants' else '靴',world_mesh=models[label+'_pickup'],world_material='',ue_equipment_icon_mesh=models[label+'_icon'],ue_icon_pitch=0,ue_icon_yaw=-90 if slot=='pants' else 0)
    recipe=dict(slot=15 if slot=='pants' else 13,material='',appearance_family=family,rig_meshes={'Jason':models['SK_Jason_'+label]},rig_world_covers={'Jason':[8,10,12,14,16] if slot=='pants' else [4,11,13,15,16]})
    items[key]=item;recipes[key]=recipe
recipes['ue_st6_tactical_pants']['shoe_fit_meshes']={
    'ue_st6_tactical_boots':{'Jason':models['SK_Jason_ST6Trousers_ST6BootsFit']},
    'ue_boots':{'Jason':models['SK_Jason_ST6Trousers_ShortBootsFit']},
    'ue_armored_boots':{'Jason':models['SK_Jason_ST6Trousers_HighBootsFit']},
    'ue_leather_boots':{'Jason':models['SK_Jason_ST6Trousers_HighBootsFit']}}
capri=copy.deepcopy(config['items']['ue_smoke_grey_capri']);capri['appearance_family']='SmokeGreyCapriNativeWaistFit20261018';capri['rig_meshes']['Jason']=models['SK_Jason_CapriTailored']
for shoe in ('ue_armored_boots','ue_leather_boots','ue_st6_tactical_boots'):capri.setdefault('shoe_fit_meshes',{})[shoe]={'Jason':models['SK_Jason_CapriTailored_HighBootsFit']}
capri_item=copy.deepcopy(catalog['ue_smoke_grey_capri']);capri_item.update(world_mesh=models['CapriTailored_pickup'],ue_equipment_icon_mesh=models['CapriTailored_icon'],ue_icon='Icons/ST6LowerSet20261018/ue_smoke_grey_capri.png')
out_catalog,out_config=text
for key,item in items.items():
    out_catalog=entries.replace(out_catalog,[key],item) if key in catalog else entries.insert(out_catalog,[],key,item)
    out_config=entries.replace(out_config,['items',key],recipes[key]) if key in config['items'] else entries.insert(out_config,['items'],key,recipes[key])
out_catalog=entries.replace(out_catalog,['ue_smoke_grey_capri'],capri_item);out_config=entries.replace(out_config,['items','ue_smoke_grey_capri'],capri)
if any(p.read_bytes()!=b for p,b in zip(paths,raw)):raise RuntimeError('Catalog changed during publication; retry the scoped merge')
for path,before,content in zip(paths,raw,[out_catalog,out_config]):
    backup=R/'Before'/path.relative_to(P)
    if not backup.exists():backup.parent.mkdir(parents=True,exist_ok=True);backup.write_bytes(before)
    path.write_bytes((b'\xef\xbb\xbf' if before.startswith(b'\xef\xbb\xbf') else b'')+content.encode('utf-8'))
folder=D/'Icons/ST6LowerSet20261018';folder.mkdir(exist_ok=True)
for key in ('ue_st6_tactical_pants','ue_st6_tactical_boots','ue_smoke_grey_capri'):shutil.copy2(R/(key+'.png'),folder/(key+'.png'))
shutil.copy2(R/'ue_smoke_grey_capri.png',P/'SourceAssets/SmokeGreyCapri20261004/ue_smoke_grey_capri.png')
# Future capri re-saves and icon production retain this fitted source family.
capri_saved=P/'SourceAssets/SmokeGreyCapri20261004/saved_assets.json';data=json.loads(capri_saved.read_text());data.update(pants=models['SK_Jason_CapriTailored'],pants_high=models['SK_Jason_CapriTailored_HighBootsFit'],pants_icon=models['CapriTailored_icon'],pants_pickup=models['CapriTailored_pickup']);capri_saved.write_text(json.dumps(data,indent=2),encoding='utf-8')
entry=P/'Tools/SmokeGreyCapri/save_assets.py';source=entry.read_text()
if 'st6_current_capri_io' not in source:
    start=source.index('def main(reuse_materials=False):');end=source.index("if __name__=='__main__':",start)
    wrapper="""def main(reuse_materials=False):
    # NativeWaistFit20261018: save to the current, fitted capri package family.
    spec=importlib.util.spec_from_file_location('st6_current_capri_io',str(P/'Tools/ST6LowerSet/save_assets.py'))
    current=importlib.util.module_from_spec(spec);spec.loader.exec_module(current)
    current.save_capri()
"""
    entry.write_text(source[:start]+wrapper+source[end:],encoding='utf-8')
report=dict(completed=True,items=items,recipes=recipes,capri_recipe=capri,shared_with=['ue_hardknuckle_gloves','ue_st6_sleeves'],set_bonus_added=False,player_saves_changed=False,runtime_tested=False)
(R/'published.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print('ST6_LOWER_SET_AND_CAPRI_PUBLISHED',flush=True)
