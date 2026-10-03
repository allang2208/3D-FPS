"""Reuse the accepted staff desks, chairs, bookcases and working shelf drawer."""
import copy,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parents[1]
staff=json.loads((PROJECT/'SourceAssets/DungeonStaffLiving20261002/Production20261002/Config/modules.json').read_text('utf8'))
dorm=next(m for m in staff['modules'] if m['id']=='StaffDormitory')
base='/Game/Dungeons/StaffLiving20261002/Meshes/'
parts=[]
def part(identity,key,position,yaw=0):
 parts.append(dict(id='HospitalOffice.'+identity,mesh=base+'SM_Staff_'+key,
   position=position,yaw=yaw,scale=[1,1,1],collision=True,affects_navigation=True,materials=[],fluid=False))
floor=4.4
part('ConsultationDesk','Desk',[2450,874,floor])
part('DoctorChair','Chair',[2450,961,floor],180)
part('VisitorChairA','Chair',[2390,769,floor],4)
part('VisitorChairB','Chair',[2513,755,floor],-7)
part('RecordsDesk','Desk',[1768,777,floor],-90)
part('RecordsChair','Chair',[1850,777,floor],92)
part('WaitingBench','ChangingBench',[2010,995,floor])
part('WaitingTable','CoffeeTable',[2000,883,floor],3)
for identity,position,yaw in (
 ('ConsultationRecords',[2450,874,82.68],180),
 ('WorkingRecords',[1768,777,82.68],-90)):
 parts.append(dict(id='HospitalOffice.'+identity,
   mesh='/Game/Dungeons/HospitalDoctorOffice20261003/Meshes/SM_Office_RecordsDesktop',
   position=position,yaw=yaw,scale=[1,1,1],collision=False,affects_navigation=False,materials=[],fluid=False))
containers=[]
for identity,caption,kind,position,yaw in (
 ('MedicalBooks','医学书柜','Bookcase',[2880,993,floor],180),
 ('PatientRecords','病历档案柜','Bookcase',[2725,993,floor],180),
 ('WorkingShelf','医生资料书架','Bookshelf',[2950,748,floor],90)):
 source=next(c for c in dorm['scene_containers'] if '.%s_'%kind in c['container_id'])
 c=copy.deepcopy(source);c.pop('layout_slot',None)
 c.update(type='scene_container',container_id='Hospital.Office.'+identity,caption=caption,
   position=position,yaw=yaw,storage_pages=2)
 containers.append(c)
data=dict(revision=1,module_id='AbandonedIsolationWard',room='East corridor-end room, former empty DECON wing',
 bounds_cm=dict(min=[1714,464,4.2],max=[2986,1036,440]),
 door_cm=[2350,450,0],parts=parts,
 group=dict(id='Hospital.Office.Storage',pick_count=[3,3],slots=[
   dict(id=c['container_id'],variants=[dict(containers=[c])]) for c in containers]),
 tests_run=False,rendered=False,game_run=False)
(ROOT/'Config/office.json').write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf8')
print('DOCTOR_OFFICE_LAYOUT_AUTHORED',len(parts),len(containers))
