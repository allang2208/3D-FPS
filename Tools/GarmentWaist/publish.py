"""Publish only saved waist mappings, preserving unrelated outfit configuration."""
import copy, hashlib, json, os, sys
from pathlib import Path
P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/GarmentWaist20261023'
if (R/'authoring.lock').exists():raise RuntimeError('Complete the active waist authoring revision before publication')
sys.path.insert(0,str(P/'Tools/BrownLeatherSet'));from json_entries import replace
def read(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def disk(p):return P/'Content'/(p.split('.')[0][6:]+'.uasset')
inventory=read(R/'inventory.json');authored=read(R/'authored.json');saved=read(R/'saved_assets.json')
if not saved.get('completed'):raise RuntimeError('Save every waist variant before publishing')
for row in authored['records']:
    old=saved['saved'][row['item']+'/'+row['group']+'/'+row['profile']]
    if sha(row['file'])!=old['author_sha256'] or not disk(old['asset']).exists():raise RuntimeError('Unsaved waist asset')
    if sha(disk(row['source_asset']))!=row['source_sha256']:raise RuntimeError('Source garment changed')
for path,digest in inventory['asset_sha256'].items():
    if sha(disk(path))!=digest:raise RuntimeError('Pants changed since waist fitting')
file=P/'Content/ColdSteelData/modular_outfits.json';raw=file.read_bytes();text=raw.decode('utf-8-sig');cfg=json.loads(text)
for item,recipe in inventory['pants'].items():
    for field in ('rig_meshes','shoe_fit_meshes'):
        if cfg['items'][item].get(field)!=recipe.get(field):raise RuntimeError('Pants routes changed')
items=sorted({r['item'] for r in authored['records']});changes={}
for item in items:
    recipe=copy.deepcopy(cfg['items'][item])
    for field in ('rig_meshes','owner_body_meshes'):
        if recipe[field]['Jason']!=inventory['shirts'][item][field]['Jason']:raise RuntimeError('Garment routes changed')
    def pair(group):
        return {field:{'Jason':saved['saved'][item+'/'+group+'/'+profile]['asset']} for field,profile in [('rig_meshes','Jason'),('owner_body_meshes','Owner_Jason')]}
    groups={r['group'] for r in authored['records'] if r['item']==item}
    fields=dict(pants_mesh_fit_meshes={path:pair(row['signature']) for path,row in authored['routes'].items() if row['signature'] in groups},
                pants_fit_meshes={k:pair(authored['routes'][v['rig_meshes']['Jason']]['signature']) for k,v in inventory['pants'].items() if authored['routes'][v['rig_meshes']['Jason']]['signature'] in groups},
                pants_fit_pipeline='Tools/GarmentWaist/run.ps1',waist_fit_revision='20261023-local-waist-tuck-v2')
    if authored['default_group'] in groups:fields['pants_fit_default']=pair(authored['default_group'])
    for key,value in fields.items():
        if isinstance(value,dict):recipe.setdefault(key,{}).update(value)
        else:recipe[key]=value
    text=replace(text,['items',item],recipe);changes[item]=fields
if file.read_bytes()!=raw:raise RuntimeError('Configuration changed; retry publication from fresh state')
before=R/'Before/modular_outfits.json';before.parent.mkdir(parents=True,exist_ok=True)
if not before.exists():before.write_bytes(raw)
out=(b'\xef\xbb\xbf' if raw.startswith(b'\xef\xbb\xbf') else b'')+text.encode('utf-8')
temp=file.with_name('modular_outfits.garment-waist.tmp');temp.write_bytes(out)
if file.read_bytes()!=raw:raise RuntimeError('Concurrent config edit; preserve current configuration')
os.replace(temp,file)
(R/'published.json').write_text(json.dumps(dict(completed=True,items=items,mesh_pair_count=len(authored['routes']),saved_mesh_count=len(authored['records']),changes=changes,runtime_tested=False),indent=2),encoding='utf-8')
print('GARMENT_WAIST_PUBLISHED',len(items),len(authored['routes']),len(authored['records']),flush=True)
