"""Publish the approved trousers and only their four robe-underlayer mappings."""
from common import *
import copy,hashlib,shutil
saved=read(R/'saved_assets.json');editable=read(R/'editable_receipt.json')
if not saved.get('completed') or not editable.get('completed'):raise RuntimeError('Complete asset saving and editable exports before publication')
for file,sha in saved.get('source_sha256',{}).items():
    if hashlib.sha256(Path(file).read_bytes()).hexdigest()!=sha:raise RuntimeError('Source changed since saving: '+file)
models=saved['meshes'];entries=module('mage_pants_json_entries','Tools/BrownLeatherSet/json_entries.py');D=P/'Content/ColdSteelData';paths=[D/'items.json',D/'modular_outfits.json'];raw=[p.read_bytes() for p in paths];texts=[b.decode('utf-8-sig') for b in raw];catalog,config=[json.loads(t) for t in texts]
native=read(R/'native_reference.json');body=read(D/'player_body.json');profile=config['profiles'][body['body_mesh']]
if profile.get('native_bare_skin',profile['base'])!=native['source']:raise RuntimeError('Native body changed during authoring; retain assets for adaptation')
if KEY in config['items'] and config['items'][KEY].get('appearance_family')!=FAMILY:raise RuntimeError('Another definition owns this equipment key')
item=copy.deepcopy(ITEM);item.update(world_mesh=saved['pickup'],ue_equipment_icon_mesh=saved['icon'])
recipe=dict(slot=15,material='',appearance_family=FAMILY,rig_meshes={'Jason':models['SK_'+VARIANTS[0]]},rig_world_covers={'Jason':[8,10,12,14,16]},shoe_fit_meshes={})
for shoe,index in [('ue_boots',1),('ue_armored_boots',2),('ue_leather_boots',2),('ue_st6_tactical_boots',3)]:recipe['shoe_fit_meshes'][shoe]={'Jason':models['SK_'+VARIANTS[index]]}
if 'ue_blue_mage_boots' in config['items']:recipe['shoe_fit_meshes']['ue_blue_mage_boots']={'Jason':models['SK_'+VARIANTS[2]]}
out_catalog=entries.replace(texts[0],[KEY],item) if KEY in catalog else entries.insert(texts[0],[],KEY,item)
out_config=entries.replace(texts[1],['items',KEY],recipe) if KEY in config['items'] else entries.insert(texts[1],['items'],KEY,recipe)
underlayers=copy.deepcopy(config['items']['ue_blue_mage_robe']['underlayer_meshes']);added={models['SK_'+n]:models['SK_'+n+'_RobeInner'] for n in VARIANTS};underlayers.update(added)
out_config=entries.replace(out_config,['items','ue_blue_mage_robe','underlayer_meshes'],underlayers)
if any(path.read_bytes()!=before for path,before in zip(paths,raw)):raise RuntimeError('Catalog changed during publication; retry the scoped merge')
for path,before,content in zip(paths,raw,[out_catalog,out_config]):
    backup=R/'Before'/path.relative_to(P)
    if not backup.exists():backup.parent.mkdir(parents=True,exist_ok=True);backup.write_bytes(before)
    path.write_bytes((b'\xef\xbb\xbf' if before.startswith(b'\xef\xbb\xbf') else b'')+content.encode('utf-8'))
for target in [D/ITEM['ue_icon'],D/'Icons'/(KEY+'.png')]:target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(R/(KEY+'.png'),target)
brief_path=R/'Design/design-brief-v02.json';brief=read(brief_path);brief.update(stage='accepted_model_saved_and_integrated',approved_by_user='可用，继续',published_item=KEY,model_created=True,engine_imported=True);write(brief_path,brief)
write(R/'published.json',dict(completed=True,item=item,recipe=recipe,robe_underlayers_added=added,shared_body='Jason native body used by first-person owner lower body and third-person weapon poses',weapon_dispatch='Existing common modular outfit path; no weapon-specific lower-body override added',canonical_icon=str(D/'Icons'/(KEY+'.png')),editable=editable['blend'],runtime_tested=False))
print('MAGE_PANTS_PUBLISHED',KEY,flush=True)
