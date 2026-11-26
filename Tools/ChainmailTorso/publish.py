"""Publish only the saved chainmail torso and its matching display assets."""
import copy,hashlib,importlib.util,json,shutil
from pathlib import Path
P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/ChainmailTorsoRepair20261021';D=P/'Content/ColdSteelData';KEY='ue_chainmail_shirt'
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
s=importlib.util.spec_from_file_location('mail_json_entries',str(P/'Tools/BrownLeatherSet/json_entries.py'));entries=importlib.util.module_from_spec(s);s.loader.exec_module(entries)
saved=read(R/'saved_assets.json');display=read(R/'display_assets.json');authored=read(R/'authored.json');editable=read(R/'editable.json');baseline=read(R/'before.json')['recipe']
if not all(v.get('completed') for v in (saved,display,authored,editable)):raise RuntimeError('Finish saving chainmail assets before integration')
paths=[D/'items.json',D/'modular_outfits.json'];raw=[p.read_bytes() for p in paths];texts=[b.decode('utf-8-sig') for b in raw];catalog,config=[json.loads(t) for t in texts]
item=copy.deepcopy(catalog[KEY]);recipe=copy.deepcopy(config['items'][KEY]);original=copy.deepcopy(recipe)
for profile in ('Body','Jason','Owner_Jason'):
    field='owner_body_meshes' if profile=='Owner_Jason' else 'rig_meshes';rig='Jason' if profile=='Owner_Jason' else profile;row=saved['saved'][KEY+'/'+profile]
    if recipe[field][rig] not in (baseline[field][rig],row['asset']):raise RuntimeError('Current chainmail torso changed during authoring: '+profile)
    if hashlib.sha256((R/'Authored'/KEY/(profile+'.json')).read_bytes()).hexdigest()!=row['author_sha256']:raise RuntimeError('Unsaved source '+profile)
    recipe[field][rig]=row['asset']
item.update(ue_icon='Icons/ChainmailTorsoRepair20261021/ue_chainmail_shirt.png',world_mesh=display['pickup'],world_material='',ue_equipment_icon_mesh=display['icon'],ue_icon_pitch=0,ue_icon_yaw=-90)
out=[entries.replace(texts[0],[KEY],item),entries.replace(texts[1],['items',KEY],recipe)]
for path,data in zip(paths,raw):
    backup=R/'Before'/path.name;backup.parent.mkdir(exist_ok=True)
    if not backup.exists():backup.write_bytes(data)
for target in dict.fromkeys([D/item['ue_icon'],D/catalog[KEY]['ue_icon'],D/'Icons/ue_chainmail_shirt.png']):
    backup=R/'Before'/('icon-'+'_'.join(target.relative_to(D).parts))
    if target.exists() and not backup.exists():shutil.copy2(target,backup)
    target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(R/'ue_chainmail_shirt.png',target)
if any(p.read_bytes()!=b for p,b in zip(paths,raw)):raise RuntimeError('Catalog changed during scoped integration; retry')
for p,before,text in zip(paths,raw,out):p.write_bytes((b'\xef\xbb\xbf' if before.startswith(b'\xef\xbb\xbf') else b'')+text.encode('utf-8'))
(R/'published.json').write_text(json.dumps(dict(completed=True,revision=R.name,geometry_profiles=['Body','Jason','Owner_Jason'],recipe=recipe,item=item,diagnosis=authored['diagnosis'],first_person_sleeves_changed=False,gameplay_attributes_changed=False,runtime_tested=False),ensure_ascii=False,indent=2),encoding='utf-8')
print('CHAINMAIL_TORSO_PUBLISHED: Body, Jason, Owner_Jason, pickup, inventory icon; 23 FP sleeves retained',flush=True)
