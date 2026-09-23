"""Exercise the real catalog builder with all file writes intercepted in memory."""
import json, runpy
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parents[1];OUT=ROOT/'Results'
routes=PROJECT/'SourceAssets/DungeonRoutes20260922'
registry=routes/'Config/room-extensions.json'
extension_path=PROJECT/'SourceAssets/DungeonVentFreight20260922/Config/modules.json'
source=(ROOT/'Snapshot/SourceAssets/DungeonRoutes20260922/Scripts/build_catalog.py').read_text(encoding='utf-8')
original_read=Path.read_text;original_exists=Path.exists;captured={}
def read(p,*a,**kw):
    if p==registry:return json.dumps(['DungeonVentFreight20260922/Config/modules.json'])
    return original_read(p,*a,**kw)
def exists(p):return True if p==registry else original_exists(p)
def write(p,data,*a,**kw):captured[str(p)]=data;return len(data)
with patch.object(Path,'read_text',read),patch.object(Path,'exists',exists),patch.object(Path,'write_text',write):
    scope={'__file__':str(routes/'Scripts/build_catalog.py'),'__name__':'__audit__'}
    exec(compile(source,str(routes/'Scripts/build_catalog.py'),'exec'),scope)
catalog=json.loads(captured[str(routes/'Config/catalog.json')]);ids=[m['id'] for m in catalog['modules']]
result={'scenario':'Simulate completed registration of two existing candidate rooms; real builder, writes captured only',
        'registry_exists_on_disk':registry.exists(),'serialized_module_ids':ids,'room_ids':catalog.get('room_ids'),
        'missing_room_modules':[m for m in catalog['room_ids'] if m not in ids],
        'outer_modules_ids':[m['id'] for m in scope['modules']],
        'same_list':scope['modules'] is scope['catalog']['modules'],'captured_write_paths':list(captured)}
editor=json.loads((OUT/'editor-state.json').read_text(encoding='utf-8'))
active=json.loads(editor['generators'][0]['module_catalog_json']);hard=set(editor['generators'][0]['hard_assets'])
paths=set()
for m in active['modules']:
    for p in m['parts']+[p for s in m.get('side_sockets',[]) for p in s['parts']]:
        paths.add(p['mesh']);paths.update(x for x in p.get('materials',[]) if x)
    for p in m.get('props',[]):
        paths.update((p['skeletal_mesh'],p['closed_animation']));paths.update(p['material_overrides'].values())
def canonical(p):return p if '.' in p.rsplit('/',1)[-1] else p+'.'+p.rsplit('/',1)[-1]
result['active_explicit_reference_count']=len(paths)
result['active_missing_hard_refs']=[p for p in sorted(paths) if canonical(p) not in hard]
result['active_missing_game_files']=[p for p in sorted(paths) if p.startswith('/Game/') and not (PROJECT/'Content'/p[6:].split('.')[0]).with_suffix('.uasset').exists()]
(OUT/'catalog-probe.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(result,ensure_ascii=False,indent=2))
