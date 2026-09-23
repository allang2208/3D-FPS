"""Emit reusable room sockets from the same perimeter/opening authoring data."""
import json,math
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
cfg=json.loads((ROOT/'Config/rooms.json').read_text(encoding='utf-8'))
result={'unit':'centimetres','coordinate_system':'Unreal +Z up','rooms':{},'route':[
    ['existing_service_link.end','Distribution.entry'],
    ['Distribution.exit','Distribution_Drainage.start'],
    ['Distribution_Drainage.end','Drainage.entry'],
    ['Drainage.exit','Drainage_ShoredBreach.start'],
    ['Drainage_ShoredBreach.end','ShoredBreach.entry']
]}
for room in cfg['rooms']:
    sockets=[];outline=room['footprint'];origin=room['origin_m']
    for op in room['openings']:
        a=outline[op['edge']];b=outline[(op['edge']+1)%len(outline)]
        length=math.hypot(b[0]-a[0],b[1]-a[1]);dx=(b[0]-a[0])/length;dy=(b[1]-a[1])/length
        local=[a[0]+dx*op['center'],a[1]+dy*op['center'],0]
        sockets.append({'id':op['id'],'local_cm':[local[0]*100,-local[1]*100,0],
            'world_cm':[(origin[0]+local[0])*100,-(origin[1]+local[1])*100,origin[2]*100],
            'outward_yaw':math.degrees(math.atan2(dx,dy)),
            'clear_width_cm':op['width']*100,'clear_height_cm':op['height']*100})
    result['rooms'][room['id']]={'origin_cm':[origin[0]*100,-origin[1]*100,origin[2]*100],'sockets':sockets}
for link in cfg['links']:
    origin=link['origin_m'];dx=link['length'] if link['axis']=='x' else 0;dy=link['length'] if link['axis']=='y' else 0
    forward=math.degrees(math.atan2(-dy,dx));sockets=[]
    for name,local,yaw in [('start',[0,0,0],forward+180),('end',[dx,dy,0],forward)]:
        sockets.append({'id':name,'local_cm':[local[0]*100,-local[1]*100,0],
            'world_cm':[(origin[0]+local[0])*100,-(origin[1]+local[1])*100,origin[2]*100],
            'outward_yaw':yaw,'clear_width_cm':link['width']*100,'clear_height_cm':link['height']*100})
    result['rooms'][link['id']]={'origin_cm':[origin[0]*100,-origin[1]*100,origin[2]*100],'sockets':sockets}
(ROOT/'Authored/interfaces.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
print('ROOM_INTERFACE_METADATA_WRITTEN')
