"""Enumerate actual pants and boot routes, reusing matching saved mesh captures."""
import hashlib,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
from pants_compatibility_paths import *
c=read(P/'Content/ColdSteelData/modular_outfits.json');catalog=read(P/'Content/ColdSteelData/items.json')
shirt_source=read(P/'SourceAssets/RangerCrouchFit20261021/inputs.json')['recipe']['ue_field_sweater']
for field in ('rig_meshes','owner_body_meshes'):
    if c['items']['ue_field_sweater'][field]['Jason']!=shirt_source[field]['Jason']:raise RuntimeError('Update the authored shirt source before fitting a new shirt revision')
old=read(P/'SourceAssets/BlueMageRobe20261018/UnderRobeFit20261020/authored.json');known={r['source']:r for r in old['rows']}
previous=read(R/'inventory.json') if (R/'inventory.json').exists() else {}
previous_rows={row['asset']:row for row in previous.get('meshes',[])}
approved_shas=dict(previous.get('approved_asset_sha256',{}))
for row in previous.get('meshes',[]):
    if row.get('capture'):known[row['asset']]=dict(file=row['capture'],asset_sha256=row.get('asset_sha256'))
items={};meshes={};robe=c['items']['ue_blue_mage_robe'];shirt=c['items']['ue_field_sweater']
accepted=read(P/'SourceAssets/RangerLeatherPants20261021/RealisticCutV3/Integration20261022/published.json')
for key,item in c['items'].items():
    if item.get('slot')!=15:continue
    routes=[]
    for rig,asset in item.get('rig_meshes',{}).items():routes.append(dict(rig=rig,shoe=None,asset=asset))
    for shoe,rigs in item.get('shoe_fit_meshes',{}).items():
        for rig,asset in rigs.items():routes.append(dict(rig=rig,shoe=shoe,asset=asset))
    items[key]=dict(name=catalog.get(key,{}).get('name',key),recipe=item,routes=routes)
    for route in routes:
        path=route['asset']
        if route['rig']!='Jason':raise RuntimeError('This shirt needs a matching native source for rig '+route['rig'])
        if path in meshes:continue
        sha=hashlib.sha256(disk(path).read_bytes()).hexdigest();row=dict(asset=path,item=key,rig=route['rig'],asset_sha256=sha,robe_inner=robe.get('underlayer_meshes',{}).get(path))
        approved=path in accepted['robe_mappings'] and key=='ue_leather_pants'
        if approved and path not in approved_shas:approved_shas[path]=previous_rows.get(path,{}).get('asset_sha256',sha)
        if approved and approved_shas[path]==sha:row['reuse_pair']=accepted['shirt_pair']
        else:
            source=known.get(path)
            if source and source.get('asset_sha256')==sha and Path(source['file']).exists():row['capture']=source['file']
        meshes[path]=row
missing=[k for k,v in catalog.items() if v.get('equipSlot')=='pants' and k not in items]
if missing:raise RuntimeError('Register the wearable recipe for these pants first: '+str(missing))
write(R/'inventory.json',dict(items=items,meshes=list(meshes.values()),shirt=shirt,robe=robe,item_count=len(items),mesh_count=len(meshes),approved_asset_sha256=approved_shas,runtime_tested=False))
print('PANTS_COMPATIBILITY_INVENTORY',len(items),len(meshes),'need captures',sum(not r.get('capture') and not r.get('reuse_pair') for r in meshes.values()),flush=True)
