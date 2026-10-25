"""Explicit offline receipt and asset-reference audit; does not load or modify UE assets."""
import hashlib,json
from pathlib import Path
P=Path(__file__).resolve().parents[2]
R=P/'SourceAssets/LeatherQuiverBelt20261025';D=P/'Content/ColdSteelData';KEY='ue_leather_quiver_belt'
read=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
saved=read(R/'saved_assets.json');delivery=read(R/'delivery.json');items=read(D/'items.json');recipes=read(D/'modular_outfits.json')
rows=[]
def check(name,ok,detail=''):rows.append(dict(case=name,passed=bool(ok),detail=detail))
def paths(o):
    if isinstance(o,str) and o.startswith('/Game/'):yield o
    elif isinstance(o,dict):
        for v in o.values():yield from paths(v)
    elif isinstance(o,list):
        for v in o:yield from paths(v)
item=items[KEY]
check('catalog belt slot and grid',item['equipSlot']=='belt' and item['grid_w']==2 and item['grid_h']==3)
check('backpack icon saved',(D/item['ue_icon']).is_file())
check('backpack icon matches authored icon',hashlib.sha256((D/item['ue_icon']).read_bytes()).hexdigest()==saved['icon_sha256'])
check('pickup uses saved mesh',item['world_mesh']==saved['pickup']['asset'])
allpaths=set(paths(saved))
for row in delivery['records']:
    body=row['body'];recipe=(recipes if body=='Jason' else recipes['body_variants']['kaitlin'])['items'][KEY]
    check(body+' recipe uses saved wear',recipe['rig_meshes'][body]==saved['wear'][body]['asset'] and recipe['owner_body_meshes'][body]==saved['wear'][body]['asset'])
    check(body+' source LOD hashes',saved['wear'][body]['lod_source_hashes']==[hashlib.sha256(Path(l['file']).read_bytes()).hexdigest() for l in row['lods']])
    motion=recipe['quiver_motion'];check(body+' bounded weighted motion',motion['max_angle_degrees']<=2.5 and motion['max_displacement_cm']<=2.5 and motion['damping']>=.85)
    check(body+' five arrow slots',len(motion['arrow_tips'])==5)
    allpaths.update(paths(recipe))
for path in sorted(allpaths):
    package=path.split('.')[0]
    check('saved asset '+package,(P/'Content'/package.removeprefix('/Game/')).with_suffix('.uasset').is_file())
report=dict(checks=len(rows),failed=sum(not r['passed'] for r in rows),results=rows,scope='catalog/reference/source-hash checks; no rendered fit or network transport')
out=R/'Audit20261025/catalog.json';out.parent.mkdir(exist_ok=True);out.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('QUIVER_CATALOG_AUDIT',report['checks'],'checks;',report['failed'],'failed')
for row in rows:
    if not row['passed']:print('FAIL',row['case'],row['detail'])
raise SystemExit(bool(report['failed']))
