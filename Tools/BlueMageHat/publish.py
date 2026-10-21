"""Publish the saved hat into the shared inventory and body configuration."""
import json,shutil,importlib.util
from pathlib import Path
P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/BlueMageHat20261019';D=P/'Content/ColdSteelData';key='ue_blue_mage_hat';family='BlueMageHat20261019'
spec=importlib.util.spec_from_file_location('hat_json_entries',str(P/'Tools/BrownLeatherSet/json_entries.py'));entries=importlib.util.module_from_spec(spec);spec.loader.exec_module(entries)
saved=json.loads((R/'saved_assets.json').read_text())
if not saved.get('completed'):raise RuntimeError('Hat packages have not all been saved')
paths=[D/'items.json',D/'player_body.json'];raw=[p.read_bytes() for p in paths];texts=[b.decode('utf-8-sig') for b in raw];catalog,config=[json.loads(t) for t in texts]
item=dict(id=key,name='蓝色尖顶法师帽',category='equipment',type='头部装备',equipSlot='helmet',stack_max=1,maxStack=1,price=30,grid_w=2,grid_h=2,defense={'base':3},desc='钴蓝织物尖顶帽，深蓝帽带、银色星纹和蓝宝石帽扣，与蓝色法师长袍配套。柔软帽尖随动作轻摆回弹。',ue_icon='Icons/'+family+'/'+key+'.png',icon_fallback='帽',world_mesh=saved['pickup'],world_material='',ue_equipment_icon_mesh=saved['icon'],ue_icon_pitch=0,ue_icon_yaw=-90)
recipe=dict(skeletal_mesh=saved['mesh'],attach_bone='head',fits=saved['fit'],tip_bones=saved['tip_bones'],tip_limit_degrees=10.,tip_frequency_hz=2.5,tip_damping=.6,covers_scalp_hair=True)
out=[entries.replace(texts[0],[key],item) if key in catalog else entries.insert(texts[0],[],key,item)]
if 'head_equipment' not in config:out.append(entries.insert(texts[1],[],'head_equipment',{key:recipe}))
elif key in config['head_equipment']:out.append(entries.replace(texts[1],['head_equipment',key],recipe))
elif config['head_equipment']:out.append(entries.insert(texts[1],['head_equipment'],key,recipe))
else:out.append(entries.replace(texts[1],['head_equipment'],{key:recipe}))
folder=D/'Icons'/family;folder.mkdir(parents=True,exist_ok=True);shutil.copy2(R/(key+'.png'),folder/(key+'.png'))
shutil.copy2(R/(key+'.png'),D/'Icons'/(key+'.png'))
if any(p.read_bytes()!=b for p,b in zip(paths,raw)):raise RuntimeError('Catalog changed during scoped publication; retry')
for path,before,content in zip(paths,raw,out):
    if path.name == 'player_body.json':
        entries.commit_player_body(path,before,content,owned_paths=[('head_equipment',key)],producer=__file__)
    else:
        path.write_bytes((b'\xef\xbb\xbf' if before.startswith(b'\xef\xbb\xbf') else b'')+content.encode('utf-8'))
(R/'published.json').write_text(json.dumps(dict(completed=True,item=item,recipe=recipe,slot=1,all_weapon_branches='shared player body head attachment',runtime_tested=False),ensure_ascii=False,indent=2),encoding='utf-8')
print('BLUE_MAGE_HAT_PUBLISHED slot=1')
