"""Publish only selected V3 trousers, matching shirt pair and robe mappings."""
import copy,hashlib,shutil,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
from integration_common import *
sys.path.insert(0,str(P/'Tools/BrownLeatherSet'))
from json_entries import replace
saved=read(R/'saved_assets.json');authored=read(R/'authored.json');baseline=read(R/'baseline.json')
if not saved.get('completed'):raise RuntimeError('Complete actual mesh/material/display saves first')
for row in authored['records']:
    sha=hashlib.sha256(Path(row['file']).read_bytes()).hexdigest()
    if saved['saved'][row['item']+'/'+row['profile']]['author_sha256']!=sha:raise RuntimeError('Unsaved authoring '+row['profile'])
paths=[P/'Content/ColdSteelData/modular_outfits.json',P/'Content/ColdSteelData/items.json']
raw=[p.read_bytes() for p in paths];texts=[b.decode('utf-8-sig') for b in raw];cfg,catalog=[__import__('json').loads(t) for t in texts]
pants=copy.deepcopy(cfg['items']['ue_leather_pants']);old=baseline['items']['ue_leather_pants']
def asset(item,profile):return saved['saved'][item+'/'+profile]['asset']
route={old['rig_meshes']['Jason']:asset('ue_leather_pants','Jason')}
for shoe in old.get('shoe_fit_meshes',{}):
    profile='Jason_ShortBootsFit' if shoe=='ue_boots' else 'Jason_HighBootsFit'
    route[old['shoe_fit_meshes'][shoe]['Jason']]=asset('ue_leather_pants',profile)
def resolve(path):
    if path in route:return route[path]
    if path in route.values():return path
    raise RuntimeError('Pants route changed during integration: '+path)
pants['rig_meshes']['Jason']=resolve(pants['rig_meshes']['Jason'])
for shoe,rigs in pants.get('shoe_fit_meshes',{}).items():
    if 'Jason' in rigs:rigs['Jason']=resolve(rigs['Jason'])
pants['appearance_family']='RangerLeatherPantsRealisticCutV3_20261022'
shirt=copy.deepcopy(cfg['items']['ue_field_sweater']);base_shirt=baseline['items']['ue_field_sweater']
pair=dict(rig_meshes={'Jason':asset('ue_field_sweater','Jason')},owner_body_meshes={'Jason':asset('ue_field_sweater','Owner_Jason')})
current=shirt.get('pants_fit_meshes',{}).get('ue_leather_pants')
if current not in (base_shirt.get('pants_fit_meshes',{}).get('ue_leather_pants'),pair):raise RuntimeError('Shirt pairing changed during integration')
for field in ('rig_meshes','owner_body_meshes'):
    if shirt[field]['Jason']!=base_shirt[field]['Jason']:raise RuntimeError('Shirt source changed during integration')
shirt.setdefault('pants_fit_meshes',{})['ue_leather_pants']=pair
robe=copy.deepcopy(cfg['items']['ue_blue_mage_robe']);under=robe.setdefault('underlayer_meshes',{})
for profile in PROFILES:
    key=asset('ue_leather_pants',profile);value=asset('ue_leather_pants',profile+'_RobeInner')
    if key in under and under[key]!=value:raise RuntimeError('Conflicting new robe pairing')
    under[key]=value
definition=copy.deepcopy(catalog['ue_leather_pants'])
for k in ('world_mesh','ue_equipment_icon_mesh','ue_icon'):
    if definition.get(k)!=baseline['definition'].get(k) and not str(definition.get(k)).startswith(DEST) and not str(definition.get(k)).startswith('Icons/RangerLeatherPantsRealisticCutV3/'):raise RuntimeError('Display routing changed during integration')
definition.update(world_mesh=saved['displays']['pickup'],ue_equipment_icon_mesh=saved['displays']['icon'],ue_icon='Icons/RangerLeatherPantsRealisticCutV3/ue_leather_pants.png',desc='胡桃棕皮革与橄榄色活动布片拼接的野外长裤，膝窝和内腿留有活动余量，斜插袋、腰带及收口裤脚便于携行。')
for key,recipe in [('ue_leather_pants',pants),('ue_field_sweater',shirt),('ue_blue_mage_robe',robe)]:texts[0]=replace(texts[0],['items',key],recipe)
texts[1]=replace(texts[1],['ue_leather_pants'],definition)
icon=P/'Content/ColdSteelData'/definition['ue_icon'];icon.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(R/'ue_leather_pants.png',icon)
if any(p.read_bytes()!=b for p,b in zip(paths,raw)):raise RuntimeError('Catalog changed during scoped publication; retry')
for p,b,t in zip(paths,raw,texts):
    before=R/'Before'/p.name
    if not before.exists():before.parent.mkdir(parents=True,exist_ok=True);before.write_bytes(b)
    p.write_bytes((b'\xef\xbb\xbf' if b.startswith(b'\xef\xbb\xbf') else b'')+t.encode('utf-8'))
write(R/'published.json',dict(completed=True,revision='RealisticCutV3',item='ue_leather_pants',route=route,shirt_pair=pair,robe_mappings={asset('ue_leather_pants',p):asset('ue_leather_pants',p+'_RobeInner') for p in PROFILES},definition=definition,runtime_tested=False))
latest=read(SOURCE.parent/'latest_revision.json');latest.update(status='Saved UE wearables, PBR, displays and icon; equipment routes integrated; runtime acceptance pending',ue_imported=True,integration=str(R),runtime_tested=False);write(SOURCE.parent/'latest_revision.json',latest)
print('RANGER_V3_INTEGRATED regular / short boots / high boots / robe / paired shirt / pickup / inventory',flush=True)
