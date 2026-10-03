"""Register saved garments in the existing equipment and item catalog."""
import json
from pathlib import Path
P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/LowerBodyEquipment20261003';DATA=P/'Content/ColdSteelData'
saved=json.loads((R/'saved_assets.json').read_text());base=json.loads((R/'base_fitted.json').read_text())
names={'jeans':('ue_jeans','牛仔裤','pants','耐磨牛仔布长裤，保留洗水纹理、接缝和自然褶皱。',38),
       'cargo':('ue_cargo_pants','工装裤','pants','带立体侧袋的工装长裤，裤腿宽松，可与鞋靴独立搭配。',42),
       'sneakers':('ue_casual_sneakers','休闲鞋','boots','系带休闲鞋，布面鞋身与橡胶鞋底，可独立穿脱。',28)}
items={}
for key,(ident,name,slot,desc,price) in names.items():
    items[ident]={'id':ident,'name':name,'category':'equipment','type':'鞋靴' if slot=='boots' else '裤子',
        'equipSlot':slot,'rarity':'common','stack_max':1,'maxStack':1,'price':price,
        'grid_w':2,'grid_h':2 if slot=='boots' else 3,'desc':desc,
        'ue_icon':'Icons/'+ident+'.png','icon_fallback':'鞋' if slot=='boots' else '裤',
        'world_mesh':saved[key+'_pickup'],'world_material':'','ue_equipment_icon_mesh':saved[key+'_icon_mesh']}
    if key=='sneakers':items[ident].update(ue_icon_pitch=-18,ue_icon_yaw=-60)
# Insert only these definitions; retain the large catalog's original formatting.
path=DATA/'items.json';raw=path.read_bytes();current=json.loads(raw.decode('utf-8-sig'))
if any(k in current for k in items):raise RuntimeError('Definitions already published; update them deliberately.')
backup=R/'items_before_lower_body.json'
if not backup.exists():backup.write_bytes(raw)
offset=raw.index(b'{')+1
entries=json.dumps(items,ensure_ascii=False,indent=2)[1:-1].strip('\n').encode('utf-8')
path.write_bytes(raw[:offset]+b'\n'+entries+b','+raw[offset:])

path=DATA/'modular_outfits.json';raw=path.read_bytes();config=json.loads(raw.decode('utf-8-sig'))
backup=R/'modular_outfits_before_lower_body.json'
if not backup.exists():backup.write_bytes(raw)
for key,(ident,*_) in names.items():
    config['items'][ident]={'slot':13 if key=='sneakers' else 15,
        'rig_meshes':{'Jason':saved[key]},'rig_world_covers':{'Jason':base['covers'][key]}}
# Use the new sectioned follower on the active Jason source; leave body setup,
# animation, root offsets and weapon viewmodels under their existing ownership.
profile=config['profiles'][base['source']]
profile['base']=saved['base'];profile['native_bare_skin']=saved['base']
def expanded(values):
    return list(dict.fromkeys(values+[int(n) for n,old in base['section_origins'].items() if old in values]))
profile['shirt_covers']=expanded(profile.get('shirt_covers',[]))
for recipe in config['items'].values():
    coverage=recipe.get('rig_world_covers',{})
    if 'Jason' in coverage and recipe.get('slot') not in (13,15):
        coverage['Jason']=expanded(coverage['Jason'])
    elif recipe.get('slot')==7:
        old=recipe.get('world_covers',recipe.get('covers',profile['shirt_covers']))
        recipe.setdefault('rig_world_covers',{})['Jason']=expanded(old)
path.write_text(json.dumps(config,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
(R/'published_items.json').write_text(json.dumps(items,ensure_ascii=False,indent=2),encoding='utf-8')
print('LOWER_BODY_CATALOG_PUBLISHED',','.join(items),flush=True)
