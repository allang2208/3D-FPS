import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
instances=[]
for side,x,y,yaw in [('West',-9.99,-4.5,-90),('East',9.99,4.5,90)]:
 for i,offset in enumerate((-1.23,-.41,.41,1.23)):
  instances.append(dict(id='Server'+side+str(i+1),mesh='ServerRack',position=[x,y+offset,.16],yaw=yaw))
for kind,center in [('FileArchive',-5.1),('TapeLibrary',5.1)]:
 for i,offset in enumerate((-1.36,0,1.36)):
  instances.append(dict(id=kind+str(i+1),mesh=kind,position=[center+offset,-10.1,.16],yaw=180))
instances.append(dict(id='CentralDispatch',mesh='DispatchConsole',position=[0,3.7,-.6],yaw=0))
c=dict(revision='archive_equipment_v1_20260930',ue_base='/Game/Dungeons/DataArchive20260930/EquipmentV1',historical_author_layout=True,sample_retired=True,
 instances=instances,replace_actor_labels=['DataArchive_RecordsDesk1'],tag='DataArchive.Equipment.V1',tests_run=False)
(ROOT/'Config/layout.json').write_text(json.dumps(c,ensure_ascii=False,indent=2),encoding='utf-8')
print('ARCHIVE_EQUIPMENT_LAYOUT_SAVED',len(instances))
