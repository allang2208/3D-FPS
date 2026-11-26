"""Switch only the approved green field top after all packages are saved."""
import copy,hashlib,importlib.util,json,shutil
from pathlib import Path
P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/FieldRangerTop20261020';D=P/'Content/ColdSteelData';key='ue_field_sweater'
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
spec=importlib.util.spec_from_file_location('ranger_json_entries',str(P/'Tools/BrownLeatherSet/json_entries.py'));entries=importlib.util.module_from_spec(spec);spec.loader.exec_module(entries)
saved=read(R/'saved_assets.json');display=read(R/'display_assets.json');source=read(R/'inputs.json');authored=read(R/'authored.json');editable=read(R/'editable.json')
if not all(d.get('completed') for d in (saved,display,authored,editable)):raise RuntimeError('Ranger production is not completely saved')
paths=[D/'items.json',D/'modular_outfits.json'];raw=[p.read_bytes() for p in paths];texts=[b.decode('utf-8-sig') for b in raw];catalog,config=[json.loads(t) for t in texts]
recipe=copy.deepcopy(config['items'][key]);item=copy.deepcopy(catalog[key]);meshes={};owners={}
if recipe['rig_meshes']!=source['recipe']['rig_meshes'] or recipe.get('owner_body_meshes')!=source['recipe'].get('owner_body_meshes'):
    raise RuntimeError('The current field top changed during production; preserve it for scoped merging')
for row in authored['records']:
    record=saved['saved'][key+'/'+row['profile']]
    if record['author_sha256']!=hashlib.sha256(Path(row['authored']).read_bytes()).hexdigest():raise RuntimeError('Unsaved ranger geometry '+row['profile'])
    if row['group']=='Owner':owners[row['profile'].removeprefix('Owner_')]=record['asset']
    else:meshes[row['profile']]=record['asset']
recipe.update(rig_meshes=meshes,owner_body_meshes=owners,owner_body_hidden_materials={k:list(range(6,12)) for k in owners},
    appearance_family='FieldRangerTop20261020',material='')
item.update(desc='橄榄色斜纹布野行上衣，深棕软皮护肩、护肘及前臂加强，低立领、贴合袖口与嵌线口袋，肩背留有活动褶。',
    ue_icon='Icons/FieldRangerTop20261020/ue_field_sweater.png',world_mesh=display['pickup'],world_material='',
    ue_equipment_icon_mesh=display['icon'],ue_icon_pitch=0,ue_icon_yaw=-90)
out=[entries.replace(texts[0],[key],item),entries.replace(texts[1],['items',key],recipe)]
for target in [D/item['ue_icon'],D/catalog[key]['ue_icon'],D/'Icons/ue_field_sweater.png',D/'Icons/ModularOutfit20260924/ue_field_sweater.png']:
    backup=R/'Before'/('icon-'+'_'.join(target.relative_to(D).parts));backup.parent.mkdir(parents=True,exist_ok=True)
    if target.exists() and not backup.exists():shutil.copy2(target,backup)
    target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(R/'ue_field_sweater.png',target)
if any(p.read_bytes()!=b for p,b in zip(paths,raw)):raise RuntimeError('Catalog changed during scoped publication; retry')
for path,before,content in zip(paths,raw,out):path.write_bytes((b'\xef\xbb\xbf' if before.startswith(b'\xef\xbb\xbf') else b'')+content.encode('utf-8'))
(R/'published.json').write_text(json.dumps(dict(completed=True,item=item,recipe=recipe,profiles=len(meshes),
    owner_profiles=list(owners),native_exports=editable['exports'],runtime_tested=False,
    gameplay_attributes_changed=False),ensure_ascii=False,indent=2),encoding='utf-8')
print('RANGER_PUBLISHED',len(meshes),'native profiles',len(owners),'owner body profiles',flush=True)
