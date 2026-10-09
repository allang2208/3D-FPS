"""Place only locally verified original assets; preserve centimetre assembly contracts.
Rerun after prepare_design.py. This never rebuilds existing props or shaders.
"""
import json,math
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];B=ROOT/'References/ReuseBundle';P=ROOT/'Config/scene.json';c=json.loads(P.read_text());h=json.loads((B/'HANDOFF.json').read_text());a={i['name']:i for i in h['assets']};rooms={r['id']:r for r in c['rooms']+c['connectors']}
for r in rooms.values():r['reused_parts']=[];r['scene_containers']=[]
def add(room,id,name,p,yaw=0,**kw):
 asset=a[name];row=dict(id=id,mesh=asset['ue_asset'],source_asset_id=name,position_m=p,yaw_deg=yaw,collision=asset.get('collision',True),cast_shadow=True,**kw)
 rooms[room]['reused_parts'].append(row);return row
def rotate(p,yaw):
 t=math.radians(yaw);return [p[0]*math.cos(t)-p[1]*math.sin(t),p[0]*math.sin(t)+p[1]*math.cos(t),p[2]]
def offset(p,q,yaw):r=rotate(q,yaw);return [p[k]+r[k] for k in range(3)]
def locker(room,id,p,yaw=0):
 add(room,id+'_Body','SM_Treatment_PPELocker_Body',p,yaw,container_id=id)
 hinge=a['SM_Treatment_PPELocker_Door']['pivot_blender_m']
 add(room,id+'_Door','SM_Treatment_PPELocker_Door',offset(p,hinge,yaw),yaw,container_id=id)
 rooms[room]['scene_containers'].append(dict(id=id,prototype='PPELocker',position_m=p,yaw_deg=yaw,caption='供能站防护用品柜',source_assembly='References/ReuseBundle/SourceAssets/IncineratorContainers20261003/Config/assemblies.json',rewards_deferred=True))
def records(room,id,p,yaw=0):
 add(room,id+'_Carcass','SM_Treatment_RecordsCabinet_Carcass',p,yaw)
 for i,z in enumerate((.11,.45,.79)):
  q=offset(p,[0,0,z],yaw);cid=id+'_Drawer'+str(i+1)
  add(room,cid+'_Frame','SM_Treatment_RecordsDrawer_Frame',q,yaw,container_id=cid)
  add(room,cid+'_Tray','SM_Treatment_RecordsDrawer_Tray',q,yaw,container_id=cid)
  rooms[room]['scene_containers'].append(dict(id=cid,prototype='RecordsDrawer',position_m=q,yaw_deg=yaw,caption='供能站检修记录 '+str(i+1),source_assembly='References/ReuseBundle/SourceAssets/IncineratorContainers20261003/Config/assemblies.json',rewards_deferred=True))
# Equipment banks; source cabinets' instrumented face is -Y, no scale changes.
for x in (-6,-2,2,6):
 for s in (-1,1):add('SwitchgearGallery','Distribution_'+('N' if s>0 else 'S')+str(x),'SM_Facility_PowerCabinet',[x,s*5.8,0],0 if s>0 else 180)
add('SwitchgearGallery','DutyDesk','SM_Staff_Desk',[.9,10.38,0])
add('SwitchgearGallery','DutyChair','SM_Staff_Chair',[.9,9.5,.0014],180)
locker('SwitchgearGallery','PPE_01',[-2.57,9.6,0],-90)
records('SwitchgearGallery','Records_01',[-1.25,10.5,0],180)
add('GeneratorHall','GeneratorDispatch','SM_Archive_DispatchConsole_V2',[0,9.3,2.4])
add('GeneratorHall','DispatchChair','SM_Staff_Chair',[0,8.20,2.4014],180)
for s in (-1,1):add('GeneratorHall','AuxPower_'+str(s),'SM_Facility_PowerCabinet',[s*12.25,-8.10,0],-s*90)
locker('GeneratorHall','PPE_02',[-8.6,-10.35,0],0)
add('AccumulatorControl','CoreDispatch','SM_Archive_DispatchConsole_V2',[0,9.1,1.92])
add('AccumulatorControl','CoreOperatorChair','SM_Staff_Chair',[0,7.97,1.9214],180)
add('AccumulatorControl','ControlDesk','SM_Staff_Desk',[3.9,9.55,1.92])
add('AccumulatorControl','ControlDeskChair','SM_Staff_Chair',[3.9,8.7,1.9214],180)
records('AccumulatorControl','Records_02',[-3.9,9.60,1.92],180)
locker('AccumulatorControl','PPE_03',[10.3,3.2,0],90);locker('AccumulatorControl','PPE_04',[10.3,4.5,0],90)
# Every real light gets the existing staff fixture, except the deliberately low
# small core service accent, which uses indirect equipment-side illumination.
for room in rooms.values():
 for l in room.get('lights',[]):
  if l['id']=='CoreAccent':continue
  p=l['position_m'];row=add(room['id'],'Fixture_'+l['id'],'SM_Staff_LampFixture',[p[0],p[1],p[2]+.13],0)
  row['collision']=False;row['cast_shadow']=False
# Existing 4.03m damaged ceramic wall group, rigid placement only, no tile scaling.
# Source runs +Y, faces +X, backing minX=.12021; bottom and worn upper edge preserved.
idx=0
def tile(room,wall_start,wall_end,inward,z=0):
 global idx
 dx=wall_end[0]-wall_start[0];dy=wall_end[1]-wall_start[1];length=math.hypot(dx,dy);ux,uy=dx/length,dy/length
 # The source +Y must follow wall tangent; +X then equals (uy,-ux).
 nx,ny=inward
 if abs(uy-nx)>1e-4 or abs(-ux-ny)>1e-4:raise ValueError('Tile wall tangent must match inward normal')
 if length<4.03-1e-6:raise ValueError('Never stretch or compress existing tile wall group')
 inset=(length-4.03)/2
 p=[wall_start[0]+ux*inset+nx*(.15+.002-.12021),wall_start[1]+uy*inset+ny*(.15+.002-.12021),z]
 yaw=math.degrees(math.atan2(ny,nx));idx+=1
 row=add(room,'OriginalTileDado_%02d'%idx,'SM_TileFracture_EntryEnd',p,yaw);row['collision']=False;row['cast_shadow']=False;row['reuse_method']='rigid original 4.03m group; source UV/ceramic thickness unchanged'
# South walls: tangent -X, inward +Y. North walls: tangent +X, inward -Y.
for lo,hi in [(-8.45,-4.20),(-2.12,2.12),(4.2,8.45)]:tile('SwitchgearGallery',(hi,-8),(lo,-8),(0,1))
for lo,hi in [(-8.45,-4.2),(4.2,8.45)]:tile('SwitchgearGallery',(lo,8),(hi,8),(0,-1))
for lo,hi in [(-7.5,-3.3),(3.3,7.5)]:
 tile('SwitchgearGallery',(-9,lo),(-9,hi),(1,0));tile('SwitchgearGallery',(9,hi),(9,lo),(-1,0))
for lo in (-12.1,-7.4,-2.015,3.5,8.2):tile('GeneratorHall',(lo+4.03,-11),(lo,-11),(0,1))
for lo in (-11.8,-6.0,.0,6.0):tile('GeneratorHall',(lo,11),(lo+4.03,11),(0,-1),2.4)
for lo,hi in [(-10.4,-6.2),(6.2,10.4)]:
 tile('GeneratorHall',(-13,lo),(-13,hi),(1,0));tile('GeneratorHall',(13,hi),(13,lo),(-1,0))
for lo,hi in [(-5.8,-1.7),(1.7,5.8)]:
 tile('AccumulatorControl',(-11,lo),(-11,hi),(1,0));tile('AccumulatorControl',(11,hi),(11,lo),(-1,0))
for lo,hi in [(-5.3,-1.2),(1.2,5.3)]:
 tile('AccumulatorControl',(hi,-11),(lo,-11),(0,1));tile('AccumulatorControl',(lo,11),(hi,11),(0,-1),1.92)
# Two exposed diagonal walls read as the octagonal core's chamfered perimeter.
s=2**-.5
tile('AccumulatorControl',(-6,-11),(-11,-6),(s,s));tile('AccumulatorControl',(11,-6),(6,-11),(-s,s))
c['existing_assets']=[dict(id=v['name'],mesh=v['ue_asset'],package_fbx='References/ReuseBundle/'+v['package_fbx'],materials=v.get('materials',{v.get('slot','Material'):v.get('material','')}),source_sha256=next(f['sha256'] for f in h['files'] if f['path']==v['package_fbx'])) for v in h['assets']]
c['geometry_reuse_stage']='portable_original_FBX_imported; exact UE original references retained'
c['yaw_contract']='yaw_deg is Blender right-handed local Z angle; Unreal yaw is its negative'
c['container_source_contract']='Original assemblies.json; static body/door rows marked container_id are Blender-only when existing runtime actor installer is present.'
c['source_project_head_at_inventory']=h['source_head_at_inventory'];c['source_engine_actual']=h['source_engine_actual']
P.write_text(json.dumps(c,ensure_ascii=False,indent=2),encoding='utf8')
print('POWER_REUSE_LAYOUT_AUTHORED',sum(len(r['reused_parts']) for r in rooms.values()),'original mesh instances;',idx,'rigid original tile groups; no furniture remodelling')
