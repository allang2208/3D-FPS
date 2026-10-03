"""Precisely rebuild the espresso cavity and supported cup; no render or test."""
from pathlib import Path
SCRIPT=Path(__file__).resolve().parent
entry=SCRIPT/'author_living.py';_STAFF_REFINEMENT_HELPERS=True
basecode=entry.read_text('utf8')
exec(compile(basecode.split('for key,fn in PROTOTYPES.items():')[0],str(entry),'exec'))
import copy
OUT=ROOT/'CoffeePolishV7/Authored';OUT.mkdir(parents=True,exist_ok=True)
BASE=CFG['ue_base']+'/CoffeePolishV7';records=[]
for key in ('Stainless','KettleRubber'):
    MAPPING[key]=CFG['ue_base']+'/WallInsetV6/Materials/M_Staff_'+key+'_V6'
    MATS[key]=bpy.data.materials.new('RS_'+key)
for key in ('MachineCoat','CupGlaze','Crema','StatusLight'):
    MAPPING[key]=BASE+'/Materials/M_Staff_'+key+'_V7';MATS[key]=bpy.data.materials.new('RS_'+key)
MAPPING['Coffee']=CFG['ue_base']+'/RoomDetailsV5/Materials/M_Staff_Coffee_V5'
MATS['Coffee']=bpy.data.materials.new('RS_Coffee')
# Load only accepted geometry definitions, never older author entrypoints.
v4=SCRIPT/'author_scene_polish_v4.py';v4code=v4.read_text('utf8')
exec(compile(v4code[v4code.index('v3=SCRIPT/'):v4code.index('def emit(')],str(v4),'exec'))

def curve(points,steps=10):
    ps=[Vector(p) for p in points];out=[]
    for i in range(len(ps)-1):
        a=ps[max(0,i-1)];b=ps[i];c=ps[i+1];d=ps[min(i+2,len(ps)-1)]
        for k in range(steps):
            t=k/steps;out.append(tuple(.5*((2*b)+(-a+c)*t+(2*a-5*b+4*c-d)*t*t+(-a+3*b-3*c+d)*t*t*t)))
    out.append(tuple(ps[-1]));return out

def front_ring(c,outer,inner,depth,mat='Stainless'):
    detail.ring(c,(0,-1,0),outer,inner,depth,mat,64,'Body')

def screw(c):
    cylinder(c,(0,-1,0),.0032,.0024,'Stainless',sides=24)
    box('Body',(c[0],c[1]-.0014,c[2]),(.004,.0005,.0008),'KettleRubber')

def coffee_machine():
    # Back, side cheeks and overhead case surround a REAL empty dispensing bay.
    # The previous .43 x .33 solid body intersected the rear 9mm of the cup.
    rounded_box('Body',(0,.080,.295),(.420,.230,.526),'MachineCoat',.018,8)
    for x in (-.197,.197):
        rounded_box('Body',(x,-.092,.310),(.036,.256,.536),'Stainless',.014,8)
        rounded_box('Body',(x+(.0185 if x>0 else -.0185),-.033,.327),(.002,.108,.373),'MachineCoat',.001,3)
        for z in (.11,.45):screw((x,-.221,z))
    rounded_box('Body',(0,-.092,.455),(.370,.256,.196),'Stainless',.014,8)
    rounded_box('Body',(0,-.223,.446),(.337,.011,.148),'MachineCoat',.005,6)
    rounded_box('Body',(0,-.092,.349),(.300,.255,.018),'Stainless',.004,5)
    # The rear wall is deeply recessed and separate from the cup and its handle.
    rounded_box('Body',(0,-.038,.194),(.342,.008,.282),'Stainless',.003,5)
    for x in (-.164,.164):
        for z in (.088,.276):screw((x,-.043,z))
    rounded_box('Body',(0,-.015,.565),(.420,.354,.025),'KettleRubber',.007,6)
    rounded_box('Body',(0,-.011,.580),(.390,.304,.011),'Stainless',.004,5)
    # Cup warming tray: recessed insert, fine ribs and retaining rails.
    for i in range(11):rounded_box('Body',(-.150+i*.030,-.012,.587),(.011,.244,.003),'Stainless',.001,3)
    for x in (-.192,.192):detail.tube('Body',[(x,-.134,.595),(x,.113,.595)],.005,'Stainless',24)
    detail.tube('Body',[(-.192,.119,.595),(.192,.119,.595)],.005,'Stainless',24)
    for x in (-.153,.153):
        for y in (-.111,.137):
            cylinder((x,y,.015),(0,0,1),.022,.030,'KettleRubber',sides=40)
            detail.ring((x,y,.026),(0,0,1),.023,.018,.006,'Stainless',40,'Body')
    # Removable drip pan: bottom, raised perimeter and supported open grate.
    rounded_box('Body',(0,-.195,.040),(.426,.291,.024),'KettleRubber',.009,6)
    for x in (-.204,.204):rounded_box('Body',(x,-.195,.053),(.014,.285,.031),'Stainless',.005,5)
    for y in (-.333,-.057):rounded_box('Body',(0,y,.053),(.398,.014,.031),'Stainless',.005,5)
    for y in (-.298,-.092):box('Body',(0,y,.052),(.397,.012,.010),'KettleRubber')
    for i in range(18):
        rounded_box('Body',(-.187+i*.022,-.195,.064),(.012,.258,.008),'Stainless',.002,4)
    # Small float in a real gap, flush front pull and pan/case separation seam.
    cylinder((.143,-.317,.071),(0,0,1),.004,.004,'StatusLight',sides=24)
    rounded_box('Body',(0,-.342,.044),(.100,.010,.012),'MachineCoat',.003,4)
    # Gauge, two knurled control dials, a recessed screen and physical buttons.
    front_ring((-.103,-.232,.470),.034,.025,.006)
    cylinder((-.103,-.234,.470),(0,-1,0),.0245,.004,'CupGlaze',sides=64)
    for i in range(13):
        a=math.radians(-140+i*23.3)
        p=Vector((-.103,-.237,.470))+Vector((math.sin(a),0,math.cos(a)))*.0195
        q=Vector((-.103,-.237,.470))+Vector((math.sin(a),0,math.cos(a)))*.0168
        detail.tube('Body',[p,q],.00075,'MachineCoat',12)
    detail.tube('Body',[(-.103,-.239,.470),(-.115,-.239,.481)],.0009,'MachineCoat',12)
    cylinder((-.103,-.240,.470),(0,-1,0),.002,.001,'Stainless',sides=20)
    for x in (-.111,.120):
        front_ring((x,-.232,.399),.022,.018,.005)
        cylinder((x,-.244,.399),(0,-1,0),.017,.024,'KettleRubber',sides=64)
        for i in range(24):
            a=i*math.tau/24
            detail.tube('Body',[(x+.017*math.cos(a),-.237,.399+.017*math.sin(a)),
                (x+.017*math.cos(a),-.253,.399+.017*math.sin(a))],.00075,'MachineCoat',12)
        box('Body',(x,-.257,.410),(.002,.001,.006),'CupGlaze')
    rounded_box('Body',(.020,-.230,.478),(.101,.012,.050),'KettleRubber',.004,6)
    rounded_box('Body',(.020,-.237,.478),(.086,.001,.038),'Screen',.002,4)
    # Native seven-segment numerals keep glyph proportions without texture stretch.
    bars=[(-.005,0,.003,.014),(.005,0,.003,.014),(0,.008,.009,.002),(0,-.008,.009,.002)]
    for x in (.004,.021,.038):
        for dx,dz,w,h in bars:box('Body',(x+dx,-.238,.478+dz),(w,.0007,h),'StatusLight')
    for x in (-.026,.012,.050):
        cylinder((x,-.235,.421),(0,-1,0),.007,.006,'KettleRubber',sides=40)
        cylinder((x,-.239,.421),(0,-1,0),.002,.001,'StatusLight',sides=24)
    # Connected extraction mount, chrome basket, seal, twin hollow outlets.
    lathe((0,-.209,.302),[(0,.052),(.007,.062),(.033,.059),(.044,.045)],'Stainless',96)
    detail.ring((0,-.209,.305),(0,0,1),.061,.049,.006,'KettleRubber',80,'Body')
    lathe((0,-.209,.275),[(0,.041),(.010,.047),(.024,.051),(.031,.053)],'Stainless',96)
    detail.tube('Body',[(0,-.237,.292),(.004,-.278,.292)],.012,'Stainless',32)
    handle_path=curve([(.004,-.275,.292),(.013,-.298,.291),(.027,-.354,.280),(.030,-.386,.273)],8)
    detail.tube('Body',handle_path,.0135,'KettleRubber',40)
    cylinder((.031,-.387,.273),(0,-1,-.15),.014,.010,'Stainless',sides=40)
    for x in (-.018,.018):
        detail.sweep('Body',curve([(x,-.212,.277),(x,-.232,.270),(x,-.238,.248)],6),.0045,'Stainless',32,.0014)
    # Steam wand starts at a swivel boss, stays beside the dispensing bay.
    rounded_box('Body',(.165,-.174,.332),(.045,.038,.044),'Stainless',.006,6)
    front_ring((.164,-.173,.313),.019,.010,.016)
    wand=curve([(.164,-.173,.313),(.170,-.208,.302),(.176,-.264,.234),(.164,-.278,.177)],10)
    detail.sweep('Body',wand,.0055,'Stainless',32,.0017)
    detail.tube('Body',curve([(.166,-.212,.294),(.174,-.235,.267)],8),.009,'KettleRubber',32)
    detail.ring((.164,-.278,.177),(-.12,-.14,-.57),.007,.004,.014,'Stainless',40,'Body')
    # Rear removable water reservoir, top latch and side vent slots.
    rounded_box('Body',(0,.185,.325),(.278,.065,.404),'MachineCoat',.017,8)
    rounded_box('Body',(0,.185,.529),(.285,.073,.014),'KettleRubber',.005,6)
    rounded_box('Body',(0,.195,.542),(.082,.028,.012),'Stainless',.004,5)
    for x in (-.217,.217):
        for z in [.292+i*.013 for i in range(9)]:
            rounded_box('Body',(x,.069,z),(.0015,.081,.005),'KettleRubber',.0006,2)
    # Mug rests at z=.068 (grate top), with a thick glazed lip and visible interior.
    cx,cy,base=0,-.238,.068
    lathe((cx,cy,base),[(0,.030),(.004,.030),(.006,.034),(.017,.036),(.062,.041),
        (.098,.044),(.103,.0437),(.107,.0423),(.108,.0404),(.107,.0385),
        (.102,.0380),(.060,.0360),(.023,.0305),(.015,.022),(.015,.001)],'CupGlaze',128)
    mug_handle=curve([(.039,cy,base+.088),(.062,cy,base+.089),(.077,cy,base+.069),
        (.076,cy,base+.043),(.061,cy,base+.025),(.0355,cy,base+.024)],12)
    detail.tube('Body',mug_handle,.0055,'CupGlaze',32)
    # Coffee is below the lip and within the actual inner wall, with subtle crema.
    cylinder((cx,cy,base+.078),(0,0,1),.0358,.0018,'Coffee',sides=96)
    detail.ring((cx,cy,base+.0791),(0,0,1),.0355,.0318,.0005,'Crema',96,'Body')
    for i in range(4):
        a=i*1.7+.4;r=.020-i*.003
        cylinder((cx+r*math.cos(a),cy+r*math.sin(a),base+.0794),(0,0,1),.0017+i*.0003,.0004,'Crema',sides=24)

G={};HULLS=[];coffee_machine()
name='SM_Staff_CoffeeMachine_V7'
export_mesh(name,merge_groups(),kind='Body',collision=False,nanite=True)
records[-1]['asset']=BASE+'/Meshes/'+name
prototype=bpy.data.objects[name];prototype.location=(0,-89,0)
# Preserve the complete V6 editable scene and replace its one coffee assembly.
source=ROOT/'WallInsetV6/Authored/StaffLivingTheme_WallInsetV6.blend'
with bpy.data.libraries.load(str(source),link=False) as (src,dst):
    dst.objects=[n for n in src.objects if n!='SM_Staff_CoffeeMachine_V5']
for obj in dst.objects:
    if obj:bpy.context.scene.collection.objects.link(obj)
instance=bpy.data.objects.get('StaffRecreation_CoffeeMachine')
if not instance:raise RuntimeError('Missing existing editable coffee assembly')
instance.data=prototype.data
cfg=copy.deepcopy(CFG)
cfg.update(coffee_polish_revision=7,revision='staff_coffee_machine_polish_v7_20261002',
    current_authored_source='CoffeePolishV7/Authored/StaffLivingTheme_CoffeePolishV7.blend')
coffee=next(p for r in cfg['rooms'] if r['id']=='StaffRecreation' for p in r['furniture'] if p['id']=='CoffeeMachine')
offset=cfg['preview_placements_m'][[r['id'] for r in cfg['rooms']].index('StaffRecreation')]
instance.location=Vector(offset)+Vector(coffee['position']);instance.rotation_euler.z=math.radians(coffee['yaw_blender_deg'])
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'StaffLivingTheme_CoffeePolishV7.blend'))
(OUT/'room-coffee.json').write_text(json.dumps(cfg,ensure_ascii=False,indent=2),encoding='utf8')
(OUT/'manifest.json').write_text(json.dumps(dict(objects=records,prototypes={'CoffeeMachine':name},revision=7,
    dispensing_space=dict(cup_center_m=[0,-.238,.068],cup_rim_z_m=.176,grate_top_z_m=.068,
        rear_panel_front_y_m=-.042,cup_rear_y_m=-.194,outlet_bottom_z_m=.248),
    tests_run=False,rendered=False),ensure_ascii=False,indent=2),encoding='utf8')
print('STAFF_COFFEE_POLISH_V7_AUTHORED',len(records),flush=True)
