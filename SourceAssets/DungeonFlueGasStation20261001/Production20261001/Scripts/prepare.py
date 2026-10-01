"""Promote the user-approved station; keep it out of unordered room draws."""
import copy,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];HALL=ROOT.parent;PROJECT=HALL.parents[1]
for folder in ('Config','Receipts','Backup'):(ROOT/folder).mkdir(exist_ok=True)
def read(p):return json.loads(p.read_text('utf-8-sig'))
def write(p,v):p.write_text(json.dumps(v,ensure_ascii=False,indent=2),encoding='utf-8')
m=read(HALL/'Config/module-draft.json');m.update(m.pop('bounds'))
m.pop('authoring_only',None);m.pop('kind',None)
m.update(role='room',encounter_role='special_combat',revision='accepted_flue_gas_20261001',runtime_actors=[],
    selection=dict(chance_per_run=1.,max_per_run=1),walk_polyline=[[-1600,800,5],[0,800,5],[1600,800,5]],
    walk_mask=[dict(min=[-435,-780,-5],max=[435,900,40])])
m['route_intent'].update(registration='production_catalog_reserved_for_fixed_themed_route',predecessor='AbandonedIncineratorHall')
catalog=read(PROJECT/'SourceAssets/DungeonRoutes20260922/Config/catalog.json')
spawn=copy.deepcopy(next(x for x in catalog['modules'] if x['id']=='AbandonedAnatomyTheatre')['spawn'])
spawn.update(source='DungeonFlueGasStation20261001',theme='abandoned_flue_gas_station',count=[4,6],anchor_roles=['flue_gas_combat'])
m['spawn']=spawn
for l in m['lights']:l.update(max_draw_distance=3200,max_distance_fade_range=500)
write(ROOT/'Config/module.json',m)
print('FLUE_GAS_PRODUCTION_MODULE_WRITTEN')
