"""Persist the same placement in each active authoring input, preserving other edits."""
from pathlib import Path
import json,shutil
ROOT=Path(__file__).resolve().parent;PROJECT=ROOT.parents[1]
TRANSIT=PROJECT/'SourceAssets/DungeonFacilityTransit20261007'
INCIDENT=PROJECT/'SourceAssets/TransitIncidentDressing20261010'
def backup(path):
    dest=ROOT/'Backups/source-before'/path.relative_to(PROJECT)
    dest.parent.mkdir(parents=True,exist_ok=True)
    if not dest.exists():shutil.copy2(path,dest)
def save_json(path,data):path.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf8')
for relative,key in [('Config/layout.json','containers'),('Config/module-draft.json','native_interactions')]:
    path=TRANSIT/relative;backup(path);data=json.loads(path.read_text('utf-8-sig'))
    containers=data[key] if key=='containers' else data[key]['containers']
    item=next(p for p in containers if p['id']=='PPE5');item['position_m'][0]=1.9;save_json(path,data)
path=TRANSIT/'prepare.py';backup(path);text=path.read_text('utf-8-sig')
old='enumerate((-3.5,-2.6,-1.7,-.8,.1,1.0))';new='enumerate((-3.5,-2.6,-1.7,-.8,.1,1.9))'
if old not in text and new not in text:raise RuntimeError('PPE source changed')
path.write_text(text.replace(old,new),encoding='utf8')
path=INCIDENT/'recipe.py';backup(path);text=path.read_text('utf-8-sig')
old="part('CleaningMop','Mop',[-2035,-907,0],-59)";new="part('CleaningMop','Mop',[-1985,-907,0],-59)"
if old not in text and new not in text:raise RuntimeError('Mop source changed')
path.write_text(text.replace(old,new),encoding='utf8')
path=INCIDENT/'placements.json';backup(path);data=json.loads(path.read_text('utf8'))
next(p for p in data if p['id']=='Incident_CleaningMop')['position']=[-1985,-907,0];save_json(path,data)
print('TRANSIT_EQUIPMENT_AUTHORING_SOURCES_UPDATED')
