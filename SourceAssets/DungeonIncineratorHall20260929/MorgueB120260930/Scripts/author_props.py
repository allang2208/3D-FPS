"""Dimensioned mortuary refrigerator modules, empty trays, furniture and retained ash plant."""
import json,sys,math
from pathlib import Path
import bpy
from mathutils import Vector,Matrix
ROOT=Path(__file__).resolve().parents[1];HALL=ROOT.parent
sys.path.insert(0,str(HALL/'AshStation20260930/Scripts'))
import author_station as ash
fx=ash.fx;eq=ash.eq;g=ash.g;box=g.box;rod=g.rod;bolt=g.bolt
C=json.loads((ROOT/'Config/layout.json').read_text(encoding='utf-8'))
BASE=C['ue_base'];OUT=ROOT/'Authored';OUT.mkdir(parents=True,exist_ok=True)

def tray(c,length=2.1,width=.69):
    x,y,z=c
    box((x,y,z),(width,length,.018),'steel',.003)
    for xx in (-width/2,width/2):box((x+xx,y,z+.035),(.018,length,.07),'steel',.004)
    for yy in (-length/2,length/2):box((x,y+yy,z+.035),(width,.018,.07),'steel',.004)
    for xx in (-.18,.18):rod((x+xx,y+length/2,z+.02),(x+xx,y+length/2+.055,z+.02),.009,'steel',16)
    rod((x-.18,y+length/2+.055,z+.02),(x+.18,y+length/2+.055,z+.02),.009,'steel',16)

def refrigerator(opened=False):
    eq.part('01_Insulated_cabinet_shell_and_three_separate_chambers')
    for x in (-.475,.475):box((x,-1.20,1.26),(.065,2.46,2.38),'steel',.008)
    box((0,-2.40,1.26),(.94,.08,2.38),'steel',.006)
    for z in (.13,.85,1.57,2.29):box((0,-1.2,z),(.95,2.46,.07),'steel',.006)
    for x in (-.36,.36):
        for y in (-.28,-2.10):g.lathe((x,y,0),(0,0,1),[(0,.045),(.025,.045),(.03,.025),(.12,.025)],'steel',24)
    for row in range(3):
        bottom=.17+row*.72;center=bottom+.325
        eq.part('02_Compartment_%d_seal_hinges_door'%row)
        # Closed gasket frames with real door thickness, hinges and lever latches.
        for x in (-.425,.425):box((x,.035,center),(.035,.022,.65),'rubber',.003)
        for zz in (bottom,bottom+.65):box((0,.035,zz),(.86,.022,.035),'rubber',.003)
        start=len(g.V)
        box((0,.083,center),(.85,.087,.63),'steel',.008)
        box((0,.132,center),(.74,.012,.515),'graphite',.005)
        box((0,.141,center),(.71,.012,.49),'steel',.005)
        for xx in (-.35,.35):
            for zz in (center-.23,center+.23):bolt((xx,.151,zz),(0,1,0),.55)
        # Door card holder (individual numbering is a separate shared signage batch).
        box((-.08,.157,center+.14),(.22,.015,.12),'steel',.003)
        box((.32,.165,center),(.055,.045,.20),'steel',.004)
        rod((.32,.20,center-.045),(.18,.23,center-.045),.019,'steel',24)
        for zz in (center-.20,center+.20):
            box((-.445,.075,zz),(.085,.09,.07),'steel',.004)
            g.lathe((-.46,.12,zz-.062),(0,0,1),[(0,.029),(.124,.029)],'steel',24)
        if opened and row==1:
            pivot=Vector((-.46,.08,center));rotation=Matrix.Rotation(math.radians(95),3,'Z')
            for i in range(start,len(g.V)):g.V[i]=tuple(pivot+rotation@(Vector(g.V[i])-pivot))
        eq.part('03_Compartment_%d_tray_and_telescoping_tracks'%row)
        offset=1.45 if opened and row==1 else 0
        for x in (-.35,.35):
            box((x,-1.18,bottom+.055),(.045,2.17,.06),'steel',.004)
            if offset:box((x,-.27,bottom+.09),(.032,2.22,.04),'steel',.003)
        tray((0,-1.13+offset,bottom+.118))
    eq.part('04_Condensing_unit_louvers_and_temperature_control')
    box((0,-.78,2.50),(.91,1.16,.34),'graphite',.006)
    for i in range(14):box((-.38+i*.058,-.192,2.51),(.032,.026,.235),'steel',.002)
    box((.29,.048,2.405),(.22,.055,.135),'graphite',.004)
    box((.27,.079,2.42),(.13,.012,.058),'rubber',.002)
    for x in (.355,.39):g.lathe((x,.08,2.39),(0,1,0),[(0,.01),(.01,.01)],'ochre',16)

def trolley():
    eq.part('01_Braked_casters_and_stainless_underframe')
    for x in (-.32,.32):
        for y in (-.83,.83):eq.caster(x,y,y>0,y>0)
        box((x,0,.34),(.055,1.85,.065),'steel',.005)
    for y in (-.81,.81):
        box((0,y,.34),(.7,.055,.065),'steel',.004)
        for x in (-.3,.3):box((x,y,.65),(.042,.042,.57),'steel',.004)
    eq.part('02_Removable_empty_transfer_tray')
    tray((0,0,.96),2.14,.76)
    for y in (-.87,.87):box((0,y,.90),(.75,.05,.05),'steel',.003)
    for x in (-.32,.32):rod((x,.93,.81),(x,1.14,.95),.016,'steel',20)
    rod((-.32,1.14,.95),(.32,1.14,.95),.018,'steel',24)

def preparation():
    eq.part('01_Fixed_preparation_table')
    tray((0,0,.92),2.22,.86)
    for y in (-.77,.77):
        box((0,y,.38),(.59,.35,.71),'steel',.012)
        box((0,y,.035),(.72,.54,.07),'graphite',.006)
    for x in (-.31,.31):box((x,0,.24),(.04,1.80,.04),'steel',.003)
    g.lathe((.28,-.85,.87),(0,0,-1),[(0,.033),(.24,.033)],'steel',24)

def sink():
    eq.part('01_Wash_sink_real_bowl_splashback_and_faucet')
    for x in (-.37,.37):
        for y in (-.23,.23):box((x,y,.43),(.045,.045,.86),'steel',.004)
    # Bowl walls and recessed bottom leave a real open cavity.
    box((0,0,.73),(.75,.54,.035),'steel',.003)
    for x in (-.39,.39):box((x,0,.825),(.035,.59,.22),'steel',.003)
    for y in (-.28,.28):box((0,y,.825),(.81,.035,.22),'steel',.003)
    box((0,.02,.945),(.88,.04,.04),'steel',.003)
    box((0,.325,1.10),(.87,.035,.36),'steel',.004)
    eq.curved([(0,.26,.95),(0,.26,1.27),(0,.17,1.34),(0,-.02,1.28),(0,-.02,1.18)],.015,'steel',20,6)
    for x in (-.15,.15):g.lathe((x,.26,.95),(0,0,1),[(0,.025),(.04,.025)],'graphite',20)
    eq.curved([(0,0,.70),(0,0,.43),(0,.18,.36),(0,.31,.46)],.022,'steel',20,5)

def desk():
    eq.part('01_Identification_records_station')
    box((0,0,.81),(1.36,.62,.055),'teal',.008)
    for x in (-.56,.56):
        for y in (-.23,.23):box((x,y,.39),(.045,.045,.78),'steel',.003)
    box((.4,0,.62),(.45,.55,.30),'graphite',.005)
    for z in (.53,.68):
        box((.4,-.286,z),(.40,.018,.12),'teal',.004)
        rod((.31,-.31,z),(.49,-.31,z),.009,'steel',16)
    for i in range(3):box((-.38+i*.12,.13,.87),(.10,.27,.055),'graphite',.003)

def closed_transfer_door():
    eq.part('01_Closed_logistics_transfer_double_door')
    for x in (-.55,.55):
        box((x,0,1.2),(1.09,.085,2.4),'teal',.006)
        box((x,-.047,.36),(.94,.018,.45),'steel',.004)
        box((x,-.052,1.82),(.29,.018,.36),'graphite',.003)
        rod((x*.3,-.115,.94),(x*.3,-.115,1.27),.018,'steel',20)

def rail_specs():
    original=old_rail_layout()
    out=[s for s in original if min(s['a'][1],s['b'][1])>5]
    def add(a,b,h=1.1):out.append({'a':list(a),'b':list(b),'height':h})
    add((-11.05,-2.57,0),(-8.6,-2.57,0))
    for x in (-13.08,-8.52):add((x,-7.65,0),(x,-2.65,0))
    add((-13,-7.73,0),(-8.6,-7.73,0))
    for x in (-12.91,-11.0):add((x,-2.65,0),(x,-5.95,-1.8),.95)
    for x in (-10.65,-8.75):add((x,-5.95,-1.8),(x,-2.65,-3.6),.95)
    return out

def sign_mat():
    mat=bpy.data.materials.new('MorgueSigns');mat.use_nodes=True
    image=bpy.data.images.load(str(OUT/'Textures/T_MorgueSigns_BaseColor.png'));image.pack()
    node=mat.node_tree.nodes.new('ShaderNodeTexImage');node.image=image
    mat.node_tree.links.new(node.outputs['Color'],mat.node_tree.nodes.get('Principled BSDF').inputs['Base Color'])
    return mat

def signs():
    eq.part('01_Stair_and_room_directions')
    for key,p,w,h,n in [
        ('stairs',(-9.2125,-2.43,.79),.94,.305,(0,1,0)),
        ('foyer',(-5.884,0,-.70),1.45,.468,(1,0,0)),
        ('cold',(-6.116,0,-.70),1.45,.468,(-1,0,0)),
        ('wash',(-2.5,2.184,-.88),1.1,.355,(0,-1,0)),
        ('service',(4.5,2.184,-.88),1.1,.355,(0,-1,0)),
        ('transfer',(-10.8,4.735,-.73),1.2,.387,(0,-1,0)),
        ('ash',(12.1,-7.12,1.30),1.0,.323,(0,1,0))]:
        fx.solid_nameplate(p,w,h,key,n,.007)
    for x in (-9.57,-8.86):
        box((x,-2.5,.63),(.03,.05,.36),'steel',.002)
        box((x,-2.467,.79),(.03,.025,.03),'steel',.001)
    for x in (11.72,12.48):
        box((x,-7.155,.72),(.04,.04,1.44),'steel',.002)
        box((x,-7.155,.013),(.14,.14,.026),'steel',.002)
    eq.part('02_Twelve_individual_mortuary_numbers')
    for spec in C['freezer_modules']:
        origin=Vector(spec['origin']);rot=Matrix.Rotation(math.radians(spec['yaw']),3,'Z')
        for row in range(3):
            if spec['key']=='ColdBankOpen' and row==1:continue
            local=Vector((-.08,.168,.17+row*.72+.465))
            fx.solid_nameplate(origin+rot@local,.19,.13,'slot%02d'%(spec['first_slot']+row),rot@Vector((0,1,0)),.002)
    # Slot 08 label is mounted on the cabinet jamb beside the open tray.
    fx.solid_nameplate((5.10,-1.46,-2.58),.12,.17,'slot08',(-1,0,0),.002)
    eq.part('03_Relocated_ash_receiver_plate')
    o=Vector(C['ash_station']['origin'])
    fx.solid_nameplate(o+Vector((0,.427,1.57)),.59,.162,'machine',(0,1,0),.003)

bpy.ops.wm.read_factory_settings(use_empty=True);bpy.context.scene.unit_settings.system='METRIC'
fx.ROOT=ROOT;fx.BASE=BASE;mat=eq.material();records=[]
old_rail_layout=fx.rails_layout;fx.rails_layout=rail_specs
specs=rail_specs();records.append(fx.export('Railings',fx.author_rails,[fx.rail_prism(s['a'],s['b'],-.025,s['height']+.04,.08) for s in specs],mat,'_MorgueB1'))
for key,author in [('ColdBankClosed',lambda:refrigerator(False)),('ColdBankOpen',lambda:refrigerator(True)),
                   ('MortuaryTrolley',trolley),('PreparationTable',preparation),('WashSink',sink),('RecordsDesk',desk),('TransferDoor',closed_transfer_door)]:
    rec=fx.export(key,author,[],mat,'_MorgueB1');rec['collision_policy']='complex_as_simple';records.append(rec)
# Keep the existing ash plant's identity and parts, adapting only its new gravity-fed inlet.
ash.CFG=dict(ash.CFG,inlet_at_furnace_m=C['ash_station']['inlet'],inlet_outward_axis=C['ash_station']['outward_axis'])
ash.ORIGIN=Vector(C['ash_station']['origin'])
rec=fx.export('AshReceiver',ash.receiver,[],mat,'_MorgueB1');rec['collision_policy']='complex_as_simple';records.append(rec)
atlas=json.loads((OUT/'sign_atlas.json').read_text(encoding='utf-8'))
def sign_tex(surface,u,v):
    x0,y0,x1,y1=atlas['rects'].get(surface,atlas['rects']['steel'])
    return ((x0+u*(x1-x0))/2048,1-(y0+v*(y1-y0))/2048)
g.tex=sign_tex;g.MATERIAL=BASE+'/Materials/M_MorgueSigns'
rec=fx.export('MorgueSigns',signs,[],sign_mat(),'_MorgueB1');rec['collision_policy']='none';records.append(rec)
bpy.ops.object.select_all(action='DESELECT')
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'Morgue_Equipment_And_StairRails.blend'))
(OUT/'manifest.json').write_text(json.dumps({'revision':C['revision'],'objects':records,'rail_runs':specs,'tests_run':False,'rendered':False},indent=2),encoding='utf-8')
print('MORGUE_EQUIPMENT_AUTHORED',len(records),flush=True)
