"""Persist the requested lighting profile without regenerating any geometry."""
import json
import runpy
from pathlib import Path
ROOT=Path(__file__).resolve().parent
P=runpy.run_path(str(ROOT/'profile.py'))
PROJECT=P['PROJECT']
saved=[]
for group,folder in [('Reception','DungeonReceptionHall20261006'),('Transit','DungeonFacilityTransit20261007')]:
    root=PROJECT/'SourceAssets'/folder
    path=root/'Config/layout.json'
    backup=ROOT/'Backups/sources'/folder
    backup.mkdir(parents=True,exist_ok=True)
    for name in ('layout.json','module-draft.json'):
        source=root/'Config'/name
        target=backup/name
        if source.exists() and not target.exists():target.write_bytes(source.read_bytes())
    before=json.loads(path.read_text('utf8'))
    after=P['revise_layout'](before,group)
    path.write_text(json.dumps(after,ensure_ascii=False,indent=2),encoding='utf8')
    runpy.run_path(str(root/'draft.py'),run_name='__main__')
    saved.append(dict(group=group,lights=len(after['lights']),
        flicker=sum(p['fault']=='flicker' for p in after['lights']),dead=sum(p['fault']=='dead' for p in after['lights'])))
(ROOT/'Receipts/sources.json').write_text(json.dumps(saved,indent=2),encoding='utf8')
print('HALL_LIGHTING_RECIPES_SAVED',saved)
