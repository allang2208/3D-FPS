"""Register saved Boots equipment without changing inventory instance state."""
import json
from pathlib import Path

P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/BootsEquipment20261004';DATA=P/'Content/ColdSteelData'
saved=json.loads((R/'saved_assets.json').read_text())
base=json.loads((R/'base_fitted.json').read_text())
profile=json.loads((R/'profile.json').read_text())
item={'id':'ue_boots','name':'系带皮靴','category':'equipment','type':'鞋靴','equipSlot':'boots',
      'rarity':'common','stack_max':1,'maxStack':1,'price':45,'grid_w':2,'grid_h':2,
      'desc':'为日常行走制作的系带皮靴，靴筒包覆脚踝，厚底与皮革拼接保留自然褶皱。可与长裤搭配，独立穿脱。',
      'ue_icon':'Icons/ue_boots.png','icon_fallback':'靴','world_mesh':saved['pickup'],'world_material':'',
      'ue_equipment_icon_mesh':saved['icon'],'ue_icon_pitch':0,'ue_icon_yaw':0}

path=DATA/'items.json';raw=path.read_bytes();current=json.loads(raw.decode('utf-8-sig'))
if 'ue_boots' in current:raise RuntimeError('ue_boots already exists; update the published definition deliberately')
backup=R/'items_before_boots.json'
if not backup.exists():backup.write_bytes(raw)
offset=raw.index(b'{')+1
entry=json.dumps({'ue_boots':item},ensure_ascii=False,indent=2)[1:-1].strip('\n').encode('utf-8')

outfit_path=DATA/'modular_outfits.json';outfit_raw=outfit_path.read_bytes()
config=json.loads(outfit_raw.decode('utf-8-sig'))
active=config['profiles'][profile['profile_key']]
if active['base']!=profile['previous_base']:raise RuntimeError('The active body base changed during Boots authoring')
backup=R/'modular_outfits_before_boots.json'
if not backup.exists():backup.write_bytes(outfit_raw)
def expand(values):
    return list(dict.fromkeys(values+[int(section) for section,parent in base['section_origins'].items() if parent in values]))
for recipe in config['items'].values():
    coverage=recipe.get('rig_world_covers',{})
    if 'Jason' in coverage:coverage['Jason']=expand(coverage['Jason'])
active['base']=saved['base'];active['native_bare_skin']=saved['base']
active['shirt_covers']=expand(active.get('shirt_covers',[]))
active['glove_covers']=expand(active.get('glove_covers',[]))
config['items']['ue_boots']={'slot':13,'rig_meshes':{'Jason':saved['boots']},'rig_world_covers':{'Jason':base['boots_covers']}}
for key,definition in [('jeans','ue_jeans'),('cargo','ue_cargo_pants')]:
    config['items'][definition].setdefault('shoe_fit_meshes',{})['ue_boots']={'Jason':saved[key]}
outfit_path.write_text(json.dumps(config,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
path.write_bytes(raw[:offset]+b'\n'+entry+b','+raw[offset:])
(R/'published_item.json').write_text(json.dumps(item,ensure_ascii=False,indent=2),encoding='utf-8')
print('BOOTS_CATALOG_PUBLISHED ue_boots',flush=True)
