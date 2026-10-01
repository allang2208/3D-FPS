"""One independent incineration hall; author coordinates in metres, UE=(x,-y,z)*100."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for name in ('Config', 'Authored', 'Receipts'):
    (ROOT / name).mkdir(parents=True, exist_ok=True)
cfg = {
    'id': 'AbandonedIncineratorHall',
    'revision': 'incinerator_architecture_v1_20260929',
    'phase': 'production_pool',
    'pool_install_script': 'Pool20260930/Scripts/install_pool.py',
    'pool_module': 'Pool20260930/Config/module.json',
    'retirement_manifest': 'trash/incinerator-subject-retired-20260930/manifest.json',
    'ue_base': '/Game/Dungeons/IncineratorHall20260929',
    'lower_level_layout': 'MorgueOpenPlan20260930/Config/layout.json',
    'coordinate_system': 'Blender metres; UE centimetres (x,-y,z)',
    'hall': {'outline': [[-14,-7.5],[-9,-10.5],[9,-10.5],[14,-7.5],[14,7.5],[9,10.5],[-14,10.5]],
             'height': 8.0, 'wall_thickness': .28},
    'ports': [{'id': 'receiving', 'position': [-16,0,0], 'normal': [-1,0,0], 'width': 3., 'height': 2.8},
              {'id': 'service', 'position': [16,0,0], 'normal': [1,0,0], 'width': 3., 'height': 2.8}],
    'furnaces': {'centres_x': [-6.,0.,6.], 'body_y': [-10.1,-7.25], 'height': 4.7,
                 'bay_width': 4.6, 'opening_width': 2.2, 'opening_height': 2.6,
                 'loading_length': 2.25, 'operating': False},
    'observation': {'x': [-7.,7.], 'y': [5.6,10.1], 'top': 2.4,
                    'stairs_width': 2.6, 'stairs_centre_y': 7., 'steps': 16, 'going': .30, 'rise': .15},
    'ash_pit': {'rect': [-13.0,-7.65,-8.6,-2.65], 'floor': -1.2,
                'recovery_steps': 8, 'recovery_going': .30, 'recovery_width': 1.6,
                'recovery_centre_x': -11.95,
                'equipment_revision': 'AshStation20260930',
                'receiver_position_m': [-9.8,-7.03,-1.2],
                'front_service_lane_min_m': 1.2},
    'clear_areas_m': [{'name': 'continuous seven-metre working aisle', 'rect': [-13.6,-2.3,13.6,4.7]},
                      {'name': 'furnace apron', 'rect': [-8.7,-4.8,9.,-2.3]}],
    'player_start_m': [-14.65,0,.98], 'player_yaw': 0.,
    'return_anchor_m': [-15.75,0,0],
    'furnishing_reservations': [
        {'id': 'furnace_door_mechanics', 'centres_m': [[x,-7.25,0] for x in (-6,0,6)], 'max_width_m': 3.22, 'status': 'precision_v1_installed'},
        {'id': 'loading_trolleys', 'centres_m': [[-6,-3.6,0],[6,-3.6,0]], 'max_footprint_m': [1.8,2.], 'status': 'one_roller_cart_and_one_lidded_hopper_installed'},
        {'id': 'control_console', 'rect': [-3.,8.6,1.,9.9], 'floor': 2.4},
        {'id': 'waste_bins', 'rect': [10.,-5.7,12.7,-3.2], 'floor': 0.},
    ],
    'lights': [], 'tests_run': False, 'random_pool_registered': True,
    'environment_damage': False,
}
for index, (x,y,z,warm,lumens,shadow,role) in enumerate([
    (-10,1.0,6.4,False,2100,True,'entry'),(-3,1.,6.4,False,2400,False,'fill'),
    (4,1.,6.4,False,2400,True,'key'),(11,1.,6.4,False,1800,False,'exit'),
    (-6,-5.0,6.2,True,1250,True,'equipment'),(0,-5.,6.2,True,1250,False,'equipment'),
    (6,-5.,6.2,True,1250,False,'equipment'),(-4,8.2,6.4,False,1450,False,'gallery'),
    (4,8.2,6.4,False,1450,True,'gallery'),(-15,0,3.05,False,500,False,'entry'),
    (15,0,3.05,False,500,False,'exit'),(-10.5,-4.8,3.0,True,450,False,'pit')]):
    cfg['lights'].append(dict(id=f'Incinerator_{index:02}',position=[x,y,z],warm=warm,lumens=lumens,
       radius_cm=850 if z>4 else 420,role=role,cast_shadows=shadow,max_draw_distance_cm=3400,fade_range_cm=650))
(ROOT/'Config/room.json').write_text(json.dumps(cfg,ensure_ascii=False,indent=2),encoding='utf-8')
print('INCINERATOR_DESIGN_SAVED',cfg['id'])
