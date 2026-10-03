"""Medical binders, layered documents, pen and clipboard for the reused desks."""
from pathlib import Path
import bpy,json
TASK=Path(__file__).resolve().parents[1];PROJECT=TASK.parents[1]
library=PROJECT/'SourceAssets/WarehouseContainers20261002/Scripts/author_containers.py'
exec(compile(library.read_text('utf8').split('def wood_crate():')[0],str(library),'exec'))
ROOT=TASK;OUT=ROOT/'Authored';BASE='/Game/Dungeons/HospitalDoctorOffice20261003'
previous=json.loads((OUT/'manifest.json').read_text('utf8'))
for material in list(bpy.data.materials):bpy.data.materials.remove(material)
MAP=dict(Paper='/Game/Dungeons/StaffLiving20261002/DormitoryVariantsV2/Materials/M_Dorm_BookPaper',
 Green='/Game/Dungeons/StaffLiving20261002/DormitoryVariantsV2/Materials/M_Dorm_BookGreen',
 Blue='/Game/Dungeons/StaffLiving20261002/DormitoryVariantsV2/Materials/M_Dorm_BookBlue',
 Steel='/Game/Dungeons/StaffLiving20261002/WallInsetV6/Materials/M_Staff_Stainless_V6',
 Rubber='/Game/Dungeons/StaffLiving20261002/WallInsetV6/Materials/M_Staff_KettleRubber_V6')
MATS={key:bpy.data.materials.new('RS_'+key) for key in MAP}
for index,mat in enumerate(('Green','Blue')):
 z=.0175+index*.035;x=-.33+index*.012;y=.025-index*.010
 box((x,y,z),(.22,.275,.028),'Paper',.002)
 for dz in (-.016,.016):box((x,y,z+dz),(.238,.287,.003),mat,.001)
 box((x-.119,y,z),(.009,.287,.035),mat,.002)
 for offset in (-.007,-.003,.003,.007):
  box((x+.111,y,z+offset),(.002,.267,.0005),'Rubber',0)
 # A spine label retains its own dimensions and never stretches text.
 box((x-.125,y,z),(.002,.085,.020),'Paper',.001)
box((.185,-.023,.003),(.24,.32,.006),'Green',.004)
for index in range(4):
 box((.181+index*.001,-.016+index*.002,.007+index*.0012),(.213,.297,.001),'Paper',.0002)
for x in (.142,.186,.230):cylinder((x,-.156,.013),.008,.038,'Steel',axis=(1,0,0),sides=24)
for row in range(10):
 box((.181,-.110+row*.023,.0113),(.176,.0007,.0004),'Rubber',0)
for x in (.123,.226):box((x,-.016,.0113),(.0007,.235,.0004),'Rubber',0)
cylinder((-.015,.030,.0045),.0045,.145,'Blue',axis=(0,1,0),sides=24)
cylinder((-.015,-.045,.0045),.0035,.013,'Steel',axis=(0,1,0),sides=24)
box((-.010,.071,.010),(.004,.035,.002),'Steel',.0005)
obj=emit('SM_Office_RecordsDesktop')
for o in bpy.context.scene.objects:o.hide_set(False)
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'DoctorOffice_DesktopProps.blend'))
previous['objects']=[i for i in previous['objects'] if i['name']!='SM_Office_RecordsDesktop']+records
(OUT/'manifest.json').write_text(json.dumps(previous,ensure_ascii=False,indent=2),encoding='utf8')
print('OFFICE_DESKTOP_PROPS_AUTHORED',len(records))
