"""Scoped publication of the saved blue mage glove item and native routes."""
import json,shutil,importlib.util
from pathlib import Path
P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/BlueMageGloves20261019';D=P/'Content/ColdSteelData';key='ue_blue_mage_gloves';family='BlueMageGloves20261019'
spec=importlib.util.spec_from_file_location('mage_glove_entries',str(P/'Tools/BrownLeatherSet/json_entries.py'));entries=importlib.util.module_from_spec(spec);spec.loader.exec_module(entries)
saved=json.loads((R/'saved_assets.json').read_text());editable=json.loads((R/'editable_receipt.json').read_text())
if not saved.get('completed') or not editable.get('completed'):raise RuntimeError('Production sources and saved assets must be complete')
paths=[D/'items.json',D/'modular_outfits.json'];raw=[p.read_bytes() for p in paths];texts=[b.decode('utf-8-sig') for b in raw];items,config=[json.loads(t) for t in texts]
profiles=list(dict.fromkeys(v['rig_profile'] for v in config['profiles'].values()));meshes={profile:saved['profiles'][profile]['asset'] for profile in profiles}
item=dict(items['ue_field_gloves_black']);item.update(id=key,name='蓝色法师手套',type='手套',equipSlot='gloves',desc='蓝色织物与深蓝薄皮拼接的全指手套，手背饰银色星纹和藤纹，腕口收束并带低矮蓝宝石扣。掌心与指腹保持柔软，便于施法和握持。',ue_icon='Icons/'+family+'/'+key+'.png',icon_fallback='套',world_mesh=saved['pickup'],world_material='',ue_equipment_icon_mesh=saved['icon'],ue_icon_pitch=0,ue_icon_yaw=0)
for field in ('rarity','grade'):item.pop(field,None)
recipe=dict(config['items']['ue_field_gloves_black'],rig_meshes=meshes,material='',appearance_family=family)
out=[entries.replace(texts[0],[key],item) if key in items else entries.insert(texts[0],[],key,item),entries.replace(texts[1],['items',key],recipe) if key in config['items'] else entries.insert(texts[1],['items'],key,recipe)]
folder=D/'Icons'/family;folder.mkdir(parents=True,exist_ok=True);shutil.copy2(R/(key+'.png'),folder/(key+'.png'))
shutil.copy2(R/(key+'.png'),D/'Icons'/(key+'.png'))
if any(p.read_bytes()!=b for p,b in zip(paths,raw)):raise RuntimeError('Shared catalog changed; retry scoped publication')
for path,before,content in zip(paths,raw,out):path.write_bytes((b'\xef\xbb\xbf' if before.startswith(b'\xef\xbb\xbf') else b'')+content.encode('utf-8'))
(R/'published.json').write_text(json.dumps(dict(completed=True,item=item,recipe=recipe,profile_count=len(profiles),registered_sources=sum(len(row['aliases']) for row in saved['profiles'].values()),new_animations=0,runtime_tested=False),ensure_ascii=False,indent=2),encoding='utf-8');print('BLUE_MAGE_GLOVES_PUBLISHED',len(profiles),'profiles')
