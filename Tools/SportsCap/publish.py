"""Register the saved sports cap only; leave the four outfit items and set bonuses alone."""
import hashlib
import json
import os
import runpy
import shutil
import sys
import uuid
from pathlib import Path

P=Path(__file__).resolve().parents[2];R=P/'SourceAssets/SportsCap20261024';D=P/'Content/ColdSteelData';KEY='ue_charcoal_sports_cap'
sys.path.insert(0,str(P/'Tools/BrownLeatherSet'))
import json_entries as entries

def read(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()

saved=read(R/'saved_assets.json');delivery=read(R/'delivery.json');fits=read(R/'fit_candidate.json')['variants']
if not saved.get('completed'):raise RuntimeError('Complete the actual UE asset saves first')
for row in delivery['records']:
    if saved['wear'][row['body']]['lod_source_hashes']!=[sha(v['file']) for v in row['lods']]:raise RuntimeError('A source LOD changed after save: '+row['body'])
if saved['icon_sha256']!=sha(R/(KEY+'.png')):raise RuntimeError('Save the current inventory texture first')
paths=[v['asset'] for v in saved['wear'].values()]+[saved['pickup']['asset'],saved['icon']['asset'],saved['icon_texture']]+saved['materials']+list(saved['textures'].values())
for asset in paths:
    if not (P/'Content'/(asset.split('.')[0][6:]+'.uasset')).exists():raise RuntimeError('Missing saved package: '+asset)
catalog_path=D/'items.json';body_path=D/'player_body.json';raw=catalog_path.read_bytes();body_raw=body_path.read_bytes()
catalog=json.loads(raw.decode('utf-8-sig'));body=json.loads(body_raw.decode('utf-8-sig'))
if KEY in catalog and catalog[KEY].get('world_mesh')!=saved['pickup']['asset']:raise RuntimeError('Existing sports cap definition has a different source; preserve it')
item=dict(id=KEY,name='炭灰运动帽',category='equipment',type='头部装备',equipSlot='helmet',stack_max=1,maxStack=1,price=25,grid_w=2,grid_h=2,defense=dict(base=2,perEnhance=.4),
          desc='以炭灰尼龙裁片缝制的轻便运动帽，短弧檐遮挡日光，侧面透气孔、内汗带与后部调节织带适合日常奔走。细蓝包边和银色反光片增强辨识，柔软帽体仅提供有限防护。',
          ue_icon='Icons/SportsCap20261024/'+KEY+'.png',icon_fallback='帽',world_mesh=saved['pickup']['asset'],world_material='',ue_equipment_icon_mesh='',ue_icon_pitch=0,ue_icon_yaw=-90,ue_icon_roll=0)
recipes={}
for name,profile in (('jason','Jason'),('kaitlin','Kaitlin')):
    recipe=dict(static_mesh=saved['wear'][profile]['asset'],attach_bone='head',fits={name:fits[name]['fit']},covers_scalp_hair=False)
    target=body if name=='jason' else body['body_variants'][name]
    current=target.get('head_equipment',{}).get(KEY)
    if current and current!=recipe:raise RuntimeError('Sports cap mount changed concurrently: '+name)
    target.setdefault('head_equipment',{})[KEY]=recipe;recipes[name]=recipe
before=R/'Before';before.mkdir(exist_ok=True)
for name,data in (('items.json',raw),('player_body.json',body_raw)):
    if not (before/name).exists():(before/name).write_bytes(data)
for target in (D/item['ue_icon'],D/'Icons'/(KEY+'.png')):
    target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(R/(KEY+'.png'),target)
commit=runpy.run_path(str(P/'Tools/PlayerBody/config_transaction.py'))['commit']
body_receipt=commit(body_path,body_raw,body,owned_paths=[('head_equipment',KEY),('body_variants','kaitlin','head_equipment',KEY)],producer=__file__)
text=entries.replace(raw.decode('utf-8-sig'),[KEY],item) if KEY in catalog else entries.insert(raw.decode('utf-8-sig'),[],KEY,item)
if catalog_path.read_bytes()!=raw:raise RuntimeError('Catalog changed; merge again from current contents')
temp=catalog_path.with_name('items.sports-cap-'+uuid.uuid4().hex+'.tmp');temp.write_bytes((b'\xef\xbb\xbf' if raw.startswith(b'\xef\xbb\xbf') else b'')+text.encode('utf-8'))
if catalog_path.read_bytes()!=raw:raise RuntimeError('Concurrent catalog writer; preserving current catalog')
os.replace(temp,catalog_path)
report=dict(completed=True,item=item,recipes=recipes,body_config=body_receipt,saved_asset_root='/Game/Characters/ModularOutfit20260924/SportsCap20261024',
            authored_lods_preserved=True,other_items_changed=False,set_bonus_added=False,game_integrated=True,runtime_tested=False,
            developer_menu=['装备','头部装备','炭灰运动帽'],configuration_load='Next game instance / player BeginPlay',git_commit=None,git_push=None)
(R/'published.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('SPORTS_CAP_PUBLISHED',KEY,'Jason + Kaitlin; set bonuses unchanged',flush=True)
