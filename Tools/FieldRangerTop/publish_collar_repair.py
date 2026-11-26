"""Scoped local integration; preserve all arm profiles and unrelated item changes."""
import copy,hashlib,importlib.util,json,shutil
from pathlib import Path
P=Path('D:/FPS3D/FPSGAME');BASE=P/'SourceAssets/FieldRangerTop20261020';R=BASE/'CollarRepair20261021';D=P/'Content/ColdSteelData';KEY='ue_field_sweater'
def read(path):return json.loads(path.read_text(encoding='utf-8-sig'))
s=importlib.util.spec_from_file_location('collar_json_entries',str(P/'Tools/BrownLeatherSet/json_entries.py'));entries=importlib.util.module_from_spec(s);s.loader.exec_module(entries)
saved=read(R/'saved_assets.json');display=read(R/'display_assets.json');authored=read(R/'authored.json');editable=read(R/'editable.json')
if not all(x.get('completed') for x in (saved,display,authored,editable)):raise RuntimeError('Complete all collar saves before publication')
paths=[D/'items.json',D/'modular_outfits.json'];raw=[p.read_bytes() for p in paths];texts=[b.decode('utf-8-sig') for b in raw];catalog,config=[json.loads(t) for t in texts]
recipe=copy.deepcopy(config['items'][KEY]);item=copy.deepcopy(catalog[KEY]);baseline=read(R/'Before/modular_outfits.json')['items'][KEY]
for row in authored['records']:
    profile=row['profile'];record=saved['saved'][KEY+'/'+profile]
    if record['author_sha256']!=hashlib.sha256(Path(row['authored']).read_bytes()).hexdigest():raise RuntimeError('Unsaved collar geometry '+profile)
    field='owner_body_meshes' if profile=='Owner_Jason' else 'rig_meshes';rig='Jason' if profile=='Owner_Jason' else profile
    if recipe[field][rig] not in (baseline[field][rig],record['asset']):raise RuntimeError('The target torso changed during repair: '+profile)
    recipe[field][rig]=record['asset']
recipe.setdefault('owner_body_hidden_materials',{})['Jason']=list(range(6,12))
item.update(ue_icon='Icons/FieldRangerTop20261020/CollarRepair20261021/ue_field_sweater.png',world_mesh=display['pickup'],world_material='',ue_equipment_icon_mesh=display['icon'],ue_icon_pitch=0,ue_icon_yaw=-90)
out=[entries.replace(texts[0],[KEY],item),entries.replace(texts[1],['items',KEY],recipe)]
for target in dict.fromkeys([D/item['ue_icon'],D/catalog[KEY]['ue_icon'],D/'Icons/ue_field_sweater.png',D/'Icons/ModularOutfit20260924/ue_field_sweater.png']):
    backup=R/'Before'/('icon-'+'_'.join(target.relative_to(D).parts));backup.parent.mkdir(parents=True,exist_ok=True)
    if target.exists() and not backup.exists():shutil.copy2(target,backup)
    target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(R/'ue_field_sweater.png',target)
if any(p.read_bytes()!=b for p,b in zip(paths,raw)):raise RuntimeError('Catalog changed during scoped publication; retry')
for path,before,content in zip(paths,raw,out):path.write_bytes((b'\xef\xbb\xbf' if before.startswith(b'\xef\xbb\xbf') else b'')+content.encode('utf-8'))
(R/'published.json').write_text(json.dumps(dict(completed=True,revision='CollarRepair20261021',changed_profiles=['Body','Jason','Owner_Jason'],preserved_arm_profiles=[k for k in recipe['rig_meshes'] if k not in ('Body','Jason')],item=item,recipe=recipe,exports=editable['exports'],runtime_tested=False,gameplay_attributes_changed=False),ensure_ascii=False,indent=2),encoding='utf-8')
print('COLLAR_PUBLISHED Body Jason Owner_Jason; existing FP arm profiles retained',flush=True)
