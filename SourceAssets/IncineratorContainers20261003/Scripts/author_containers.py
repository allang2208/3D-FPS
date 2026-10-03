"""Five precisely authored treatment-route containers; separate moving meshes, no render."""
import json
import math
from pathlib import Path
import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT.parents[1]
LIB = ROOT / 'Scripts/geometry_helpers.py'
exec(compile(LIB.read_text('utf8'), str(LIB), 'exec'))
BASE = '/Game/Dungeons/IncineratorContainers20261003'
for material in list(bpy.data.materials):
    bpy.data.materials.remove(material)
MAP = dict(Steel='/Game/Dungeons/StaffLiving20261002/WallInsetV6/Materials/M_Staff_Stainless_V6',
           Rubber='/Game/Dungeons/StaffLiving20261002/WallInsetV6/Materials/M_Staff_KettleRubber_V6',
           Green=BASE+'/Materials/M_Treatment_Green', Charcoal=BASE+'/Materials/M_Treatment_Charcoal',
           Gray=BASE+'/Materials/M_Treatment_Gray', Ceramic=BASE+'/Materials/M_Treatment_Ceramic',
           Canvas=BASE+'/Materials/M_Treatment_Canvas', Paper=BASE+'/Materials/M_Treatment_Paper',
           Filter=BASE+'/Materials/M_Treatment_Filter', Labels=BASE+'/Materials/M_Treatment_Labels')
MATS = {key: bpy.data.materials.new('RS_'+key) for key in MAP}
COLORS = dict(Steel=(.40,.44,.43,1), Rubber=(.024,.027,.023,1), Green=(.12,.21,.16,1),
              Charcoal=(.065,.074,.076,1), Gray=(.28,.32,.30,1), Ceramic=(.61,.57,.45,1),
              Canvas=(.29,.26,.18,1), Paper=(.61,.59,.48,1), Filter=(.51,.47,.37,1), Labels=(.8,.8,.7,1))
for key, material in MATS.items():
    material.diffuse_color = COLORS[key]
    material.use_nodes = True
    shader = material.node_tree.nodes.get('Principled BSDF')
    shader.inputs['Base Color'].default_value = COLORS[key]
    shader.inputs['Metallic'].default_value = .9 if key == 'Steel' else .1 if key in ('Green','Gray','Charcoal') else 0
    shader.inputs['Roughness'].default_value = .78 if key in ('Canvas','Paper','Filter') else .44
if (OUT/'T_Treatment_Labels.png').exists():
    texture = MATS['Labels'].node_tree.nodes.new('ShaderNodeTexImage')
    texture.image = bpy.data.images.load(str(OUT/'T_Treatment_Labels.png'))
    MATS['Labels'].node_tree.links.new(texture.outputs['Color'], MATS['Labels'].node_tree.nodes['Principled BSDF'].inputs['Base Color'])
_emit = emit
assemblies = {}


def emit(name, pivot=(0,0,0), hulls=()):
    obj = _emit(name, pivot, hulls)
    colors = obj.data.color_attributes['ServiceAge']
    for face in obj.data.polygons:
        edge = max(abs(v) for v in face.normal) < .975
        for li in face.loop_indices:
            p = obj.data.vertices[obj.data.loops[li].vertex_index].co
            variation = .5+.5*math.sin(p.x*27+p.y*19+p.z*13)
            colors.data[li].color = ((.48 if edge else .035)*variation, 0,
                                    .11+.08*math.sin(p.z*3+p.y*2), 1)
    # Re-export after the own wear channels are authored.
    select(obj)
    collision = []
    for i,(center,size) in enumerate(hulls):
        bpy.ops.mesh.primitive_cube_add(size=1, location=Vector(center)-Vector(pivot))
        co=bpy.context.object;co.name='UCX_'+name+'_'+str(i);co.scale=size
        bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
        collision.append(co)
    bpy.ops.object.select_all(action='DESELECT');obj.hide_set(False);obj.select_set(True)
    for co in collision:co.select_set(True)
    bpy.context.view_layer.objects.active=obj
    bpy.ops.export_scene.fbx(filepath=str(OUT/(name+'.fbx')),use_selection=True,object_types={'MESH'},
        axis_forward='-Y',axis_up='Z',bake_anim=False,mesh_smooth_type='FACE',use_tspace=True,add_leaf_bones=False)
    for co in collision:bpy.data.objects.remove(co,do_unlink=True)
    obj.hide_set(True)
    return obj


def label(c, width, row):
    height=width/2
    mesh=bpy.data.meshes.new('Proportioned treatment label')
    mesh.from_pydata([(c[0]-width/2,c[1],c[2]-height/2),(c[0]+width/2,c[1],c[2]-height/2),
                     (c[0]+width/2,c[1],c[2]+height/2),(c[0]-width/2,c[1],c[2]+height/2)],[],[(0,3,2,1)])
    mesh.update();obj=bpy.data.objects.new('Printed equipment plate',mesh)
    bpy.context.scene.collection.objects.link(obj);mesh.materials.append(MATS['Labels'])
    uv=mesh.uv_layers.new(name='UVMap');v0=1-(row+1)/5;v1=1-row/5
    coords=[(0,v0),(1,v0),(1,v1),(0,v1)]
    for li in mesh.polygons[0].loop_indices:uv.data[li].uv=coords[mesh.loops[li].vertex_index]
    parts.append(obj)


def panel(center,size,mat='Green'):
    box(center,size,mat,.004)
    return (center,size)


def rim(w,d,z,mat='Rubber',thickness=.009):
    for y in (-d/2,d/2):box((0,y,z),(w,thickness,thickness),mat,.002)
    for x in (-w/2,w/2):box((x,0,z),(thickness,d,thickness),mat,.002)


def chest_shell(w,d,h,mat):
    t=.014
    hulls=[panel((0,0,.02),(w,d,.025),mat)]
    for x in (-w/2+t/2,w/2-t/2):hulls.append(panel((x,0,h/2),(t,d,h),mat))
    for y in (-d/2+t/2,d/2-t/2):hulls.append(panel((0,y,h/2),(w-t*2,t,h),mat))
    rim(w-.025,d-.025,h-.008,mat,.012)
    for x in (-w/2+.033,w/2-.033):
        for y in (-d/2+.032,d/2-.032):
            box((x,y,.023),(.065,.064,.046),'Rubber',.008)
            box((x,y,h/2),(.040,.044,h-.065),mat,.005)
    return hulls


def tray(w,d,z,mat='Steel',height=.05):
    box((0,0,z),(w,d,.012),mat,.003)
    for x in (-w/2+.008,w/2-.008):box((x,0,z+height/2),(.016,d,height),mat,.003)
    for y in (-d/2+.008,d/2-.008):box((0,y,z+height/2),(w-.02,.016,height),mat,.003)


def torus(center,major,minor,mat='Steel',axis=(0,0,1)):
    bpy.ops.mesh.primitive_torus_add(major_radius=major,minor_radius=minor,major_segments=40,minor_segments=10,location=center)
    obj=bpy.context.object;obj.rotation_euler=Vector(axis).to_track_quat('Z','Y').to_euler()
    for face in obj.data.polygons:face.use_smooth=True
    return finish(obj,mat,0)


def annular_shell(center,radius,height,thickness,mat='Steel',sides=40):
    x,y,z=center;vertices=[]
    for r,zz in ((radius,z-height/2),(radius,z+height/2),(radius-thickness,z-height/2),(radius-thickness,z+height/2)):
        vertices += [(x+r*math.cos(i*math.tau/sides),y+r*math.sin(i*math.tau/sides),zz) for i in range(sides)]
    faces=[]
    for i in range(sides):
        j=(i+1)%sides
        faces.extend([(i,j,sides+j,sides+i),(2*sides+j,2*sides+i,3*sides+i,3*sides+j),
                      (i,2*sides+i,2*sides+j,j),(sides+j,3*sides+j,3*sides+i,sides+i)])
    mesh=bpy.data.meshes.new('Hollow sleeve');mesh.from_pydata(vertices,[],faces);mesh.update()
    obj=bpy.data.objects.new('Hollow sleeve',mesh);bpy.context.scene.collection.objects.link(obj)
    return finish(obj,mat,.0008)


def spanner(x,y,z,length=.22):
    box((x,y,z),(length,.021,.009),'Steel',.003)
    torus((x-length*.49,y,z),.021,.004,'Steel')
    # Open jaw: three connected thick pieces, with a true gap between tips.
    box((x+length*.5,y,z),(.024,.043,.009),'Steel',.002)
    for sign in (-1,1):box((x+length*.58,y+sign*.018,z),(.036,.013,.009),'Steel',.002)


def toolbox():
    w,d,h=.70,.36,.32
    hulls=chest_shell(w,d,h,'Green');tray(w-.055,d-.055,.082,height=.055)
    for x in (-.075,.12):box((x,0,.108),(.012,d-.08,.052),'Steel',.002)
    spanner(-.21,0,.0925,.16)
    cylinder((.015,0,.105),.008,.18,'Steel',axis=(0,1,0))
    cylinder((.015,-.104,.108),.018,.083,'Rubber',axis=(0,1,0),sides=32)
    for x in (.18,.235):
        annular_shell((x,-.025,.1025),.019,.029,.006)
    for x in (-.24,.24):latch(x,d/2+.010,h-.056)
    hinges(w,d,h)
    side_handle(w/2+.009,.18,.17)
    for x in (-.27,.27):box((x,0,.17),(.019,d+.017,.265),'Steel',.003)
    label((0,d/2+.012,.19),.19,0)
    emit('SM_Treatment_ToolBox_Body',hulls=hulls)
    box((0,0,h+.017),(w+.01,d+.01,.030),'Green',.007)
    box((0,0,h+.035),(w-.055,d-.055,.009),'Green',.004)
    rim(w-.032,d-.032,h+.004,'Rubber',.007)
    for x in (-.11,.11):
        box((x,0,h+.047),(.04,.034,.012),'Steel',.003)
        fasteners(x,0,h+.054,axis=(0,0,1))
    tube([(-.11,0,h+.05),(-.11,0,h+.10),(.11,0,h+.10),(.11,0,h+.05)],.008,'Rubber')
    emit('SM_Treatment_ToolBox_Lid',pivot=(0,-d/2,h))
    prototypes['ToolBox']=dict(body='SM_Treatment_ToolBox_Body',door='SM_Treatment_ToolBox_Lid',
        hinge=[0,d*50,h*100],opening_motion='Lid',opened_roll=108,caption='检修工具箱',storage_pages=1,
        dimensions_m=[w+.065,d+.065,h+.11])


def cabinet_shell(w,d,h,mat,base=.08):
    t=.016;hulls=[]
    for x in (-w/2+t/2,w/2-t/2):hulls.append(panel((x,0,(h+base)/2),(t,d,h-base),mat))
    hulls.append(panel((0,-d/2+t/2,(h+base)/2),(w-.025,t,h-base),mat))
    for z in (base,h-.012):hulls.append(panel((0,0,z),(w,d,.024),mat))
    for x in (-w*.39,w*.39):
        for y in (-d*.34,d*.34):hulls.append(panel((x,y,.043),(.06,.06,.086),'Charcoal'))
    return hulls


def fixed_hinges(w,d,lower,upper):
    for z in (lower,upper):
        box((-w/2+.011,d/2+.007,z),(.047,.012,.090),'Steel',.002)
        for zz in (z-.039,z+.039):fasteners(-w/2+.018,d/2+.015,zz)
        cylinder((-w/2+.013,d/2+.017,z),.010,.093,'Steel',sides=32)


def door_handle(x,y,z,mat='Steel'):
    for zz in (z-.07,z+.07):
        box((x,y+.009,zz),(.032,.012,.032),'Steel',.003)
        fasteners(x,y+.017,zz)
    tube([(x,y+.015,z-.07),(x,y+.063,z-.07),(x,y+.063,z+.07),(x,y+.015,z+.07)],.009,mat)
    cylinder((x+.040,y+.018,z+.115),.014,.009,'Steel',axis=(0,1,0),sides=32)


def ppe_locker():
    w,d,h=.64,.43,1.70
    hulls=cabinet_shell(w,d,h,'Green')
    for z in (.52,1.02,1.38):box((0,-.004,z),(w-.04,d-.02,.013),'Steel',.003)
    # Folded protection packs rest on the lower shelf; cartridge masks above.
    for x in (-.145,.12):
        for z in (.544,.579):
            box((x,.025,z),(.23,.27,.035),'Canvas',.009)
            tube([(x-.092,-.107,z+.017),(x+.092,-.107,z+.017)],.0015,'Paper')
    for x in (-.13,.13):
        bpy.ops.mesh.primitive_uv_sphere_add(segments=32,ring_count=20,location=(x,.01,1.0915))
        obj=bpy.context.object;obj.scale=(.10,.045,.065)
        finish(obj,'Rubber',0)
        cylinder((x+.074,.056,1.0845),.030,.030,'Gray',axis=(0,1,0),sides=32)
        cylinder((x-.074,.056,1.0845),.030,.030,'Gray',axis=(0,1,0),sides=32)
        tube([(x-.08,-.02,1.0865),(x-.08,-.095,1.1165),(x+.08,-.095,1.1165),(x+.08,-.02,1.0865)],.003,'Rubber')
    cylinder((0,0,1.451),.063,.13,'Filter',sides=48)
    torus((0,0,1.515),.060,.006,'Steel')
    fixed_hinges(w,d,.28,1.41)
    emit('SM_Treatment_PPELocker_Body',hulls=hulls)
    # Real vent gaps: surrounding folded frame, separate tilted blades.
    front=d/2+.018
    box((0,front,.765),(w-.037,.027,1.30),'Green',.008)
    for x in (-w/2+.038,w/2-.038):box((x,front,1.505),(.037,.027,.185),'Green',.004)
    for z in (1.414,1.595):box((0,front,z),(w-.037,.027,.023),'Green',.004)
    box((0,front,1.640),(w-.037,.027,.087),'Green',.004)
    for z in (1.444,1.474,1.504,1.534,1.564):
        obj=box((0,front+.003,z),(w-.10,.025,.012),'Green',.003)
        obj.rotation_euler.x=math.radians(-22)
    for x in (-.22,.22):box((x,front-.016,.76),(.025,.017,1.17),'Green',.003)
    door_handle(.235,front+.02,.90)
    label((-.045,front+.016,1.15),.25,1)
    emit('SM_Treatment_PPELocker_Door',pivot=(-w/2+.013,front,.09))
    prototypes['PPELocker']=dict(body='SM_Treatment_PPELocker_Body',door='SM_Treatment_PPELocker_Door',
        hinge=[(-w/2+.013)*100,-front*100,9],opening_motion='Swing',opened_yaw=-105,
        caption='防护用品柜',storage_pages=2,dimensions_m=[w,d+.095,h])


def drawer_pair(prefix,w,d,height,mat,row,caption,base=0):
    # One reusable hollow fixed runner frame and one moving tray.
    for x in (-w/2+.015,w/2-.015):
        box((x,0,base+height/2),(.016,d,height-.018),'Steel',.003)
        box((x*.97,0,base+.042),(.012,d-.04,.019),'Steel',.002)
    box((0,-d/2+.011,base+height/2),(w,.022,height-.012),mat,.003)
    box((0,0,base+.005),(w,d,.01),'Steel',.002)
    emit('SM_Treatment_'+prefix+'_Frame',hulls=[((0,.008,base+height/2),(w,d+.035,height))])
    tray(w-.043,d-.028,base+.032,height=height-.063)
    front=d/2+.022
    box((0,front,base+height/2),(w+.010,.030,height+.008),mat,.006)
    for x in (-w*.40,w*.40):box((x,0,base+.06),(.008,d*.72,.016),'Steel',.002)
    tube([(-.12,front+.018,base+height*.4),(-.12,front+.060,base+height*.4),
          (.12,front+.060,base+height*.4),(.12,front+.018,base+height*.4)],.007,'Steel')
    label((0,front+.018,base+height*.72),min(.16,w*.26),row)
    if prefix == 'HeatDrawer':
        for x in (-.15,.15):box((x,.018,base+.078),(.20,.26,.075),'Canvas',.008)
    else:
        for i in range(7):
            y=-d/2+.04+i*.045
            box((0,y,base+.115),(w-.08,.007,.145),'Canvas',.002)
            box((0,y-.006,base+.118),(w-.105,.008,.135),'Paper',.001)
            box((-.12 if i%2 else .12,y,base+.193),(.11,.010,.025),'Paper',.002)
    emit('SM_Treatment_'+prefix+'_Tray')
    prototypes[prefix]=dict(body='SM_Treatment_'+prefix+'_Frame',door='SM_Treatment_'+prefix+'_Tray',
        hinge=[0,0,0],opening_motion='Drawer',drawer_travel=[0,-min(35,d*78),0],caption=caption,
        storage_pages=1,dimensions_m=[w+.04,d+.09,height])


def heat_cabinet():
    w,d,h=.80,.49,1.08
    hulls=cabinet_shell(w,d,h,'Charcoal')
    for z in (.35,.58,.755):box((0,-.015,z),(w-.05,d-.06,.020),'Steel',.003)
    for x in (-.22,.18):
        box((x,0,.372),(.19,.32,.032),'Ceramic',.006)
        for z in (.611,.646):box((x,.003,z),(.23,.30,.032),'Canvas',.008)
    fixed_hinges(w,d,.22,.60)
    emit('SM_Treatment_HeatCabinet_Body',hulls=hulls)
    front=d/2+.020
    box((0,front,.424),(w-.043,.032,.614),'Charcoal',.009)
    box((0,front-.025,.424),(w-.09,.027,.57),'Ceramic',.006)
    for x in (-.29,.29):box((x,front-.045,.424),(.032,.021,.50),'Steel',.003)
    door_handle(.30,front+.025,.42,'Ceramic');label((-.055,front+.020,.59),.22,2)
    emit('SM_Treatment_HeatCabinet_Door',pivot=(-w/2+.013,front,.10))
    prototypes['HeatCabinet']=dict(body='SM_Treatment_HeatCabinet_Body',door='SM_Treatment_HeatCabinet_Door',
        hinge=[(-w/2+.013)*100,-front*100,10],opening_motion='Swing',opened_yaw=-103,
        caption='耐热器材柜',storage_pages=2,dimensions_m=[w,d+.10,h])
    drawer_pair('HeatDrawer',w-.054,d-.045,.25,'Charcoal',2,'耐热柜上层抽屉',base=.79)
    assemblies['HeatCabinet']=dict(containers=[dict(prototype='HeatCabinet',position_cm=[0,0,0]),
                                               dict(prototype='HeatDrawer',position_cm=[0,0,0])])


def records_cabinet():
    w,d,h=.74,.46,1.16
    hulls=cabinet_shell(w,d,h,'Gray')
    for z in (.10,.44,.78):box((0,0,z),(w-.02,d,.012),'Gray',.003)
    for x in (-w/2+.05,w/2-.05):box((x,d/2+.009,.61),(.045,.022,1.04),'Gray',.003)
    emit('SM_Treatment_RecordsCabinet_Carcass',hulls=hulls)
    drawer_pair('RecordsDrawer',w-.070,d-.037,.29,'Gray',3,'停尸间档案抽屉')
    assemblies['RecordsCabinet']=dict(caption='停尸间档案柜',dimensions_m=[w,d+.09,h],
        static_parts=[dict(mesh='SM_Treatment_RecordsCabinet_Carcass',position_cm=[0,0,0])],
        containers=[dict(prototype='RecordsDrawer',position_cm=[0,0,z],caption='停尸档案·'+name)
                    for z,name in ((11,'登记记录'),(45,'交接记录'),(79,'设备记录'))])


def pleated_filter(x,y,z,radius=.044,height=.17):
    # Closed pleated wall around an open cylindrical bore, with metal end caps.
    n=144;vertices=[]
    for zz in (z,z+height):
        for i in range(n):
            r=radius if i%2 else radius-.006
            vertices.append((x+r*math.cos(i*math.tau/n),y+r*math.sin(i*math.tau/n),zz))
    faces=[(i,(i+1)%n,n+(i+1)%n,n+i) for i in range(n)]
    mesh=bpy.data.meshes.new('Real filter pleats');mesh.from_pydata(vertices,[],faces);mesh.update()
    obj=bpy.data.objects.new('Pleated cartridge',mesh);bpy.context.scene.collection.objects.link(obj)
    finish(obj,'Filter',0)
    annular_shell((x,y,z+height/2),radius-.009,height,.006,'Filter',48)
    for zz in (z+.006,z+height-.006):annular_shell((x,y,zz),radius+.002,.014,.018,'Steel',48)
    annular_shell((x,y,z+height/2),.022,height,.003,'Steel',40)


def filter_case():
    w,d,h=.64,.42,.36
    hulls=chest_shell(w,d,h,'Gray')
    box((0,0,.064),(w-.045,d-.045,.055),'Rubber',.005)
    # Spaced rails cradle four cartridges without intersecting their pleats.
    for x in (-.24,-.08,.08,.24):pleated_filter(x,0,.0915,.043,.175)
    for x in (-.16,0,.16):box((x,0,.12),(.016,d-.06,.12),'Rubber',.003)
    for y in (-.072,.072):box((0,y,.075),(w-.055,.018,.02),'Rubber',.003)
    for x in (-.23,.23):latch(x,d/2+.011,h-.064)
    hinges(w,d,h);side_handle(w/2+.011,.24,.21);label((0,d/2+.012,.215),.21,4)
    emit('SM_Treatment_FilterCase_Body',hulls=hulls)
    box((0,0,h+.016),(w+.012,d+.012,.031),'Gray',.007)
    box((0,0,h+.035),(w-.055,d-.06,.012),'Gray',.004)
    rim(w-.034,d-.034,h+.003,'Rubber',.009)
    box((0,0,h+.003),(w-.07,d-.07,.025),'Rubber',.004)
    for x in (-.22,.22):box((x,0,h+.043),(.030,d-.036,.010),'Steel',.003)
    tube([(-.11,0,h+.042),(-.11,0,h+.092),(.11,0,h+.092),(.11,0,h+.042)],.008,'Rubber')
    emit('SM_Treatment_FilterCase_Lid',pivot=(0,-d/2,h))
    prototypes['FilterCase']=dict(body='SM_Treatment_FilterCase_Body',door='SM_Treatment_FilterCase_Lid',
        hinge=[0,d*50,h*100],opening_motion='Lid',opened_roll=108,caption='滤芯运输箱',storage_pages=1,
        dimensions_m=[w+.064,d+.08,h+.10])


toolbox();ppe_locker();heat_cabinet();records_cabinet();filter_case()
for key in ('ToolBox','PPELocker','FilterCase'):
    assemblies[key]=dict(caption=prototypes[key]['caption'],dimensions_m=prototypes[key]['dimensions_m'],
                        containers=[dict(prototype=key,position_cm=[0,0,0])])
assemblies['HeatCabinet'].update(caption='耐热器材柜',dimensions_m=prototypes['HeatCabinet']['dimensions_m'])
# Save five closed assemblies and separate source objects; no rendering or simulation.
for index,key in enumerate(('ToolBox','PPELocker','HeatCabinet','RecordsCabinet','FilterCase')):
    offset=Vector((index*1.45,0,0));assembly=assemblies[key]
    for item in assembly.get('static_parts',[]):
        obj=bpy.data.objects[item['mesh']];obj.hide_set(False);obj.location=offset
    for ordinal,item in enumerate(assembly['containers']):
        prototype=prototypes[item['prototype']]
        at=Vector((item['position_cm'][0]/100,-item['position_cm'][1]/100,item['position_cm'][2]/100))
        for role in ('body','door'):
            obj=bpy.data.objects[prototype[role]]
            if key == 'RecordsCabinet' and ordinal:
                obj=obj.copy();obj.data=obj.data.copy();bpy.context.scene.collection.objects.link(obj)
                obj.name=prototype[role]+'_Assembly_'+str(ordinal)
            obj.hide_set(False);obj.location=offset+at
            if role=='door':
                hinge=prototype['hinge'];obj.location+=Vector((hinge[0]/100,-hinge[1]/100,hinge[2]/100))
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'IncineratorContainers_Source.blend'))
(OUT/'manifest.json').write_text(json.dumps(dict(objects=records,prototypes=prototypes,assemblies=assemblies,
    material_sources=MAP,original_geometry=True,coordinate_contract='Blender metres x,y,z -> UE cm x,-y,z',
    tests_run=False,rendered=False),ensure_ascii=False,indent=2),encoding='utf8')
print('TREATMENT_CONTAINERS_AUTHORED '+str(len(records)),flush=True)
