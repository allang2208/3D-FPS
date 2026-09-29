"""Maintain sealed three-way junctions and mission routing; rooms are independent modules."""
import copy,json,math
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def read(path):return json.loads(path.read_text(encoding='utf-8'))

def extend(catalog):
    receipt=read(ROOT/'Receipts/import.json')
    if receipt['stage']!='meshes_saved':raise RuntimeError('Save the door seals before installing recipes')
    result=copy.deepcopy(catalog)
    # Refresh source-room pools before copying them into shared interiors.
    spawn=ROOT.parent/'DungeonSpawn20260925'
    spawn_saved=spawn/'Receipts/install.json'
    if spawn_saved.exists() and read(spawn_saved).get('stage')=='map_saved':
        import runpy
        result=runpy.run_path(str(spawn/'Scripts/extend_catalog.py'))['extend'](result)
    modules={m['id']:m for m in result['modules']}
    seal_objects=read(ROOT/'Authored/manifest.json')['objects']
    def seal(port):
        yaw=math.degrees(math.atan2(port['normal'][1],port['normal'][0]))-90
        return [dict(mesh=receipt['meshes'][o['name']],position=port['position'][:],scale=[1,1,1],yaw=yaw,
            collision=o['collision'],fluid=False,materials=[],assembly_role=o['kind']) for o in seal_objects]
    fork_modules=[]
    for side,index,closed in [('Left',2,3),('Right',3,2)]:
        m=copy.deepcopy(modules['Junction']);all_ports=m['ports']
        m.update(id='Fork'+side,role='junction',ports=[all_ports[i] for i in (0,1,index)])
        m['parts']+=seal(all_ports[closed]);fork_modules.append(m)
    replaced={m['id'] for m in fork_modules}
    result['modules']=[m for m in result['modules'] if m['id'] not in replaced]+fork_modules
    result['mission_rules']=dict(version=1,grammars=['parallel_three_way','staggered_left','staggered_right'],
        corridor_cm_per_room=900,fixed_corridor_cm=14000,route_estimate_max_cm=42000,
        optional_loop_goal=[1,2],risk_route='shortest_branch',risk_level_bonus=2,risk_reward_multiplier=1.5)
    result.update(generator_version=max(5,result.get('generator_version',1)),strict_ports=True)
    # Keep later facility scene recipes when rebuilding this earlier composition layer.
    facility=ROOT.parent/'DungeonFacilityScenes20260927'
    saved=facility/'Receipts/install.json'
    if saved.exists() and read(saved).get('stage')=='map_saved':
        import runpy
        result=runpy.run_path(str(facility/'Scripts/extend_catalog.py'))['extend'](result)
    return result
