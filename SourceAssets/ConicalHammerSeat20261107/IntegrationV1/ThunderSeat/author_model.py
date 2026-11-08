"""Conical central seat: native interfaces, editable solids, baked 4K PBR."""
import bpy,bmesh,math,json,types,sys,time
from pathlib import Path
from mathutils import Vector
P=Path(__file__).resolve().parent;ROOT=Path('D:/FPS3D/FPSGAME')
for name in ('Export','Textures','Icons'):(P/name).mkdir(exist_ok=True)
sys.path.insert(0,str(P))
import solid_surface_tools as m
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.context.preferences.filepaths.save_version=0
scene=bpy.context.scene;scene.unit_settings.system='METRIC';scene.unit_settings.scale_length=1
m.BUILD=bpy.data.collections.new('01_CONICAL_SEAT_EDITABLE_SOLIDS');scene.collection.children.link(m.BUILD)
m.HOST=bpy.data.collections.new('02_FACTORY_INTERFACE_REFERENCES');scene.collection.children.link(m.HOST)
m.P=P;m.OUT=P/'Export';m.TEX=P/'Textures'
scene.world=bpy.data.worlds.new('Neutral authoring world');scene.world.color=(.08,.08,.08)
iron=m.procedural_metal('AUTHOR_ConicalSeat_ForgedSteel',(.065,.072,.08),(.17,.18,.19),.40,.000065)
silver=m.procedural_metal('AUTHOR_ConicalSeat_DressedSteel',(.26,.28,.30),(.46,.48,.50),.29,.000018)
dark=m.procedural_metal('AUTHOR_ConicalSeat_Recess',(.018,.021,.026),(.045,.05,.058),.47,.000035)
# Retained interface helper uses this material name; recolor with the same steel.
bronze=iron
exec(compile((P/'native_interfaces.py').read_text('utf-8'),'<native interfaces>','exec'))

def factory(path,name):
    with bpy.data.libraries.load(str(path),link=False) as (src,dst):dst.objects=[name]
    obj=dst.objects[0];m.HOST.objects.link(obj);obj.hide_render=True;obj.hide_set(True)
    return obj

steel=factory(ROOT/'SourceAssets/ThunderGodHammer20261028/ModulesV1/ThunderGodHammer_Modular_Editable.blend','SM_ThunderGodHammer_head_mount_factory')

bpy.context.view_layer.update()

def outline(w,d):
    c=.20
    return [(-w*(1-c),-d),(w*(1-c),-d),(w,-d*(1-c)),(w,d*(1-c)),(w*(1-c),d),(-w*(1-c),d),(-w,d*(1-c)),(-w,-d*(1-c))]

def loft(name,cx,levels,mat,bevel=.0005):
    vs=[(cx+x,y,z) for z,w,d in levels for x,y in outline(w,d)]
    fs=[tuple(reversed(range(8))),tuple((len(levels)-1)*8+i for i in range(8))]
    for k in range(len(levels)-1):
        for j in range(8):fs.append((k*8+j,k*8+(j+1)%8,(k+1)*8+(j+1)%8,(k+1)*8+j))
    return m.solid(name,vs,fs,mat,bevel,5)

def cone(cx,z,scale):
    # Eight broad facets with narrow, physically modeled dressed ridges.
    ring=[]
    for i in range(8):
        a=Vector((math.cos(i*math.tau/8),math.sin(i*math.tau/8)))
        prev=Vector((math.cos((i-1)*math.tau/8),math.sin((i-1)*math.tau/8)))
        nxt=Vector((math.cos((i+1)*math.tau/8),math.sin((i+1)*math.tau/8)))
        ring.extend([a.lerp(prev,.075),a.lerp(nxt,.075)])
    levels=[(0,.0225),(.003,.0225),(.009,.0208),(.030,.0165),(.060,.0099),(.090,.0032),(.103,.00025)]
    vs=[(cx+p.x*r*scale,p.y*r*scale,z+h*scale) for h,r in levels for p in ring]
    fs=[tuple(reversed(range(16)))]
    for k in range(len(levels)-1):
        for j in range(16):fs.append((k*16+j,k*16+(j+1)%16,(k+1)*16+(j+1)%16,(k+1)*16+j))
    tip=len(vs);vs.append((cx,0,z+.1042*scale))
    for j in range(16):fs.append(((len(levels)-1)*16+j,(len(levels)-1)*16+(j+1)%16,tip))
    return m.solid('Solid_eight_facet_forward_cone',vs,fs,silver,0)

def bolt(f,x,z,depth):
    center=m.pt(f,x,z,depth);bf=m.frame(center,f[3],f[1])
    m.annulus('Machined_recess_washer',bf,.0016,.0038,-.0004,.0005,dark,48,bevel=.00012)
    # Solid screw head with a real recessed slot and seated dark floor.
    head=m.disk('Captive_slotted_steel_pin',bf,.0029,0,.0014,silver,48)
    cutter=m.strip('Slot_cutter',bf,[(-.0022,-.00035),(.0022,-.00035),(.0022,.00035),(-.0022,.00035)],.00075,.002,dark,0,[])
    m.activate(head);mod=head.modifiers.new('True_recessed_driver_slot','BOOLEAN');mod.operation='DIFFERENCE';mod.solver='EXACT';mod.object=cutter
    bpy.ops.object.modifier_apply(modifier=mod.name);bpy.data.objects.remove(cutter,do_unlink=True)
    bevel=head.modifiers.new('Dressed_pin_edges','BEVEL');bevel.width=.00010;bevel.segments=3
    m.strip('Recessed_slot_floor',bf,[(-.0021,-.0003),(.0021,-.0003),(.0021,.0003),(-.0021,.0003)],.00073,.00078,dark,.00004)

def engrave(plate,f,paths,depth):
    cutters=[]
    for path in paths:
        points=[m.pt(f,x,z,depth) for x,z in path]
        m.stroke('Engraving_cut_tool',points,.00042,dark,8,cutters)
        m.stroke('Recessed_dark_channel', [p-f[3]*.00028 for p in points],.00017,dark,8)
    cutter=m.join_group(cutters,'Engraving_boolean_tool');m.activate(plate)
    mod=plate.modifiers.new('Physically_recessed_forged_chevrons','BOOLEAN');mod.operation='DIFFERENCE';mod.solver='EXACT';mod.object=cutter
    bpy.ops.object.modifier_apply(modifier=mod.name);bpy.data.objects.remove(cutter,do_unlink=True)

def build(label,source,left,right,bottom,top):
    m.PARTS=[];m.ENERGY=[]
    cx=(left+right)*.5;w=(right-left)*.5-.0012;low=bottom+.010;high=top
    cz=(low+high)*.5;half=(high-low)*.5;depth=.026
    retain_interfaces(source,left,right,bottom)
    loft('Continuous_forged_load_core',cx,[(low,w*.70,depth*.76),(low+.010,w*.96,depth),(high-.016,w*.96,depth),(high,w*.77,depth*.84)],iron,.00085)
    for sy in (-1,1):
        f=m.frame((cx,sy*depth,cz),(0,sy,0),(-sy,0,0))
        plate=m.strip('Chamfered_reinforced_face_plate',f,outline(w*.88,half*.83),-.001,.0058,iron,.00075)
        # A restrained double-chevron directs the eye toward the thrust cone.
        paths=[]
        for shift in (-.010,.009):
            paths.append([(-w*.51,shift-.009),(0,shift+.004),(w*.51,shift-.009)])
        for x in (-w*.69,w*.69):paths.append([(x,-half*.58),(x,half*.55)])
        engrave(plate,f,paths,.0059)
        for x in (-w*.66,w*.66):
            for zz in (-half*.64,half*.64):bolt(f,x,zz,.006)
        # Fitted outer shoulder rails have real bevels, not painted highlights.
        for sign in (-1,1):
            shape=[(sign*w*.80,-half*.61),(sign*w*.91,-half*.52),(sign*w*.91,half*.51),(sign*w*.80,half*.64)]
            m.strip('Dressed_external_load_rail',f,shape,.0036,.0072,silver,.00035)
    loft('Stepped_cone_load_shoulder',cx,[(high-.004,w*.84,depth*.91),(high+.001,w*.84,depth*.91),(high+.005,w*.69,depth*.77)],iron,.0006)
    cf=m.frame((cx,0,high+.004),(0,0,1),(1,0,0));s=(right-left)/.08
    m.disk('Turned_solid_cone_socket',cf,.0247*s,-.001,.004,iron,96)
    m.annulus('Dressed_socket_outer_band',cf,.0228*s,.025*s,.0007,.0021,silver,96,bevel=.00018)
    m.annulus('Fine_recessed_socket_groove',cf,.0232*s,.0248*s,.0022,.0027,dark,96,bevel=.00007)
    cone(cx,high+.007,s)
    for obj in m.PARTS:obj['host_variant']=label
    bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(P/('ConicalSeat_'+label+'_Construction.blend')))
    model=m.join_group(m.PARTS,'ConicalSeat_'+label+'_Atlas')
    model.data.validate(clean_customdata=False)
    m.unwrap(model)
    # Use an 8px padded 4K atlas and actual tangent-space normal bake.
    src=(P/'solid_surface_tools.py').read_text('utf-8');start=src.index('def bake_maps(');end=src.index('\ndef finalize(',start)
    baker=src[start:end].replace('T_FinalToll_','T_ConicalSeat_'+label+'_').replace('M_FinalToll_PBR_Surface','M_ConicalSeat_'+label+'_Surface')
    exec(compile(baker,'<conical seat PBR>','exec'),m.__dict__);m.bake_maps(model)
    model.name='SM_ThunderGodHammer_ConicalSeat_V1';model['slot']='head_mount';model['option_id']='conical_seat'
    model['forward_in_old_head_thrust']='author +Z, along handle toward old head-thrust contact'
    model['native_interface_planes_m']=[left,right,bottom]
    m.activate(model);bpy.ops.object.transform_apply(location=True,rotation=True,scale=True)
    fbx=P/'Export'/(model.name+'.fbx')
    bpy.ops.export_scene.fbx(filepath=str(fbx),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',bake_anim=False,mesh_smooth_type='FACE',use_tspace=True,path_mode='COPY',embed_textures=False)
    glb=P/'Export'/(model.name+'.glb');bpy.ops.export_scene.gltf(filepath=str(glb),use_selection=True,export_format='GLB',export_materials='EXPORT')
    model.data.calc_loop_triangles()
    row={'variant':label,'mesh':model.name,'fbx':str(fbx),'glb':str(glb),'triangles':len(model.data.loop_triangles),'materials':[x.name for x in model.data.materials],
         'interface_planes_m':[left,right,bottom],'forward_axis':'+Z','location_cm':[0,0,0],'cone_length_cm':10.42*s}
    model.hide_render=True;model.hide_set(True)
    return model,row

models=[];rows=[]
for args in [('ThunderGod',steel,-.0654452141,.0645547859,.842,.990)]:
    obj,row=build(*args);models.append(obj);rows.append(row)
    (P/'production_receipt.json').write_text(json.dumps({'complete':False,'parts':rows},indent=2),encoding='utf-8')
for obj in list(bpy.context.scene.objects):
    if obj not in models:bpy.data.objects.remove(obj,do_unlink=True)
for i,obj in enumerate(models):obj.hide_render=i>0;obj.hide_set(i>0)
bpy.ops.file.pack_all()
final_scene=P/'ConicalHammerSeats_Editable.blend'
bpy.ops.wm.save_as_mainfile(filepath=str(final_scene))
(P/'production_receipt.json').write_text(json.dumps({'complete':True,'parts':rows,'pbr_resolution':4096,'normal_convention':'OpenGL tangent; UE flip green',
    'visual_tested':False,'runtime_registered':False,'scope':'models, textures, icon and saved UE assets; gameplay not enabled'},indent=2),encoding='utf-8')
print('CONICAL_SEATS_EXPORTED',flush=True)
