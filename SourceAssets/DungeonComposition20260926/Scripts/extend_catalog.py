"""Shared, compatible shell/interior recipes; never regenerate complete room meshes."""
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
    wall_kinds=('_Shell','_Tiles','_Frames','_Floors','_Ceilings')
    def walls(part):return part['mesh'].split('.')[0].endswith(wall_kinds)
    seal_objects=read(ROOT/'Authored/manifest.json')['objects']
    def seal(port):
        yaw=math.degrees(math.atan2(port['normal'][1],port['normal'][0]))-90
        return [dict(mesh=receipt['meshes'][o['name']],position=port['position'][:],scale=[1,1,1],yaw=yaw,
            collision=o['collision'],fluid=False,materials=[],assembly_role=o['kind']) for o in seal_objects]
    shells={};interiors={};recipes=[]
    base=modules['VentilationLoop']
    for side_id in ('North','West'):
        side=next(s for s in base['side_sockets'] if s['id']==side_id)
        ports=copy.deepcopy(base['ports'])+[dict(id='alternate_'+side_id,position=side['position'],normal=side['normal'],width=side['width'],height=side['height'])]
        shell={k:copy.deepcopy(base[k]) for k in ('min','max','cells','role') if k in base}
        shared_slabs=[copy.deepcopy(p) for p in base['parts'] if p['mesh'].split('.')[0].endswith(('_Floors','_Ceilings'))]
        shell.update(parts=copy.deepcopy(side['parts'])+shared_slabs,ports=ports,
            port_pairs=[[0,1],[0,2],[1,2]],closed_port_parts=[dict(port_index=i,parts=seal(p)) for i,p in enumerate(ports)],
            side_sockets=[dict(p,id='Main'+str(i),port_index=i,parts=[],replace_suffixes=[]) for i,p in enumerate(ports)])
        # Structural variants use the same footprint but retain their deeper floor slab.
        shell['min'][2]=-80
        for cell in shell['cells']:cell['min'][2]=-80
        shells['vent_'+side_id.lower()]=shell
    for source_id,interior_id in [('VentilationLoop','center'),('VentilationLoop_WestCore','west'),('VentilationLoop_EastCore','east')]:
        source=modules[source_id]
        interior={k:copy.deepcopy(v) for k,v in source.items() if k not in {
            'id','family_id','parts','ports','port_pairs','side_sockets','min','max','cells','role','structural_variant'}}
        interior['parts']=[copy.deepcopy(p) for p in source['parts'] if not walls(p)]
        interior['encounter_anchors']=copy.deepcopy(source.get('anchors',[]))
        interior['compatibility_shells']=['vent_north','vent_west']
        # Walk mask is the authored ring floor, not the whole room's occupancy AABB.
        interior['walk_mask']=[dict(min=[180,-400,0],max=[1620,-180,20]),dict(min=[180,-1420,0],max=[400,-180,20]),
            dict(min=[1400,-1420,0],max=[1620,-180,20]),dict(min=[180,-1420,0],max=[1620,-1200,20])]
        interiors['vent_'+interior_id]=interior
        for side in ('north','west'):
            recipes.append(dict(id='VentilationLoop_Recipe_'+side+'_'+interior_id,family_id='VentilationLoop',
                shell_id='vent_'+side,interior_recipe_id='vent_'+interior_id,role='combat_room'))
    fork_modules=[]
    for side,index,closed in [('Left',2,3),('Right',3,2)]:
        m=copy.deepcopy(modules['Junction']);all_ports=m['ports']
        m.update(id='Fork'+side,role='junction',ports=[all_ports[i] for i in (0,1,index)])
        m['parts']+=seal(all_ports[closed]);fork_modules.append(m)
    replaced={m['id'] for m in recipes+fork_modules}
    result['modules']=[m for m in result['modules'] if m['id'] not in replaced]+recipes+fork_modules
    result['room_ids']=[x for x in result['room_ids'] if not x.startswith('VentilationLoop')]+[m['id'] for m in recipes]
    result['room_recipe_library']=dict(version=1,shells=shells,interiors=interiors)
    result['mission_rules']=dict(version=1,grammars=['parallel_three_way','staggered_left','staggered_right'],
        corridor_cm_per_room=900,fixed_corridor_cm=14000,route_estimate_max_cm=42000,
        optional_loop_goal=[1,2],risk_route='shortest_branch',risk_level_bonus=2,risk_reward_multiplier=1.5)
    result.update(generator_version=5,room_composition_version=1,strict_ports=True)
    # Keep later facility scene recipes when rebuilding this earlier composition layer.
    facility=ROOT.parent/'DungeonFacilityScenes20260927'
    saved=facility/'Receipts/install.json'
    if saved.exists() and read(saved).get('stage')=='map_saved':
        import runpy
        result=runpy.run_path(str(facility/'Scripts/extend_catalog.py'))['extend'](result)
    return result
