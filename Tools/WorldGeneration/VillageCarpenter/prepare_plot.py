"""Update plot 04 and its footprint, working yard and pedestrian approach."""
import copy
import json
import math
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SOURCE = ROOT / 'SourceAssets/TemperateHillsVillage'
plan_file = SOURCE / 'layout.json'
kit_file = SOURCE / 'house-pieces.json'
plan = json.loads(plan_file.read_text(encoding='utf-8'))
kit = json.loads(kit_file.read_text(encoding='utf-8'))
house = next(row for row in plan['houses'] if row[0] == '04')
model = 'SL_Carpenter_Workshop'
if house[2] not in ('SL_Packed_HouseTypeC_00A', model):
    raise RuntimeError('Plot 04 has been reassigned to ' + house[2])

# The road painter consumes floor extents, wall height and a doorway. The actual
# two-storey shell is assembled from the same loft kit by carpenter_shell.py.
parts = []
for source_part in kit['SL_Blacksmith_LoftR3']:
    name = source_part['mesh'].split('.')[-1]
    if name.startswith('SM_WoodenFloor_') or name == 'SM_H_OldWall_Triangle_00A':
        parts.append(source_part)
door = copy.deepcopy(next(p for p in kit['SL_Blacksmith_LoftR3'] if 'OldWall_Door' in p['mesh']))
door['pos'][:2] = [150 / plan['house_scale'], -389 / plan['house_scale']]
door['rot'] = [0., 0., 0.]
parts.append(door)
kit[model] = parts
house[1:3] = ['木工工坊', model]
house[5] = 7  # Same street-facing normal as the old cottage's side doorway.
plan['carpenter'] = dict(house=house[0], default_state='ruined', station_id='woodworking_bench',
                         original_model='SL_Packed_HouseTypeC_00A', original_yaw=97,
                         loft_floor_cm=360)
# Enter through the break at the east end of the existing drystone garden wall.
plan.setdefault('house_approaches', {})['04'] = [[-31.65,6.8],[-30.15,4.6],[-28.35,4.05],[-27.0,3.50],[-26.85,1.65]]
areas = [r for r in plan.get('service_clearings', []) if r.get('owner') != 'Carpenter04']
a = math.radians(house[5])
for x, y, hx, hy, soil in [(0,-6.24,4.06,2.31,.82), (5.24,-1.55,.95,2.46,.76)]:
    areas.append(dict(owner='Carpenter04', center=[house[3]+x*math.cos(a)-y*math.sin(a),
                                                    house[4]+x*math.sin(a)+y*math.cos(a)],
                      half=[hx,hy], yaw=house[5], soil_weight=soil))
plan['service_clearings'] = areas
kit_file.write_text(json.dumps(kit,ensure_ascii=False,separators=(',',':')),encoding='utf-8')
plan_file.write_text(json.dumps(plan,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
subprocess.run([sys.executable,str(ROOT/'Tools/WorldGeneration/AbandonedVillage/draw_plan.py'),'--data-only'],check=True)
