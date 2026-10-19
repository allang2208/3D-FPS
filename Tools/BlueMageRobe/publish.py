"""Publish only this robe once its actual UE packages have been saved."""
import json,hashlib,shutil,importlib.util,copy
from pathlib import Path
P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/BlueMageRobe20261018';D=P/'Content/ColdSteelData';family='BlueMageRobe20261018';key='ue_blue_mage_robe'
spec=importlib.util.spec_from_file_location('robe_json_entries',str(P/'Tools/BrownLeatherSet/json_entries.py'));entries=importlib.util.module_from_spec(spec);spec.loader.exec_module(entries)
saved=json.loads((R/'saved_assets.json').read_text());editable=json.loads((R/'editable_receipt.json').read_text())
if not saved.get('completed'):raise RuntimeError('Robe packages are not fully saved')
paths=[D/'items.json',D/'modular_outfits.json'];raw=[p.read_bytes() for p in paths];texts=[b.decode('utf-8-sig') for b in raw];catalog,config=[json.loads(t) for t in texts]
profiles=list(dict.fromkeys(v['rig_profile'] for v in config['profiles'].values()));meshes={};owners={};aliases={}
for profile in profiles:
    group='Body' if profile in ('Body','Jason') else 'FP';route=group+'/'+profile;row=saved['saved'][route];source=R/'Authored'/group/(profile+'.json')
    if row['author_sha256']!=hashlib.sha256(source.read_bytes()).hexdigest():raise RuntimeError('Unpublished construction changes '+profile)
    asset=P/'Content'/(row['asset'].split('.')[0].removeprefix('/Game/')+'.uasset')
    if not asset.exists():raise RuntimeError('Missing saved package '+str(asset))
    meshes[profile]=row['asset'];aliases[profile]=[k for k,v in config['profiles'].items() if v['rig_profile']==profile]
    if group=='Body':owners[profile]=saved['saved']['Body/'+profile+'_Owner']['asset']
if key in config['items'] and config['items'][key].get('appearance_family')!=family:raise RuntimeError('Another garment definition owns this item')
item=dict(id=key,name='蓝色法师长袍',category='equipment',type='衣服',equipSlot='armor',stack_max=1,maxStack=1,price=45,grid_w=3,grid_h=4,defense={'base':6},desc='钴蓝织物长袍，贴合立领与收束袖口，深蓝腰带、浅银刺绣及蓝色领扣。连续裙摆带隐藏活动褶，行走时自然摆动。',ue_icon='Icons/'+family+'/'+key+'.png',icon_fallback='袍',world_mesh=saved['pickup'],world_material='',ue_equipment_icon_mesh=saved['icon'],ue_icon_pitch=0,ue_icon_yaw=-90)
recipe=copy.deepcopy(config['items'].get(key,{}))
recipe.update(slot=7,part='shirt',material='',appearance_family=family,cloth_simulation='blue_mage_robe_v1',rig_meshes=meshes,owner_body_meshes=owners,covers=[0,1,3],rig_world_covers={'Body':[1,3],'Jason':[0,1,3,7,8,9,10,14]})
if saved.get('underlayers'):
    # New equipment owns its additional inner-layer mappings. A robe re-save
    # must retain these, including the full boot and complete new trouser calves.
    underlayers=dict(saved['underlayers']);underlayers.update(recipe.get('underlayer_meshes',{}));recipe['underlayer_meshes']=underlayers
    recipe['leg_fit_revision']=saved['leg_fit_revision']
for revision in ('cloth_revision','hip_fit_revision'):
    if revision in saved:recipe[revision]=saved[revision]
out=[entries.replace(texts[0],[key],item) if key in catalog else entries.insert(texts[0],[],key,item),entries.replace(texts[1],['items',key],recipe) if key in config['items'] else entries.insert(texts[1],['items'],key,recipe)]
folder=D/'Icons'/family;folder.mkdir(exist_ok=True);shutil.copy2(R/(key+'.png'),folder/(key+'.png'))
shutil.copy2(R/(key+'.png'),D/'Icons'/(key+'.png'))
if any(p.read_bytes()!=b for p,b in zip(paths,raw)):raise RuntimeError('Catalog changed during scoped publication; retry')
for path,before,content in zip(paths,raw,out):path.write_bytes((b'\xef\xbb\xbf' if before.startswith(b'\xef\xbb\xbf') else b'')+content.encode('utf-8'))
report=dict(completed=True,item=item,recipe=recipe,profiles=profiles,aliases=aliases,skeletal_meshes=len(saved['saved']),cloth_bodies=list(owners),cloth_proxy_particles=1920,source_exports=editable['exports'],runtime_tested=False,editor_or_game_launched_for_acceptance=False)
(R/'published.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8');print('BLUE_MAGE_ROBE_PUBLISHED',len(profiles),'profiles',sum(map(len,aliases.values())),'registered sources')
