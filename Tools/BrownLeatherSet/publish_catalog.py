"""Publish two new leather items and scoped shoe-fit mappings after asset save."""
import copy,json
from pathlib import Path
from json_entries import insert,replace
P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/BrownLeatherSet20261004';D=P/'Content/ColdSteelData'
saved=json.loads((R/'saved_assets.json').read_text(encoding='utf-8'));context=json.loads((R/'source_context.json').read_text(encoding='utf-8'))
paths=[D/'items.json',D/'modular_outfits.json'];raw=[p.read_bytes() for p in paths];texts=[x.decode('utf-8-sig') for x in raw]
catalog,config=[json.loads(x) for x in texts]
if config['profiles'][context['profile_key']]['base']!=context['base']:raise RuntimeError('Active body base changed; retain new assets and rebase the coverage mapping before publication')
if config['items']['ue_armored_boots']['rig_world_covers']['Jason']!=context['boot_covers']:raise RuntimeError('High boot coverage changed during production')
for key in ['ue_leather_boots','ue_leather_pants']:
    if key in catalog or key in config['items']:raise RuntimeError(key+' already exists; do not overwrite its definition')
items={};recipes={}
for key,definition,name,slot,defense,price,description in [
    ('boots','ue_leather_boots','棕色皮革靴','boots',12,55,'暖棕皮革高筒靴，皮革包头与加固后跟配双侧扣，沿条和靴口保留细缝线。与棕色露指皮革手套、皮革裤组成同款外观。'),
    ('pants','ue_leather_pants','棕色皮革裤','pants',20,50,'分片裁剪的棕色皮革长裤，弧形拼缝、柔性护膝、腰带和收窄裤脚保留自然褶皱。可搭配同套皮革靴及露指手套。')]:
    items[definition]=dict(id=definition,name=name,category='equipment',type='鞋靴' if key=='boots' else '裤装',equipSlot=slot,
        rarity='common',stack_max=1,maxStack=1,price=price,grid_w=2,grid_h=3,defense={'base':defense},desc=description,
        ue_icon='Icons/'+definition+'.png',icon_fallback='靴' if key=='boots' else '裤',world_mesh=saved[key+'_pickup'],world_material='',
        ue_equipment_icon_mesh=saved[key+'_icon'],ue_icon_pitch=0,ue_icon_yaw=0 if key=='boots' else -90)
    recipes[definition]=dict(slot=13 if key=='boots' else 15,material='',appearance_family='BrownLeather'+key.title()+'20261004',
        rig_meshes={'Jason':saved[key]},rig_world_covers={'Jason':context['boot_covers'] if key=='boots' else context['pants_covers']})
recipes['ue_leather_pants']['shoe_fit_meshes']={
    'ue_boots':{'Jason':saved['pants_short']},'ue_armored_boots':{'Jason':saved['pants_high']},'ue_leather_boots':{'Jason':saved['pants_high']}}
output_catalog,output_config=texts
for key in ['ue_leather_boots','ue_leather_pants']:
    output_catalog=insert(output_catalog,[],key,items[key]);output_config=insert(output_config,['items'],key,recipes[key])
for definition,old_fit in context['inherited_fits'].items():
    current=config['items'][definition]
    if current['shoe_fit_meshes']['ue_armored_boots']!=old_fit:raise RuntimeError('Existing trouser fit changed: '+definition)
    updated=copy.deepcopy(current);updated['shoe_fit_meshes']['ue_leather_boots']=copy.deepcopy(old_fit)
    output_config=replace(output_config,['items',definition],updated)
if any(p.read_bytes()!=before for p,before in zip(paths,raw)):raise RuntimeError('Catalog changed during publication; no writes made')
for path,before,text in zip(paths,raw,[output_catalog,output_config]):
    backup=R/(path.stem+'-before.json')
    if not backup.exists():backup.write_bytes(before)
    prefix=b'\xef\xbb\xbf' if before.startswith(b'\xef\xbb\xbf') else b'';path.write_bytes(prefix+text.encode('utf-8'))
(R/'published.json').write_text(json.dumps(dict(items=items,recipes=recipes,existing_fits_updated=list(context['inherited_fits']),
    matching_glove='ue_field_gloves',glove_changed=False,player_saves_changed=False,runtime_tested=False),ensure_ascii=False,indent=2),encoding='utf-8')
print('BROWN_LEATHER_CATALOG_PUBLISHED ue_leather_boots ue_leather_pants',flush=True)
