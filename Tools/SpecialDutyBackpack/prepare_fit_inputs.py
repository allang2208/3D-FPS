"""Reuse unchanged native captures and the saved ST6 additive detail recipe."""
import hashlib
import json
from pathlib import Path

P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/SpecialDutyBackpack20261024/MeshyFitR1_20261024';OUT=R/'BodyInputs'
read=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
manifest=read(OUT/'manifest.json');records=manifest['records']
lookup={(r['source'],r['weighted']):r for r in records}
details=P/'SourceAssets/ST6LowerDetail20261024';detail_plan=read(details/'manifest.json');saved=read(details/'saved_assets.json')
recipes={r['target']:r for r in detail_plan['meshes']}

def package(path):return P/'Content'/(path.split('.')[0].removeprefix('/Game/')+'.uasset')

def input_for(path,weighted):
    if (path,weighted) in lookup:
        record=lookup[path,weighted]
        if hashlib.sha256(package(path).read_bytes()).hexdigest()!=record['package_sha256']:
            raise RuntimeError('Native input changed; use read_fit_r2.py: '+path)
        return record['file']
    recipe=recipes.get(path)
    if weighted or not recipe or not recipe['detail']:
        raise RuntimeError('Capture this new native surface with read_fit_r2.py: '+path)
    receipt=saved['meshes'][recipe['source']]
    raw=(details/'Authored'/recipe['detail']).read_bytes()
    digest=hashlib.sha256(raw+json.dumps(saved['materials']).encode()).hexdigest()
    if not receipt['base_geometry_preserved'] or receipt['asset']!=path or receipt['detail_sha256']!=digest:
        raise RuntimeError('ST6 authored geometry is not the saved recipe: '+path)
    base=read(OUT/input_for(recipe['source'],False))
    extra=json.loads(raw)['positions']
    points=base['points']+[v for v in extra if abs(v[0])<28 and 80<v[2]<151]
    name=hashlib.sha256((path+str(False)).encode()).hexdigest()[:16]+'.json'
    (OUT/name).write_text(json.dumps({'source':path,'points':points},separators=(',',':')))
    record={'source':path,'file':name,'weighted':False,'package_sha256':hashlib.sha256(package(path).read_bytes()).hexdigest(),
            'vertices':len(points),'source_mode':'unchanged captured base plus saved identity-transform additive detail',
            'base_source':recipe['source'],'detail_source':str(details/'Authored'/recipe['detail']),'detail_sha256':digest}
    records.append(record);lookup[path,False]=record
    return name

body=read(P/'Content/ColdSteelData/player_body.json');modular=read(P/'Content/ColdSteelData/modular_outfits.json')
rigs={}
for rig,config,items in [('Jason',body,modular['items']),('Kaitlin',body['body_variants']['kaitlin'],modular['body_variants']['kaitlin']['items'])]:
    pack=config['outfits']['ue_pathfinder_backpack']
    row={'body':input_for(config['body_mesh'],True),'template':pack['world_mesh'],'shirts':{},'waist_routes':[]}
    for key in pack['world_mesh_by_shirt']:
        item=items[key];base=item['rig_meshes'][rig];paths={base}
        for field in ['pants_mesh_fit_meshes','pants_fit_meshes']:
            paths.update(v['rig_meshes'][rig] for v in item.get(field,{}).values() if rig in v.get('rig_meshes',{}))
        fallback=item.get('pants_fit_default',{}).get('rig_meshes',{}).get(rig)
        if fallback:paths.add(fallback)
        row['shirts'][key]={'base':input_for(base,True),'surfaces':[input_for(v,False) for v in sorted(paths)]}
    for key,item in items.items():
        if item.get('slot')!=15:continue
        paths={item['rig_meshes'][rig]}
        paths.update(v[rig] for v in item.get('shoe_fit_meshes',{}).values() if rig in v)
        for path in sorted(paths):row['waist_routes'].append({'item':key,'source':path,'file':input_for(path,False)})
    rigs[rig]=row
(OUT/'manifest.json').write_text(json.dumps({'rigs':rigs,'records':records},indent=2))
print('SPECIAL_DUTY_FIT_INPUTS_PREPARED',[(rig,len(row['waist_routes'])) for rig,row in rigs.items()],flush=True)
