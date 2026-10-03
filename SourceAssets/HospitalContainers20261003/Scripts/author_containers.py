"""Six original hospital search containers with complete, separate moving parts."""
import json
from pathlib import Path
import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT.parents[1]
# Reuse the accepted precise box/tube/bevel/UCX exporter; no old models are rebuilt.
LIB = PROJECT / 'SourceAssets/WarehouseContainers20261002/Scripts/author_containers.py'
exec(compile(LIB.read_text('utf8').split('def wood_crate():')[0], str(LIB), 'exec'))
BASE = '/Game/Dungeons/HospitalContainers20261003'
for material in list(bpy.data.materials):
    bpy.data.materials.remove(material)
MAP = dict(Steel='/Game/Dungeons/StaffLiving20261002/WallInsetV6/Materials/M_Staff_Stainless_V6',
           Rubber='/Game/Dungeons/StaffLiving20261002/WallInsetV6/Materials/M_Staff_KettleRubber_V6',
           White=BASE+'/Materials/M_Hospital_White', Blue=BASE+'/Materials/M_Hospital_Blue',
           Green=BASE+'/Materials/M_Hospital_Green', Red=BASE+'/Materials/M_Hospital_Red',
           Lining=BASE+'/Materials/M_Hospital_Lining', Labels=BASE+'/Materials/M_Hospital_Labels',
           Glass='/Game/Dungeons/IsolationWard20260929/Materials/M_WardGlassV2')
MATS = {k: bpy.data.materials.new('RS_'+k) for k in MAP}


def label(c, w, h, row):
    # UE front is -Y; UV orientation matches the repaired workshop labels.
    mesh = bpy.data.meshes.new('Hospital printed label')
    mesh.from_pydata([(c[0]-w/2,c[1],c[2]-h/2),(c[0]+w/2,c[1],c[2]-h/2),
                     (c[0]+w/2,c[1],c[2]+h/2),(c[0]-w/2,c[1],c[2]+h/2)], [], [(0,3,2,1)])
    mesh.update()
    obj = bpy.data.objects.new('Printed label', mesh)
    bpy.context.scene.collection.objects.link(obj)
    mesh.materials.append(MATS['Labels'])
    uv = mesh.uv_layers.new(name='UVMap')
    bottom, top = 1-(row+1)/6, 1-row/6
    coords = [(0,bottom),(1,bottom),(1,top),(0,top)]
    for loop in mesh.polygons[0].loop_indices:
        uv.data[loop].uv = coords[mesh.loops[loop].vertex_index]
    parts.append(obj)


def shell(w, d, h, mat, thickness=.014, floor=.012):
    box((0,0,floor),(w,d,thickness),mat,.004)
    for x in (-w/2+thickness/2,w/2-thickness/2):
        box((x,0,h/2), (thickness,d,h),mat,.004)
    for y in (-d/2+thickness/2,d/2-thickness/2):
        box((0,y,h/2), (w-thickness*2,thickness,h),mat,.004)
    return [((0,0,floor),(w,d,thickness)),
            ((-w/2+thickness/2,0,h/2),(thickness,d,h)),
            ((w/2-thickness/2,0,h/2),(thickness,d,h)),
            ((0,-d/2+thickness/2,h/2),(w,thickness,h)),
            ((0,d/2-thickness/2,h/2),(w,thickness,h))]


def rim(w, d, z, mat='Rubber', width=.009):
    for y in (-d/2,d/2):
        box((0,y,z),(w,width,width),mat,width*.2)
    for x in (-w/2,w/2):
        box((x,0,z),(width,d,width),mat,width*.2)


def fold_handle(w, d, z):
    half=min(d*.55,.22)/2
    for sign in (-1,1):
        x=sign*(w/2+.007)
        for y in (-half,half):
            box((x,y,z),(.014,.040,.065),'Steel',.003)
            cylinder((x,y,z),.012,.016,axis=(1,0,0))
        tube([(x,-half,z),(x+sign*.034,-half,z-.04),
              (x+sign*.034,half,z-.04),(x,half,z)],.007)


def lid(key, w, d, h, mat, row, thickness=.025, roll=108, handle=True):
    box((0,0,h+thickness/2+.004),(w+.014,d+.014,thickness),mat,.007)
    box((0,0,h+thickness+.009),(w-.07,d-.07,.010),mat,.004)
    rim(w-.012,d-.012,h+.002,'Rubber',.006)
    if handle:
        tube([(-.10,0,h+thickness+.018),(-.10,0,h+thickness+.064),
              (.10,0,h+thickness+.064),(.10,0,h+thickness+.018)],.007)
        for x in (-.10,.10):
            box((x,0,h+thickness+.014),(.04,.035,.012),'Steel',.003)
    emit('SM_Hospital_'+key+'_Lid',pivot=(0,-d/2,h))
    prototypes[key]=dict(body='SM_Hospital_'+key+'_Body',door='SM_Hospital_'+key+'_Lid',
        hinge=[0,d*50,h*100],opening_motion='Lid',opened_roll=roll,storage_pages=1,
        dimensions_m=[w+.10,d+.09,h+thickness+.09])


def cart():
    w,d=.68,.48
    for x in (-.27,.27):
        for y in (-.18,.18):
            cylinder((x,y,.064),.061,.027,'Rubber',axis=(1,0,0),sides=32)
            cylinder((x+.016,y,.064),.025,.004,axis=(1,0,0),sides=24)
            for xx in (x-.022,x+.022):
                box((xx,y,.099),(.012,.044,.074),'Steel',.003)
            cylinder((x,y,.149),.023,.045)
            cylinder((x,y,.51),.015,.70)
    box((0,0,.235),(w-.06,d-.04,.023),'Steel',.004)
    rim(w-.07,d-.05,.269,'Steel',.014)
    for x in (-.19,.01,.18):
        box((x,0,.272),(.13,.24,.045),'Lining',.008)
        box((x,0,.297),(.10,.22,.004),'White',.001)
    # A hollow drawer cavity with side/back panels and fixed telescopic runners.
    for x in (-w/2+.02,w/2-.02):
        box((x,0,.733),(.027,d,.238),'White',.006)
        box((x*.96,0,.674),(.012,d-.045,.019),'Steel',.002)
    box((0,-d/2+.015,.733),(w,.024,.238),'White',.005)
    box((0,0,.853),(w+.01,d+.01,.031),'Steel',.004)
    box((0,0,.613),(w-.04,d-.025,.016),'Steel',.003)
    for x in (-.295,.295):
        tube([(x,-.19,.872),(x,-.19,.966),(x,.19,.966),(x,.19,.872)],.010)
    tube([(-.28,-.24,.93),(-.28,-.29,1.01),(.28,-.29,1.01),(.28,-.24,.93)],.011)
    # Small sterile packs sit above the worktop rather than inside it.
    for x,y in ((-.12,.06),(.11,-.04)):
        box((x,y,.894),(.14,.11,.035),'Lining',.006)
        box((x,y,.914),(.12,.10,.003),'White',.001)
    hulls=[((0,0,.235),(w,d,.03)),((0,0,.853),(w,d,.04)),
           ((-.32,0,.73),(.04,d,.25)),((.32,0,.73),(.04,d,.25)),
           ((0,-.23,.73),(w,.04,.25))]
    for x in (-.27,.27):
        for y in (-.18,.18):hulls.append(((x,y,.46),(.075,.10,.92)))
    emit('SM_Hospital_MedicalCart_Body',hulls=hulls)
    box((0,.010,.666),(.59,.418,.015),'Steel',.003)
    for x in (-.286,.286):box((x,.010,.715),(.015,.418,.10),'Steel',.003)
    for x in (-.2985,.2985):box((x,.010,.674),(.009,.32,.015),'Steel',.002)
    box((0,-.192,.715),(.588,.015,.10),'Steel',.003)
    box((0,.254,.736),(.622,.028,.190),'White',.006)
    tube([(-.14,.274,.736),(-.14,.310,.736),(.14,.310,.736),(.14,.274,.736)],.007)
    for x in (-.10,.10):box((x,.01,.690),(.008,.37,.03),'Lining',.002)
    label((0,.270,.791),.16,.08,0)
    emit('SM_Hospital_MedicalCart_Drawer')
    prototypes['MedicalCart']=dict(body='SM_Hospital_MedicalCart_Body',door='SM_Hospital_MedicalCart_Drawer',
        hinge=[0,0,0],opening_motion='Drawer',drawer_travel=[0,-32,0],storage_pages=1,
        caption='医疗推车抽屉',dimensions_m=[.70,.63,1.025])


def patient_box():
    w,d,h=.44,.32,.32
    hulls=shell(w,d,h,'Blue',.015)
    rim(w-.010,d-.010,h-.004,'Blue',.012)
    fold_handle(w,d,.20)
    for x in (-.16,.16):
        latch(x,d/2+.009,h-.045)
        for y in (-d/2,d/2):box((x,y,.15),(.018,.008,.22),'Blue',.004)
    hinges(w,d,h)
    label((0,d/2+.010,.18),.18,.09,1)
    box((0,0,.035),(w-.04,d-.04,.016),'Lining',.004)
    emit('SM_Hospital_PatientBox_Body',hulls=hulls)
    lid('PatientBox',w,d,h,'Blue',1,handle=False)
    prototypes['PatientBox']['caption']='病人物品箱'


def first_aid():
    w,d,h=.50,.20,.64
    hulls=shell(w,d,h,'White',.012)
    # Remove the front shell, leaving a genuine opening behind the door.
    front=parts.pop();bpy.data.objects.remove(front,do_unlink=True)
    hulls.pop()
    for z in (.20,.405):box((0,0,z),(w-.04,d-.025,.012),'Steel',.002)
    for x in (-.15,-.07,.065,.15):
        cylinder((x,0,.255),.026,.09,'White',sides=24)
        cylinder((x,0,.309),.027,.018,'Blue',sides=24)
    for x in (-.12,.075):
        box((x,0,.468),(.13,.13,.105),'Lining',.005)
        box((x,0,.523),(.12,.12,.004),'White',.001)
    for x in (-.19,.19):
        for z in (.055,.585):cylinder((x,-d/2-.008,z),.012,.008,axis=(0,1,0))
    for z in (.12,.52):
        cylinder((-w/2,d/2,z),.009,.075,'Steel')
        box((-w/2+.013,d/2-.005,z),(.04,.010,.065),'Steel',.002)
    emit('SM_Hospital_FirstAid_Body',hulls=hulls)
    for x in (-.225,.225):box((x,d/2+.009,h/2),(.05,.022,h-.016),'White',.004)
    for z,hh in ((.085,.15),(.557,.15)):
        box((0,d/2+.009,z),(w-.08,.022,hh),'White',.004)
    box((0,d/2+.009,.323),(.40,.004,.31),'Glass',0)
    for x in (-.200,.200):box((x,d/2+.012,.323),(.012,.007,.326),'Rubber',.002)
    for z in (.162,.484):box((0,d/2+.012,z),(.402,.007,.012),'Rubber',.002)
    # A raised emergency cross and plate preserve their physical proportions.
    box((-.14,d/2+.022,.558),(.026,.006,.080),'Red',.002)
    box((-.14,d/2+.022,.558),(.080,.006,.026),'Red',.002)
    label((.055,d/2+.022,.558),.20,.10,2)
    tube([(.202,d/2+.024,.25),(.202,d/2+.060,.25),(.202,d/2+.060,.37),(.202,d/2+.024,.37)],.006)
    cylinder((.205,d/2+.026,.19),.014,.010,axis=(0,1,0),sides=24)
    emit('SM_Hospital_FirstAid_Door',pivot=(-w/2,d/2,0))
    records[-1]['nanite']=False # The thin transparent window retains conventional geometry.
    prototypes['FirstAid']=dict(body='SM_Hospital_FirstAid_Body',door='SM_Hospital_FirstAid_Door',
        hinge=[-w*50,-d*50,0],opening_motion='Swing',opened_yaw=-102,storage_pages=1,
        caption='壁挂急救箱',dimensions_m=[w,d+.075,h])


def instrument_box():
    w,d,h=.38,.25,.115
    hulls=shell(w,d,h,'Steel',.006,floor=.008)
    box((0,0,.018),(w-.035,d-.035,.012),'Lining',.003)
    for x in (-.08,.08):
        tube([(x-.016,.065,.032),(x-.023,-.045,.032),(x,-.075,.036),(x+.023,-.045,.032),
              (x+.016,.065,.032)],.0025)
        cylinder((x,.01,.035),.006,.004,'Steel',sides=16)
    hinges(w,d,h)
    for x in (-.12,.12):
        box((x,d/2+.008,.082),(.023,.012,.050),'Steel',.003)
        cylinder((x,d/2+.016,.093),.004,.034,axis=(1,0,0),sides=16)
    label((0,d/2+.009,.055),.10,.05,3)
    emit('SM_Hospital_InstrumentBox_Body',hulls=hulls)
    lid('InstrumentBox',w,d,h,'Steel',3,thickness=.014,handle=False)
    prototypes['InstrumentBox']['caption']='器械消毒盒'


def specimen_case():
    w,d,h=.58,.40,.44
    hulls=shell(w,d,h,'White',.020,floor=.016)
    rim(w-.012,d-.012,h-.003,'Blue',.015)
    box((0,0,.051),(w-.045,d-.045,.04),'Lining',.006)
    for x in (-.14,0,.14):
        box((x,0,.12),(.014,d-.055,.095),'Lining',.003)
    for y in (-.105,0,.105):
        box((0,y,.12),(w-.045,.014,.095),'Lining',.003)
    for x,y in ((-.215,-.054),(-.072,.054),(.074,-.054),(.216,.054)):
        cylinder((x,y,.128),.025,.105,'Glass',sides=24)
        cylinder((x,y,.190),.027,.020,'Blue',sides=24)
        cylinder((x,y,.110),.016,.067,'Red',sides=20)
    fold_handle(w,d,.26);hinges(w,d,h)
    for x in (-.19,.19):latch(x,d/2+.010,h-.048)
    for x in (-.24,.24):
        for y in (-.15,.15):box((x,y,.013),(.065,.060,.025),'Rubber',.005)
    label((0,d/2+.012,.28),.22,.11,4)
    emit('SM_Hospital_SpecimenCase_Body',hulls=hulls)
    records[-1]['nanite']=False
    lid('SpecimenCase',w,d,h,'Blue',4)
    prototypes['SpecimenCase']['caption']='标本运输箱'


def tool_box():
    w,d,h=.58,.30,.28
    hulls=shell(w,d,h,'Green',.012,floor=.015)
    for x in (-.23,0,.23):
        for y in (-d/2,d/2):box((x,y,.135),(.020,.010,.225),'Green',.003)
    box((0,0,.065),(w-.04,d-.04,.012),'Steel',.003)
    for x in (-.09,.10):box((x,0,.10),(.012,d-.04,.065),'Steel',.002)
    for x in (-.18,-.13):
        tube([(x,-.09,.083),(x,.07,.083),(x+.032,.09,.083)],.006)
    cylinder((.16,0,.083),.018,.025,'Steel',sides=20)
    for x in (-.21,.21):latch(x,d/2+.011,h-.055)
    hinges(w,d,h);fold_handle(w,d,.17)
    label((0,d/2+.012,.19),.17,.085,5)
    emit('SM_Hospital_ToolBox_Body',hulls=hulls)
    lid('ToolBox',w,d,h,'Green',5)
    prototypes['ToolBox']['caption']='排水检修工具箱'


cart();patient_box();first_aid();instrument_box();specimen_case();tool_box()
for index,(key,prototype) in enumerate(prototypes.items()):
    body=bpy.data.objects[prototype['body']];body.hide_set(False);body.location=(index*1.2,0,0)
    moving=bpy.data.objects[prototype['door']];moving.hide_set(False)
    hinge=prototype['hinge'];moving.location=body.location+Vector((hinge[0]/100,-hinge[1]/100,hinge[2]/100))
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'HospitalContainers_Source.blend'))
(OUT/'manifest.json').write_text(json.dumps(dict(objects=records,prototypes=prototypes,material_sources=MAP,
    original_geometry=True,tests_run=False,rendered=False),ensure_ascii=False,indent=2),encoding='utf8')
print('HOSPITAL_CONTAINERS_AUTHORED',len(records),flush=True)
