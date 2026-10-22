"""Publish complete actual-mesh fits plus future-pants defaults without changing items."""
import copy,hashlib,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
from pants_compatibility_paths import *
sys.path.insert(0,str(P/'Tools/BrownLeatherSet'));from json_entries import replace
inventory=read(R/'inventory.json');authored=read(R/'authored.json');saved=read(R/'saved_assets.json')
if not saved.get('completed'):raise RuntimeError('Finish saving all native waist fits')
for row in authored['records']:
    if hashlib.sha256(Path(row['file']).read_bytes()).hexdigest()!=saved['saved'][row['signature']+'/'+row['profile']]['author_sha256']:raise RuntimeError('Unsaved fit source')
file=P/'Content/ColdSteelData/modular_outfits.json';raw=file.read_bytes();text=raw.decode('utf-8-sig');cfg=__import__('json').loads(text)
for key,item in inventory['items'].items():
    for field in ('rig_meshes','shoe_fit_meshes'):
        if cfg['items'][key].get(field)!=item['recipe'].get(field):raise RuntimeError('Pants routes changed; rerun inventory: '+key)
shirt=copy.deepcopy(cfg['items']['ue_field_sweater']);robe=copy.deepcopy(cfg['items']['ue_blue_mage_robe'])
for field in ('rig_meshes','owner_body_meshes'):
    if shirt[field]['Jason']!=inventory['shirt'][field]['Jason']:raise RuntimeError('Shirt changed while fitting')
def paired(route):
    if route['reused']:return route['pair']
    prefix=route['signature']+'/'
    return dict(rig_meshes={'Jason':saved['saved'][prefix+'Jason']['asset']},owner_body_meshes={'Jason':saved['saved'][prefix+'Owner_Jason']['asset']})
mesh_pairs={path:paired(row) for path,row in authored['routes'].items()}
shirt.setdefault('pants_mesh_fit_meshes',{}).update(mesh_pairs)
for key,item in inventory['items'].items():
    path=item['recipe']['rig_meshes']['Jason'];shirt.setdefault('pants_fit_meshes',{})[key]=mesh_pairs[path]
# Accepted tuck is a native-rig fallback, not an item-ID allowlist. Future
# authored pants receive measured exact pairs through this same inventory.
shirt['pants_fit_default']=paired(dict(reused=False,signature=authored['default_signature']))
shirt['pants_fit_pipeline']='Tools/PantsCompatibility/run.ps1'
template=cfg['items']['ue_blue_mage_pants'];inner=robe['underlayer_meshes']
default=copy.deepcopy(robe.get('pants_underlayer_default'))
if not default:default=dict(rig_meshes={rig:inner[path] for rig,path in template['rig_meshes'].items()},shoe_fit_meshes={shoe:{rig:inner[path] for rig,path in rigs.items()} for shoe,rigs in template['shoe_fit_meshes'].items()})
robe['pants_underlayer_default']=default
out=replace(replace(text,['items','ue_field_sweater'],shirt),['items','ue_blue_mage_robe'],robe)
if file.read_bytes()!=raw:raise RuntimeError('Concurrent configuration update; retry publication')
before=R/'Before/modular_outfits.json'
if not before.exists():before.parent.mkdir(parents=True,exist_ok=True);before.write_bytes(raw)
file.write_bytes((b'\xef\xbb\xbf' if raw.startswith(b'\xef\xbb\xbf') else b'')+out.encode('utf-8'))
write(R/'published.json',dict(completed=True,item_count=len(inventory['items']),mesh_count=len(mesh_pairs),items=list(inventory['items']),mesh_pairs=mesh_pairs,default_pair=shirt['pants_fit_default'],robe_default=default,assets_saved=len(saved['saved']),runtime_tested=False))
print('PANTS_COMPATIBILITY_PUBLISHED',len(inventory['items']),len(mesh_pairs),flush=True)
