"""Publish the new mage boots and scoped combinations with existing trousers."""
from common import *
import copy,hashlib,shutil
saved=read(R/'saved_assets.json');editable=read(R/'editable_receipt.json')
if not saved.get('completed') or not editable.get('completed'):raise RuntimeError('Finish asset saving and exports before publication')
for file,sha in saved.get('source_sha256',{}).items():
    if hashlib.sha256(Path(file).read_bytes()).hexdigest()!=sha:raise RuntimeError('Source changed after saving: '+file)
entries=module('mage_boots_json_entries','Tools/BrownLeatherSet/json_entries.py');D=P/'Content/ColdSteelData';paths=[D/'items.json',D/'modular_outfits.json'];raw=[p.read_bytes() for p in paths];texts=[b.decode('utf-8-sig') for b in raw];catalog,config=[json.loads(t) for t in texts]
native=read(R/'native_reference.json');body=read(D/'player_body.json');profile=config['profiles'][body['body_mesh']]
if profile.get('native_bare_skin',profile['base'])!=native['source']:raise RuntimeError('Native body changed during authoring; retain sources for adaptation')
if KEY in config['items'] and config['items'][KEY].get('appearance_family')!=FAMILY:raise RuntimeError('Another definition owns this equipment key')
mesh=saved['meshes']['SK_Jason_BlueMageBoots'];item=copy.deepcopy(ITEM);item.update(world_mesh=saved['pickup'],ue_equipment_icon_mesh=saved['icon'])
recipe=dict(slot=13,material='',appearance_family=FAMILY,rig_meshes={'Jason':mesh},rig_world_covers={'Jason':[4,11,13,15,16]})
out_catalog=entries.replace(texts[0],[KEY],item) if KEY in catalog else entries.insert(texts[0],[],KEY,item)
out_config=entries.replace(texts[1],['items',KEY],recipe) if KEY in config['items'] else entries.insert(texts[1],['items'],KEY,recipe)
fits={}
for pants in ('ue_blue_mage_pants','ue_st6_tactical_pants','ue_smoke_grey_capri','ue_leather_pants','ue_chainmail_pants','ue_jeans','ue_cargo_pants'):
    fitting=copy.deepcopy(config['items'][pants]['shoe_fit_meshes']);selected=fitting.get('ue_armored_boots') or fitting.get('ue_leather_boots')
    if not selected:raise RuntimeError('No current high-boot fitting source for '+pants)
    fitting[KEY]=copy.deepcopy(selected);fits[pants]=fitting[KEY];out_config=entries.replace(out_config,['items',pants,'shoe_fit_meshes'],fitting)
# The entire boot ends below the robe's knee cut. Keep the full boot and sole.
underlayers=copy.deepcopy(config['items']['ue_blue_mage_robe']['underlayer_meshes']);underlayers[mesh]=mesh
out_config=entries.replace(out_config,['items','ue_blue_mage_robe','underlayer_meshes'],underlayers)
if any(path.read_bytes()!=before for path,before in zip(paths,raw)):raise RuntimeError('Catalog changed during publication; retry scoped publication')
for path,before,content in zip(paths,raw,[out_catalog,out_config]):
    backup=R/'Before'/path.relative_to(P)
    if not backup.exists():backup.parent.mkdir(parents=True,exist_ok=True);backup.write_bytes(before)
    path.write_bytes((b'\xef\xbb\xbf' if before.startswith(b'\xef\xbb\xbf') else b'')+content.encode('utf-8'))
for target in [D/ITEM['ue_icon'],D/'Icons'/(KEY+'.png')]:target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(R/(KEY+'.png'),target)
brief_path=R/'Design/design-brief-v01.json';brief=read(brief_path);brief.update(stage='accepted_model_saved_and_integrated',approved_by_user='就按这样',published_item=KEY,model_created=True,engine_imported=True);write(brief_path,brief)
write(R/'published.json',dict(completed=True,item=item,recipe=recipe,trouser_combinations=fits,robe_full_boot_mapping={mesh:mesh},shared_body='Jason native owner lower body and third-person body; weapon-independent modular outfit dispatch',native_skin_cover_top_cm=37.54038619995117,boot_top_cm=[38.27,38.9],canonical_icon=str(D/'Icons'/(KEY+'.png')),runtime_tested=False))
print('MAGE_BOOTS_PUBLISHED',KEY,'TROUSER_COMBINATIONS',len(fits),flush=True)
