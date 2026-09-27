"""Produce only the stair lighting group; no structural mesh rebuild or rendering."""
import json,sys
from pathlib import Path
import bpy

ROOT=Path(__file__).resolve().parents[1]
UNDERGROUND=ROOT.parent/'DungeonUnderground20260923'
for folder in ('Authored','Before','Receipts'):(ROOT/folder).mkdir(parents=True,exist_ok=True)
boss=ROOT.parent/'DungeonBossHall20260922/Scripts/author.py'
scope={'__file__':str(boss),'__name__':'stair_lighting_library'}
exec(compile(boss.read_text(encoding='utf-8').split('# Floor, high walls',1)[0],str(boss),'exec'),scope)
H=scope['H'];H['OUT']=ROOT/'Authored';H['RECORDS']=[];H['LIGHTS']=[];H['GROUPS']={}
H['ROOM']={'id':'StairDrop1080','origin_m':[0,0,0],'machines':[]};H['PIPE_RUNS']=[]
sys.path.insert(0,str(UNDERGROUND/'Scripts'))
from lighting_layout import build,light_records
lamps=build(H)
from export_boss import export
export(H)
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'Authored/StairPlatformLighting.blend'))
(ROOT/'Authored/manifest.json').write_text(json.dumps({'objects':H['RECORDS']},indent=2),encoding='utf-8')

# Preserve all unrelated module data in both the extension and assembled catalog.
for path in (UNDERGROUND/'Config/modules.json',ROOT.parent/'DungeonRoutes20260922/Config/catalog.json'):
    data=json.loads(path.read_text(encoding='utf-8'))
    before=ROOT/'Before'/('underground-modules.json' if path.name=='modules.json' else 'routes-catalog.json')
    if not before.exists():before.write_text(path.read_text(encoding='utf-8'),encoding='utf-8')
    for module in data['modules']:
        if module['id']=='StairDrop1080':module['lights']=light_records();module['lighting_revision']='stair-platform-lights-20260927'
    path.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
source_manifest=UNDERGROUND/'Authored/manifest.json'
data=json.loads(source_manifest.read_text(encoding='utf-8'))
for i,item in enumerate(data['objects']):
    if item['name']=='SM_RS_StairDrop1080_Fixtures':data['objects'][i]=H['RECORDS'][0]
source_manifest.write_text(json.dumps(data,indent=2),encoding='utf-8')
print('STAIR_LIGHTING_AUTHORED',len(lamps),'lamps; one fixture mesh',flush=True)
