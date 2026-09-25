"""Publish saved asset paths into the existing item/save pipeline; no savegame mutation."""
import json, shutil
from pathlib import Path
from register_original_gloves import add_original_gloves
ROOT=Path('D:/FPS3D/FPSGAME')
SOURCE=ROOT/'SourceAssets/ModularOutfit20260924'
state=json.loads((SOURCE/'imported.json').read_text())
authored=json.loads((SOURCE/'authored.json').read_text())
if set(state['profiles'])!=set(authored):raise RuntimeError('Finish asset import before publishing recipes')
colors=[('ue_field_sweater','野行长袖上衣','armor','shirt','ShirtOlive'),
 ('ue_field_sweater_charcoal','炭灰长袖上衣','armor','shirt','ShirtCharcoal'),
 ('ue_field_gloves','棕革短手套','gloves','gloves','GlovesBrown'),
 ('ue_field_gloves_black','墨黑短手套','gloves','gloves','GlovesBlack')]
config={'version':1,'items':{},'profiles':{}}
previous_path=ROOT/'Content/ColdSteelData/modular_outfits.json'
previous=json.loads(previous_path.read_text(encoding='utf-8-sig')) if previous_path.exists() else {}
config['native_bare_hands_default']=previous.get('native_bare_hands_default',False)
for key,p in state['profiles'].items():
    config['profiles'][p['source']]={k:p[k] for k in ('base','shirt','gloves','hide_source_materials','shirt_covers','glove_covers')}
    config['profiles'][p['source']]['rig_profile']=key
    candidate=previous.get('profiles',{}).get(p['source'],{}).get('bare_arms_candidate')
    if candidate:config['profiles'][p['source']]['bare_arms_candidate']=candidate
native_path=SOURCE/'NativeSkin/saved.json'
if native_path.exists():
    native=json.loads(native_path.read_text())
    if set(state['profiles']).issubset(native):
        for key,p in state['profiles'].items():
            entry=native[key]
            if entry['source']!=p['source']:raise RuntimeError('Native skin source differs: '+key)
            profile=config['profiles'][p['source']]
            profile['base']=entry['mesh']
            profile['native_bare_skin']=entry['mesh']
            profile['shirt_covers']=entry['shirt_covers'];profile['glove_covers']=entry['glove_covers']
path=ROOT/'Content/ColdSteelData/items.json'
before=SOURCE/'items.before.json'
if not before.exists():shutil.copy2(path,before)
items=json.loads(path.read_text(encoding='utf-8-sig'))
for definition,name,slot,part,material in colors:
    config['items'][definition]={'slot':7 if slot=='armor' else 3,'part':part,'material':state['materials'][material],
        'rig_meshes':{key:p[part] for key,p in state['profiles'].items()}}
    items[definition]={'id':definition,'name':name,'category':'equipment','type':'上衣' if part=='shirt' else '手套',
        'equipSlot':slot,'rarity':'common','stack_max':1,'maxStack':1,'price':35 if part=='shirt' else 20,
        'grid_w':3 if part=='shirt' else 2,'grid_h':3 if part=='shirt' else 2,
        'desc':'厚实针织长袖，配有收口袖缘，可与短手套独立搭配。' if part=='shirt' else '贴合掌指的短款皮革手套，可与长袖上衣独立搭配。',
        'ue_icon':f'Icons/ModularOutfit20260924/{definition}.png','icon_fallback':'衣' if part=='shirt' else '手',
        'world_mesh':state['pickups'][part],'world_material':state['materials'][material]}
add_original_gloves(items,config)
path.write_text(json.dumps(items,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
(ROOT/'Content/ColdSteelData/modular_outfits.json').write_text(json.dumps(config,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('REGISTERED_OUTFITS',len(config['items']),'RIG_PROFILES',len(config['profiles']))
