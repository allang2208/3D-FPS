"""Publish the approved rigid station as one rare combat module (UE centimetres)."""
import copy,json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

def read(path):return json.loads(path.read_text(encoding='utf-8'))
def point(p):return [round(p[0]*100,4),round(-p[1]*100,4),round(p[2]*100,4)]
def cell(lo,hi):
    a,b=point(lo),point(hi)
    return dict(min=[min(a[i],b[i]) for i in range(3)],max=[max(a[i],b[i]) for i in range(3)])
def part(mesh,position=(0,0,0),collision=True,yaw=0):
    return dict(mesh=mesh,position=point(position),scale=[1,1,1],yaw=yaw,
                collision=collision,affects_navigation=collision,fluid=False,materials=[])

def extend(catalog):
    cfg=read(ROOT/'Config/room.json');policy=read(ROOT/'Config/pool.json')
    manifest=read(ROOT/'Authored/manifest.json');saved=read(ROOT/'Receipts/install.json')
    if saved.get('revision')!=cfg['revision'] or saved.get('stage') not in ('sample_map_saved','meshes_saved'):
        raise RuntimeError('Import the current station geometry before pool installation')
    result=copy.deepcopy(catalog);base=cfg['ue_base'];rid=cfg['id']
    pieces=[]
    for obj in manifest['objects']:
        if obj.get('sample_only'):continue
        path=base+'/Meshes/'+obj['name']
        if obj['name'] not in saved['meshes']:raise RuntimeError('Unsaved station mesh: '+path)
        pieces.append(part(path,collision=obj['collision']))
    for spec in cfg['reused_parts']:
        pieces.append(part(spec['mesh'],spec['position'],spec['collision'],spec['yaw']))
    lamps=[]
    for spec in cfg['lights']:
        fixture='/Game/Dungeons/IndustrialV1/Meshes/SM_CeilingLamp_'+('Warm' if spec['warm'] else 'Cool')
        pieces.append(part(fixture,spec['position'],False))
        p=spec['position'][:];p[2]-=.125
        lamps.append(dict(position=point(p),intensity=spec['lumens'],radius=spec['radius_cm'],
            optimized_radius_cm=spec['radius_cm'],color=[1,.75,.48] if spec['warm'] else [.66,.80,1],
            role=spec['role'],type='point',cast_shadows=spec['cast_shadows'],
            max_draw_distance_cm=spec['max_draw_distance_cm'],fade_range_cm=spec['fade_range_cm']))
    cells=[cell(c['min'],c['max']) for c in cfg['cells_m']]
    ports=[dict(id=p['id'],position=point(p['position']),normal=[p['normal'][0],-p['normal'][1],p['normal'][2]],
                width=p['width']*100,height=p['height']*100) for p in cfg['ports']]
    walk=[]
    for area in cfg['clear_areas_m']:
        x0,y0,x1,y1=area['rect'];walk.append(cell([x0,y0,-.05],[x1,y1,2.8]))
    anchors=[dict(position=point(p),role='encounter_platform') for p in policy['spawn_anchors_m']]
    source=next(m for m in result['modules'] if m['id']==policy['spawn_pool_from'])
    spawn=copy.deepcopy(source['spawn'])
    spawn.update(source='DungeonTransitStation20260928',count=policy['spawn_count'],sealed_encounter=True,
                 anchor_roles=['encounter_platform'],theme='abandoned_transit')
    module=dict(id=rid,family_id=rid,role='room',encounter_role='special_combat',revision=cfg['revision'],
        min=[min(c['min'][i] for c in cells) for i in range(3)],
        max=[max(c['max'][i] for c in cells) for i in range(3)],cells=cells,ports=ports,port_pairs=[[0,1]],
        parts=pieces,lights=lamps,anchors=anchors,walk_mask=walk,
        walk_polyline=[point(p) for p in policy['walk_polyline_m']],spawn=spawn,selection=policy['selection'])
    result['modules']=[m for m in result['modules'] if m['id']!=rid]+[module]
    result['room_ids']=list(dict.fromkeys(result['room_ids']+[rid]))
    return result

def asset_paths(module):
    for p in module['parts']:yield p['mesh']
    for entry in module['spawn']['pool']:yield entry['class']

if __name__=='__main__':
    catalog=extend(read(ROOT.parent/'DungeonRoutes20260922/Config/catalog.json'))
    module=next(m for m in catalog['modules'] if m['id']=='AbandonedTransitStation')
    (ROOT/'Config/module.json').write_text(json.dumps(module,ensure_ascii=False,indent=2),encoding='utf-8')
    print('STATION_POOL_MODULE_AUTHORED',module['id'])
