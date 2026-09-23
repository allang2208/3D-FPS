"""Create runtime room data from authored recipes and completed import receipts."""
import json,math,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
cfg=json.loads((ROOT/'Config/rooms.json').read_text(encoding='utf-8'))
man=json.loads((ROOT/'Authored/manifest.json').read_text(encoding='utf-8'))
prepare_only='--prepare-only' in sys.argv
paths={} if prepare_only else json.loads((ROOT/'Receipts/import.json').read_text(encoding='utf-8'))['meshes']
destination='/Game/Dungeons/VentFreight20260922/Meshes/'
def vec(p):return [p[0]*100,-p[1]*100,(p[2] if len(p)>2 else 0)*100]
modules=[]
for room in cfg['rooms']:
    points=[vec(p) for p in room['footprint']];rid=room['id']
    m=dict(id=rid,min=[min(p[0] for p in points)-18,min(p[1] for p in points)-18,-25],max=[max(p[0] for p in points)+18,max(p[1] for p in points)+18,(room['height_m']+.25)*100],parts=[],ports=[],lights=[],anchors=[])
    # Occupancy is the whole architecture, including solid core and loading platform.
    m['cells']=[dict(min=[r[0]*100-18,-r[3]*100-18,-25],max=[r[2]*100+18,-r[1]*100+18,(room['height_m']+.25)*100]) for r in room['floors']]
    for o in room['openings']:
        a=room['footprint'][o['edge']];b=room['footprint'][(o['edge']+1)%len(room['footprint'])]
        dx,dy=b[0]-a[0],b[1]-a[1];length=math.hypot(dx,dy)
        m['ports'].append(dict(id=o['id'],position=vec([a[0]+dx/length*o['center'],a[1]+dy/length*o['center'],0]),normal=[dy/length,dx/length,0],width=o['width']*100,height=o['height']*100))
    for obj in man['objects']:
        if obj['room']==rid:
            mesh_path=destination+obj['name'] if prepare_only else paths[obj['name']]
            m['parts'].append(dict(mesh=mesh_path,position=[0,0,0],scale=[1,1,1],yaw=0,collision=obj['collision'],fluid=False,materials=[]))
    for index,l in enumerate(room['lights']):
        p=l['at'][:];p[2]-=.085
        m['lights'].append(dict(position=vec(p),intensity=l['lumens'],radius=l['radius_cm'],color=[1,.64,.36] if l['warm'] else [.73,.84,1]))
    m['anchors']=[dict(position=vec(a['at']),role=a['role']) for a in room['anchors']]
    modules.append(m)
extension=dict(version=1,room_ids=[m['id'] for m in modules],modules=modules)
(ROOT/'Config/modules.json').write_text(json.dumps(extension,ensure_ascii=False,indent=2),encoding='utf-8')
registry=ROOT.parent/'DungeonRoutes20260922/Config/room-extensions.json'
if not prepare_only:
    entries=json.loads(registry.read_text(encoding='utf-8')) if registry.exists() else []
    relative='DungeonVentFreight20260922/Config/modules.json'
    if relative not in entries:entries.append(relative)
    registry.write_text(json.dumps(entries,indent=2),encoding='utf-8')
print('ROOM_EXTENSION_PREPARED_NOT_REGISTERED' if prepare_only else 'ROOM_EXTENSION_REGISTERED',extension['room_ids'])
