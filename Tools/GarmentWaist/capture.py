"""Capture the current waist audit scope; read saved assets, never live poses."""
import gc, hashlib, json
from pathlib import Path
import unreal as u

P=Path('D:/FPS3D/FPSGAME'); R=P/'SourceAssets/GarmentWaist20261023'
R.mkdir(parents=True,exist_ok=True)
# Reuse the existing native mesh reader without its task-specific dispatch.
reader=P/'Tools/GarmentSleeveRepair/capture.py'
ns={'__name__':'waist_source_reader'}
exec(compile(reader.read_text(encoding='utf-8').split('\nc=json.loads(')[0],str(reader),'exec'),ns)
cfg=json.loads((P/'Content/ColdSteelData/modular_outfits.json').read_text(encoding='utf-8-sig'))
catalog=json.loads((P/'Content/ColdSteelData/items.json').read_text(encoding='utf-8-sig'))
shirts={k:v for k,v in cfg['items'].items() if v.get('slot')==7}
pants={k:v for k,v in cfg['items'].items() if v.get('slot')==15}
policies=json.loads((P/'Tools/GarmentWaist/policies.json').read_text(encoding='utf-8'))
missing=set(shirts)-set(policies['shirts'])
if missing:raise RuntimeError('Declare waist construction and native sources for new shirts: '+str(sorted(missing)))
for item in shirts:
    if policies['shirts'][item]['mode'] not in ('tuck','native_body_with_tucked_trim','existing_tuck','robe_underlayer','outer_jacket_with_inner_tuck','outer_armor_above_waist'):
        raise RuntimeError('Provide the producer for this garment construction: '+item)
    if policies['shirts'][item]['mode']=='outer_jacket_with_inner_tuck':
        # Dedicated outer jackets must not be silently omitted when a new
        # trouser route is published by the general short-shirt workflow.
        policy=policies['shirts'][item]
        baseline=json.loads((P/policy['source_root']/'Before/modular_outfits.json').read_text(encoding='utf-8-sig'))
        previous={k:v for k,v in baseline['items'].items() if v.get('slot')==15}
        # An additional native lower can reuse the exact existing waistband.
        # Accept additional routes only when publication already provided the
        # jacket's item-level fit and exact mesh-level fit for every new path.
        jacket=shirts[item]
        def published_fit(key,path):
            pair=jacket.get('pants_fit_meshes',{}).get(key)
            return bool(pair and jacket.get('pants_mesh_fit_meshes',{}).get(path)==pair)
        stale=bool(set(previous)-set(pants))
        for key,recipe in pants.items():
            old=previous.get(key);shoes=recipe.get('shoe_fit_meshes',{});base=recipe.get('rig_meshes',{})
            if old:
                old_shoes=old.get('shoe_fit_meshes',{})
                stale |= old.get('rig_meshes',{})!=base or any(shoes.get(s)!=route for s,route in old_shoes.items())
                additions=[route for shoe,route in shoes.items() if shoe not in old_shoes]
            else:additions=[base,*shoes.values()]
            stale |= any(not published_fit(key,route.get('Jason')) for route in additions)
        if stale:
            raise RuntimeError('Refresh the dedicated outer-jacket waist producer before continuing: '+policy['producer'])
catalog_missing=[k for k,v in catalog.items() if v.get('equipSlot')=='pants' and k not in pants]
if catalog_missing:raise RuntimeError('Missing wearable pants recipes: '+str(catalog_missing))
catalog_missing=[k for k,v in catalog.items() if v.get('equipSlot')=='armor' and k not in shirts]
if catalog_missing:raise RuntimeError('Missing wearable shirt recipes: '+str(catalog_missing))
def write(p,d):
    p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(d,ensure_ascii=False,indent=2),encoding='utf-8')
def disk(p):return P/'Content'/(p.split('.')[0][6:]+'.uasset')
rows=[]
for item,policy in policies['shirts'].items():
    if policy['mode'] not in ('tuck','native_body_with_tucked_trim','existing_tuck'):continue
    for profile,field in [('Jason','rig_meshes'),('Owner_Jason','owner_body_meshes')]:
        path=shirts[item][field]['Jason'];file=R/'Read'/item/(profile+'.json')
        ns['read'](path,file);rows.append(dict(item=item,profile=profile,asset=path,file=str(file),asset_sha256=hashlib.sha256(disk(path).read_bytes()).hexdigest()))
        gc.collect();u.SystemLibrary.collect_garbage()
base='/Game/Characters/ModularOutfit20260924/ArmoredBoots20261004/SK_Jason_Base.SK_Jason_Base'
ns['read'](base,R/'Read/NativeBase.json')
routes=[]
for item,recipe in pants.items():
    for rig,path in recipe.get('rig_meshes',{}).items():routes.append(dict(item=item,rig=rig,shoe=None,asset=path))
    for shoe,rigs in recipe.get('shoe_fit_meshes',{}).items():
        for rig,path in rigs.items():routes.append(dict(item=item,rig=rig,shoe=shoe,asset=path))
write(R/'inventory.json',dict(shirts=shirts,pants=pants,rows=rows,pants_routes=routes,
    names={k:catalog.get(k,{}).get('name',k) for k in [*shirts,*pants]},
    asset_sha256={r['asset']:hashlib.sha256(disk(r['asset']).read_bytes()).hexdigest() for r in routes},runtime_tested=False))
print('GARMENT_WAIST_CAPTURE_COMPLETE',len(shirts),len(pants),len(rows),flush=True)
