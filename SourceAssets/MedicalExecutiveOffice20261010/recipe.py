"""Replace only the physician workstations; retain room geometry and circulation."""
import math
BASE='/Game/Dungeons/MedicalExecutiveOffice20261010'
REVISION='medical_executive_workstations_20261010'
STATIONS=[('Consult1',-600,-300,0,2),('Consult2',-600,-1110,0,2),
 ('TeamWorkstation1',560,-285,0,0),('TeamWorkstation2',1230,-285,0,0),
 ('TeamWorkstation3',560,-650,0,0),('TeamWorkstation4',1230,-650,0,0),
 ('Chief',580,-2080,180,2),('RecordsWorkstation',-610,-1880,0,0),('ClinicalSupport',1270,-1660,180,0)]

def paths(v):
 if isinstance(v,str) and v.startswith('/Game/'):yield v
 elif isinstance(v,dict):
  for x in v.values():yield from paths(x)
 elif isinstance(v,list):
  for x in v:yield from paths(x)

def apply(module):
 if module['id']!='MedicalDoctorOffice':raise ValueError('Workstations belong to MedicalDoctorOffice')
 remove=set();new=[]
 for i,(key,x,y,yaw,visitors) in enumerate(STATIONS):
  prefix='MedicalOffice.'+key+'.'
  remove.update(prefix+suffix for suffix in ('Desk','DoctorChair','Visitor0','Visitor1','Records','Instructions','Electronics','DesktopDetails'))
  if not any(p.get('id')==prefix+'Desk' for p in module['parts']):raise ValueError('Missing target desk '+key)
  a=math.radians(yaw);co,si=math.cos(a),math.sin(a)
  def part(suffix,kind,dx=0,dy=0,turn=0,collision=False):
   new.append(dict(id=prefix+suffix,mesh=BASE+'/Meshes/SM_MedOffice_'+kind,
    position=[round(x+co*dx-si*dy,4),round(y+si*dx+co*dy,4),.6],yaw=(yaw+turn)%360,
    scale=[1,1,1],collision=collision,affects_navigation=collision,cast_shadow=True,fluid=False,materials=[]))
  part('Desk','ExecutiveDesk',collision=True)
  part('DoctorChair','ErgonomicChair',dy=108,collision=True)
  for j,dx in enumerate((-59,59) if visitors else ()):
   part('Visitor'+str(j),'VisitorChair',dx=dx,dy=-118,turn=180,collision=True)
  part('Electronics','ClinicalElectronics');part('DesktopDetails','DesktopDetails'+str(i%2))
 module['parts']=[p for p in module['parts'] if p.get('id') not in remove]+new
 module['runtime_assets']=sorted(set(paths([module['parts'],module['runtime_actors']])))
 author=module.setdefault('authoring',{});author['executive_workstations']=dict(revision=REVISION,count=len(STATIONS),
  mesh_group=BASE,main_desktop_cm=[240,110],overall_desktop_cm=[300,110],desk_top_cm=78.1,
  office_equipment_source='StationWorkshop20261003/RefineV2',tests_run=False)
 old_clearances={s[0]+'.DeskAccess' for s in STATIONS}
 author['furniture_clearances']=[s for s in author.get('furniture_clearances',[]) if s.get('id') not in old_clearances]
 for key,x,y,yaw,visitors in STATIONS:
  # Contains the L return and pulled-back chair; it does not change room/door bounds.
  author['furniture_clearances'].append(dict(id=key+'.DeskAccess',min=[x-185,y-175,0],max=[x+185,y+175,210]))
 return dict(revision=REVISION,workstations=len(STATIONS),old_part_ids=sorted(remove),new_parts=new)
