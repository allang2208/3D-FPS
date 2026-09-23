"""Cookable authored-module catalogue. Positions and ports use UE centimetres."""
import json,math,runpy
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];SOURCE=ROOT.parent/'DungeonRoomShells20260922'
old=json.loads((SOURCE/'Config/rooms.json').read_text(encoding='utf-8'));new=json.loads((ROOT/'Config/rooms.json').read_text(encoding='utf-8'))
oldman=json.loads((SOURCE/'Authored/manifest.json').read_text());newman=json.loads((ROOT/'Authored/manifest.json').read_text())
oldpaths=json.loads((SOURCE/'Receipts/import.json').read_text())['meshes'];newpaths=json.loads((ROOT/'Receipts/import.json').read_text())['meshes']
def vec(p):return [100*p[0],-100*p[1],100*(p[2] if len(p)>2 else 0)]
def part(mesh,p=(0,0,0),collision=True,fluid=False,materials=()):return dict(mesh=mesh,position=vec(p),scale=[1,1,1],yaw=0,collision=collision,fluid=fluid,materials=list(materials))
modules=[]
for room in old['rooms'][:2]+new['rooms']:
    rid=room['id'];man,paths=(oldman,oldpaths) if rid in ('Distribution','Drainage') else (newman,newpaths)
    points=room['footprint'][:]
    if 'breach' in room:
        x0,y0,x1,y1=room['breach']['pocket'];points.extend([[x0,y0],[x1,y1]])
    vertices=[vec(p) for p in points]
    m=dict(id=rid,min=[min(v[0] for v in vertices)-18,min(v[1] for v in vertices)-18,-80],max=[max(v[0] for v in vertices)+18,max(v[1] for v in vertices)+18,(room['height_m']+.25)*100],parts=[],ports=[],lights=[],anchors=[])
    m['cells']=[dict(min=[rect[0]*100-18,-rect[3]*100-18,-80],max=[rect[2]*100+18,-rect[1]*100+18,(room['height_m']+.25)*100]) for rect in room['floors']]
    for opening in room['openings']:
        edge=opening['edge'];a=room['footprint'][edge];b=room['footprint'][(edge+1)%len(room['footprint'])];dx,dy=b[0]-a[0],b[1]-a[1];length=math.hypot(dx,dy)
        m['ports'].append(dict(position=vec([a[0]+dx/length*opening['center'],a[1]+dy/length*opening['center'],0]),normal=[dy/length,dx/length,0],width=opening['width']*100,height=opening['height']*100,id=opening['id']))
    # Junction order is entry, forward, left, right; the planner reserves all three.
    if rid=='Junction':m['ports'].sort(key=lambda p:['entry','forward','left','right'].index(p['id']))
    for obj in man['objects']:
        if obj['room']==rid:m['parts'].append(part(paths[obj['name']],collision=obj['collision']))
    for lamp in room['lights']:
        p=lamp['at'][:];p[2]-=.085
        m['lights'].append(dict(position=vec(p),intensity=lamp['lumens'],radius=lamp['radius_cm'],color=[1,.64,.36] if lamp['warm'] else [.73,.84,1]))
    m['anchors']=[dict(position=vec(a['at']),role=a['role']) for a in room['anchors']]
    if rid=='Drainage':
        t=room['trench'];hazard=t['hazard'];x0,y0,x1,y1=t['rect'];h=part(hazard['mesh'],[(x0+x1)/2,(y0+y1)/2,-t['depth']],False,True,[hazard['material']]);h.update(half_size=hazard['half_size_cm'],radial=False);m['parts'].append(h)
        for i in room['pipe_slime']['objects']:
            overrides=[i['material_override']] if i.get('material_override') else []
            h=part(i['destination']+'/'+i['name'],i['local_m'],False,True,overrides)
            if i['half_size_cm']:h.update(half_size=[v*.95 for v in i['half_size_cm']],radial=i.get('radial_footprint',False))
            m['parts'].append(h)
    modules.append(m)
transit=dict(id='Transit',min=[-164,-400,-22],max=[164,0,333],ports=[dict(position=[0,0,0],normal=[0,1,0]),dict(position=[0,-400,0],normal=[0,-1,0])],parts=[part(newpaths[i['name']],collision=i['collision']) for i in newman['objects'] if i['room']=='Transit'],lights=[dict(position=[0,-200,284.5],intensity=500,radius=220,color=[1,.64,.36])],anchors=[])
modules.append(transit)
transit['cells']=[dict(min=transit['min'],max=transit['max'])]
threshold=dict(id='Threshold',min=[-164,-80,-22],max=[164,0,333],ports=[dict(position=[0,0,0],normal=[0,1,0]),dict(position=[0,-80,0],normal=[0,-1,0])],parts=[part(newpaths[i['name']],collision=i['collision']) for i in newman['objects'] if i['room']=='Threshold'],lights=[],anchors=[])
threshold['cells']=[dict(min=threshold['min'],max=threshold['max'])];modules.append(threshold)
for module in (transit,threshold):
    link=next(x for x in new['links'] if x['id']==module['id'])
    # Link width is measured between wall centres; ports describe the actual usable aperture.
    for port in module['ports']:
        port.update(width=(link['width']-new['style']['wall_thickness'])*100,height=link['height']*100)
rules=json.loads((ROOT/'Config/rules.json').read_text())
catalog=dict(version=1,min_rooms=rules['rooms_per_group'][0],max_rooms=rules['rooms_per_group'][1],group_links=round(rules['group_corridor_m']/4),branch_links=round(rules['branch_lead_m']/4),start_position=rules['start_exit_cm'],start_normal=rules['start_direction'],reserved_min=rules['reserved_start_cm'][0],reserved_max=rules['reserved_start_cm'][1],modules=modules)
catalog['start_connection']=json.loads((ROOT/'Config/start_connection.json').read_text())
treasure=ROOT.parent/'DungeonTreasure20260922'
if (treasure/'Receipts/import.json').exists():
    extension=runpy.run_path(str(treasure/'Scripts/extend_catalog.py'))
    catalog=extension['extend'](catalog)
extension_list=ROOT/'Config/room-extensions.json'
if extension_list.exists():
    catalog['room_ids']=['Distribution','Drainage','ShoredBreach']
    for relative_path in json.loads(extension_list.read_text(encoding='utf-8')):
        extension=json.loads((ROOT.parent/relative_path).read_text(encoding='utf-8'))
        ids={m['id'] for m in extension['modules']}
        catalog['modules']=[m for m in catalog['modules'] if m['id'] not in ids]+extension['modules']
        catalog['room_ids']=list(dict.fromkeys(catalog['room_ids']+extension['room_ids']))
repair=ROOT.parent/'DungeonRouteRepairs20260922/Scripts/extend_catalog.py'
if repair.exists() and (repair.parents[1]/'Receipts/import.json').exists():
    catalog=runpy.run_path(str(repair))['extend'](catalog)
module_ids=[m['id'] for m in catalog['modules']]
if len(module_ids)!=len(set(module_ids)):raise RuntimeError('Duplicate dungeon module IDs')
missing=set(catalog.get('room_ids',[]))-set(module_ids)
if missing:raise RuntimeError('Missing room modules: '+', '.join(sorted(missing)))
(ROOT/'Config/catalog.json').write_text(json.dumps(catalog,ensure_ascii=False,indent=2),encoding='utf-8')
print('AUTHORED_CATALOG_WRITTEN',len(catalog['modules']))
