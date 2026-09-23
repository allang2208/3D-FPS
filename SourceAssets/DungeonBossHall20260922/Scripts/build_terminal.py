"""Build the offline terminal catalogue; never register a boss as a random ordinary room."""
import json,math,copy
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
cfg=json.loads((ROOT/'Config/rooms.json').read_text(encoding='utf-8'))
manifest=json.loads((ROOT/'Authored/manifest.json').read_text(encoding='utf-8'))
routes=json.loads((ROOT.parent/'DungeonRoutes20260922/Config/catalog.json').read_text(encoding='utf-8'))
contract=json.loads((ROOT/'Config/terminal-assembly.json').read_text(encoding='utf-8'))
by_id={m['id']:m for m in routes['modules']}
def vec(p):return [p[0]*100,-p[1]*100,(p[2] if len(p)>2 else 0)*100]
room=cfg['rooms'][0]
boss=dict(id=room['id'],role='boss_terminal',min=[-1518,-2618,-25],max=[1518,18,865],
    cells=[dict(min=[-1518,-2618,-25],max=[1518,18,865])],parts=[],ports=[],lights=[],anchors=[])
for opening in room['openings']:
    a=room['footprint'][opening['edge']];b=room['footprint'][(opening['edge']+1)%len(room['footprint'])]
    dx,dy=b[0]-a[0],b[1]-a[1];length=math.hypot(dx,dy)
    boss['ports'].append(dict(id=opening['id'],position=vec([a[0]+dx/length*opening['center'],a[1]+dy/length*opening['center'],0]),normal=[dy/length,dx/length,0],width=opening['width']*100,height=opening['height']*100))
for item in manifest['objects']:
    boss['parts'].append(dict(mesh='/Game/Dungeons/BossHall20260922/Meshes/'+item['name'],position=[0,0,0],scale=[1,1,1],yaw=0,collision=item['collision'],fluid=False,materials=[]))
for l in room['lights']:
    p=l['at'][:];p[2]-=.085
    boss['lights'].append(dict(position=vec(p),intensity=l['lumens'],radius=l['radius_cm'],color=[1,.64,.36] if l['warm'] else [.73,.84,1],role=l['role']))
boss['anchors']=[dict(role=a['role'],position=vec(a['at'])) for a in room['anchors']]
confluence=copy.deepcopy(by_id['Junction']);confluence['id']='BossConfluence';confluence['role']='terminal_confluence'
port_ids={'left':'route_left','entry':'route_middle','right':'route_right','forward':'boss_out'}
for p in confluence['ports']:p['id']=port_ids[p['id']]
approach=copy.deepcopy(by_id['Transit']);approach['id']='BossApproach';approach['role']='terminal_connector'
for i,p in enumerate(approach['ports']):p['id']='entry' if i==0 else 'exit'
modules=[confluence,approach,boss]
instances=[dict(module=a['module'],position=vec(a['origin_m']),yaw=a['yaw'],scale=[1,1,1]) for a in contract['assembly']]
ports=[]
for p in confluence['ports']:
    if p['id'].startswith('route_'):
        external=copy.deepcopy(p);external['module']='BossConfluence'
        external['position']=[a+b for a,b in zip(p['position'],instances[0]['position'])]
        ports.append(external)
connected=bool(routes.get('boss_terminal_enabled'))
result=dict(version=1,status='imported_and_connected' if connected else 'authored_catalog',room_ids=[],terminal_ids=['BossPumpHall'],modules=modules,instances=instances,
    branch_inputs=ports,connections=contract['connections'],boss_count=1,
    min=[-1518,-2618,-25],max=[1518,1618,865],
    runtime_routing_connected=connected,integration_receipt='../DungeonBossIntegration20260923/Receipts/install.json',tests_run=False)
(ROOT/'Config/terminal-modules.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
(ROOT/'Sources/reused-module-snapshot.json').write_text(json.dumps(dict(catalog='DungeonRoutes20260922/Config/catalog.json',modules=[by_id['Junction'],by_id['Transit']]),ensure_ascii=False,indent=2),encoding='utf-8')
print('BOSS_TERMINAL_CATALOG_AUTHORED',len(boss['parts']),'new meshes; 3 branch input ports; not registered')
