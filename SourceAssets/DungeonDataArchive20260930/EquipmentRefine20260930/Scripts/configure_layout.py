"""Persist wall-side layout and deterministic non-repeating cabinet assignments."""
from pathlib import Path
import json,random,shutil
ROOT=Path(__file__).resolve().parents[1];HALL=ROOT.parent
p=HALL/'Config/room.json'
backup=ROOT/'Backup/room-before-v2.json'
if not backup.exists():shutil.copy2(p,backup)
c=json.loads(p.read_text('utf-8'))
for b in c['equipment_bays']:
 if abs(b['center'][0])>9:b['center'][0]=11.16 if b['center'][0]>0 else -11.16;b['depth']=1.35
 else:b['center'][1]=-11.40;b['depth']=.86
c.pop('equipment_install_script',None)
c['pool_install_script']='Pool20261001/Scripts/install_pool.py'
for q in c['reused_parts']:
 if q['id'].startswith('PowerCabinet'):
  west=q['id'].endswith('West');q['position']=[-11.465499916 if west else 11.465499916,4.65 if west else -4.65,0]
  q['wall_alignment']='outermost back surface 0.05 m inside inner wall; accepted saved placement'
p.write_text(json.dumps(c,ensure_ascii=False,indent=2),encoding='utf-8')
p=ROOT/'Config/layout.json';c=json.loads(p.read_text('utf-8'));rng=random.Random(c['seed']);items=[]
for side,x,y,yaw in [('West',-11.10,-4.5,-90),('East',11.10,4.5,90)]:
 for i,dy in enumerate((-1.23,-.41,.41,1.23)):
  items.append(dict(id='Server'+side+str(i+1),mesh_path='/Game/Dungeons/DataArchive20260930/EquipmentV1/Meshes/SM_Archive_ServerRack_V1',position=[x,y+dy,.16],yaw=yaw))
for family,variants,x in [('FileArchive',['Closed','UpperOpen','LowerOpen'],-5.1),('TapeLibrary',['Full','Sparse','Empty'],5.1)]:
 rng.shuffle(variants)
 for i,(dx,v) in enumerate(zip((-1.36,0,1.36),variants)):
  items.append(dict(id=family+str(i+1),mesh=family+'_'+v,position=[x+dx,-11.40,.16],yaw=180,variant=v))
items.append(dict(id='CentralDispatch',mesh='DispatchConsole',position=[0,11.12,0],yaw=0))
for v,x in [('A',-2.35),('B',2.35)]:items.append(dict(id='RecordsDesk'+v,mesh='RecordsDesk_'+v,position=[x,11.37,0],yaw=0))
c.update(instances=items,replace_actor_labels=['DataArchive_RecordsDesk'+str(i) for i in range(3)],replace_tags=['DataArchive.Equipment.V1','DataArchive.Equipment.V2'],power=[dict(label='DataArchive_PowerCabinetWest',sign=-1,y=4.65),dict(label='DataArchive_PowerCabinetEast',sign=1,y=-4.65)],notes='Seeded offline arrangements persist on saved map. No runtime Tick / cabinet interaction.')
p.write_text(json.dumps(c,ensure_ascii=False,indent=2),encoding='utf-8')
print('WALL_SIDE_LAYOUT_AUTHORED',len(items))
