"""Freeze the surrounding final asset choices so full rebuilds no longer replay old passes."""
from pathlib import Path
import json
ROOT=Path(__file__).resolve().parents[1]
source=json.loads((ROOT/'Config/sources.json').read_text());scene=json.loads((ROOT/'Sources/original-scene-inputs.json').read_text())
owned={e['old_actor'] for e in source['components'] if e.get('old_actor')}|{source['legacy_cable'],source['legacy_light']}
rows=[r for r in scene['actors'] if r['label'] not in owned]
path=ROOT/'Config/surroundings.json'
if not path.exists():path.write_text(json.dumps(dict(actors=rows,retired_lights=['DGN_AV2_Light_Workshop','DGN_Room_WS_TaskLightSource']),indent=2),encoding='utf-8')
cfg=json.loads((ROOT/'Config/workbench.json').read_text(encoding='utf-8'))
catalog={'id':cfg['id'],'root_front_axis':'-X','local_footprint_cm':{'x':[-259,0],'y':[0,259]},'table_height_cm':cfg['table_height_cm'],
         'variants':{k:'/Game/Dungeons/AtmosphereV2/RoomInteriors/WorkbenchKit/Blueprints/BP_Workbench_'+k for k in cfg['variants']},
         'supports':cfg['supports'],'operator_clearance':cfg['operator_clearance'],'runtime_python_required':False,'random_dungeon_registration':'not_changed'}
(ROOT/'Authored/runtime-catalog.json').write_text(json.dumps(catalog,indent=2),encoding='utf-8')
print('WORKBENCH_CURRENT_DEFINITION_WRITTEN')
