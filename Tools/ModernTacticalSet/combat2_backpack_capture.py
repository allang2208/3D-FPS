"""Execute the standard backpack native capture in this isolated asset host."""
import json,os,runpy
from pathlib import Path
os.environ['BACKPACK_FIT_RUN_DIR']='D:/FPS3D/FPSGAME/SourceAssets/BackpackFit20261024/ModernTacticalShirtR220261114'
os.environ['BACKPACK_FIT_SHIRT']='ue_modern_kevlar_vest'
root=Path(os.environ['BACKPACK_FIT_RUN_DIR'])
plan=json.loads((root/'plan.json').read_text(encoding='utf-8'))
full=json.loads((root/'full_plan.json').read_text(encoding='utf-8'))
# Recut straps from the current base pack. Using the previous green-vest fit
# here would accumulate its shape and gravity offsets a second time.
bare={(row['rig'],row['item']):row for row in full['rows'] if not row['shirt']}
needed={path for rig in plan['rigs'].values() for path in [
    rig['body'],*rig['pants'],*([rig['head']] if rig.get('head') else []),
    *(path for surfaces in rig['shirt_surfaces'].values() for path in surfaces)]}
for row in plan['rows']:
    source=bare[row['rig'],row['item']]
    for key in ['mesh','rigid_mesh','rigid_location','rigid_rotation_quat','hanging_pack']:
        if key in source:row[key]=source[key]
    needed.add(row['mesh'])
    if row.get('rigid_mesh'):needed.add(row['rigid_mesh'])
plan['assets']=[asset for asset in full['assets'] if asset['path'] in needed]
(root/'plan.json').write_text(json.dumps(plan,ensure_ascii=False,indent=2),encoding='utf-8')
wanted={row['path']:set(row['roles']) for row in plan['assets']}
cache={}
for revision in ['ContactFitR3','ST6FemaleCollar20261108','SavedContactR3','ModernTactical20261114','ModernTacticalEarth20261114','ModernTacticalFitR320261114']:
    manifest=root.parent/revision/'captured.json'
    if not manifest.exists():continue
    for path,row in json.loads(manifest.read_text(encoding='utf-8-sig')).items():
        if path in wanted and wanted[path]==set(row.get('roles',[])):cache[path]=row
if (root/'captured.json').exists():cache.update(json.loads((root/'captured.json').read_text(encoding='utf-8')))
# The standard capture producer compares each package hash before reuse.
(root/'captured.json').write_text(json.dumps(cache),encoding='utf-8')
producer=Path('D:/FPS3D/FPSGAME/Tools/BackpackFit/capture.py')
code=producer.read_text(encoding='utf-8').replace('records={}','records={};new_count=0')
code=code.replace('del asset,dm,points,faces;gc.collect();u.SystemLibrary.collect_garbage()',
    'del asset,dm,points,faces;gc.collect();u.SystemLibrary.collect_garbage()\n            new_count+=1\n            if new_count>=6:break')
code=code.replace("{'state':'completed','assets':len(records)}","{'state':'completed' if len(records)==len(plan['assets']) else 'partial','assets':len(records),'expected':len(plan['assets'])}")
exec(compile(code,str(producer),'exec'),{'__file__':str(producer),'__name__':'__main__'})
