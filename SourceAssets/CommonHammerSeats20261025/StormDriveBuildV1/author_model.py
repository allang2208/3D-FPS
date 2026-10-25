"""Approved Storm Drive seat: two native interfaces, solid gothic trim and 4K PBR."""
import ast,bpy,bmesh,types,math,json,sys
from pathlib import Path
from mathutils import Vector
P=Path(__file__).resolve().parent;ROOT=P.parents[2]
RUNE=ROOT/'SourceAssets/RuneboundWarhammer20261022'
code=(RUNE/'FinalTollHammerHeadV2/author_model.py').read_text('utf-8')
m=types.ModuleType('storm_drive_tools');m.__file__=str(P/'author_model.py')
exec(compile(code,'<retained_solid_modelling_tools>','exec'),m.__dict__)
m.P=RUNE/'StarTideCoreV1';m.initialize();m.P=P
m.BUILD.name='01_STORM_DRIVE_Editable_Components'
sys.path.insert(0,str(RUNE/'HeadRunePBRV3'))
from surface_authoring import refine_metal
iron=m.procedural_metal('AUTHOR_StormDrive_BlackIron',(.045,.052,.061),(.135,.15,.17),.40,.000045)
bronze=m.procedural_metal('AUTHOR_StormDrive_AgedBronze',(.16,.105,.042),(.39,.27,.105),.33,.000025)
silver=m.procedural_metal('AUTHOR_StormDrive_IvorySilver',(.26,.28,.30),(.51,.52,.53),.29,.000016)
dark=m.procedural_metal('AUTHOR_StormDrive_Cavity',(.012,.014,.018),(.03,.034,.039),.49,.00002)
for mat in (iron,bronze,silver,dark):refine_metal(mat)
energy=m.simple_material('M_StormDrive_GoldInlay',(.32,.17,.018),.15,.22)
bsdf=energy.node_tree.nodes.get('Principled BSDF');bsdf.inputs['Emission Color'].default_value=(1,.61,.045,1);bsdf.inputs['Emission Strength'].default_value=2.5
native=ast.parse((ROOT/'SourceAssets/CommonHammerSeats20261024/AncientSealBuildV1/author_model.py').read_text('utf-8'))
exec(compile(ast.Module(body=[n for n in native.body if isinstance(n,ast.FunctionDef) and n.name in ('clip','retain_interfaces','octagon','outline_stroke')],type_ignores=[]),'<native_contact_preservation>','exec'))
with bpy.data.libraries.load(str(ROOT/'SourceAssets/SteelWarhammer20261014/ModulesV1/Warhammer_Modular_Editable.blend'),link=False) as (a,b):b.objects=['SM_Warhammer_head_mount_factory']
steel=b.objects[0];m.HOST.objects.link(steel);steel.hide_render=True

def loft(name,cx,levels,mat,bevel=.0006):
    verts=[(cx+x,y,z) for z,w,d in levels for x,y in octagon(w,d,.24)]
    faces=[tuple(reversed(range(8))),tuple((len(levels)-1)*8+i for i in range(8))]
    for k in range(len(levels)-1):
        for j in range(8):faces.append((k*8+j,k*8+(j+1)%8,(k+1)*8+(j+1)%8,(k+1)*8+j))
    return m.solid(name,verts,faces,mat,bevel,5)

def arch(w,h):
    pts=[(-w,-h),(w,-h),(w,h*.30)]
    for i in range(1,19):
        t=i/18;pts.append(((1-t)**2*w+2*(1-t)*t*w*.83,(1-t)**2*h*.30+2*(1-t)*t*h*.75+t*t*h))
    pts += [(-x,z) for x,z in reversed(pts[2:-1])]
    return pts

def ring(name,f,outer,inner,d0,d1,mat):
    n=len(outer);verts=[m.pt(f,x,z,d) for d,path in ((d0,outer),(d1,outer),(d1,inner),(d0,inner)) for x,z in path]
    faces=[]
    for k in range(4):
        for i in range(n):faces.append((k*n+i,k*n+(i+1)%n,((k+1)%4)*n+(i+1)%n,((k+1)%4)*n+i))
    return m.solid(name,verts,faces,mat,.00024,4)

def cut_inlay(carrier,f,paths,top,mat=energy,width=.00048):
    cutters=[]
    for path in paths:
        shape=outline_stroke(path,width)
        m.strip('EDITABLE_carved_channel',f,shape,top-.00065,top+.0004,iron,0,cutters)
        group=m.ENERGY if mat==energy else m.PARTS
        m.strip('Inset_lightning_rune' if mat==energy else 'Inlaid_ancient_letter',f,outline_stroke(path,width*.63),top-.00059,top-.00025,mat,.00006,group)
    cutter=m.join_group(cutters,'True_recess_tool');m.activate(carrier)
    mod=carrier.modifiers.new('Actual inset engraving','BOOLEAN');mod.operation='DIFFERENCE';mod.solver='EXACT';mod.object=cutter;mod.use_self=True
    bpy.ops.object.modifier_apply(modifier=mod.name);bpy.data.objects.remove(cutter,do_unlink=True)

def star(f,x,z,size,depth):
    shape=[(x,z+size),(x+size*.20,z+size*.22),(x+size*.66,z),(x+size*.20,z-size*.22),(x,z-size),(x-size*.20,z-size*.22),(x-size*.66,z),(x-size*.20,z+size*.22)]
    m.strip('Seated_four_point_bronze_finial',f,shape,depth-.0004,depth+.001,bronze,.00017)
    m.stroke('Silver_finial_chasing',[m.pt(f,x,z+size*.65,depth+.001),m.pt(f,x,z,depth+.0012),m.pt(f,x,z-size*.65,depth+.001)],.00016,silver,6)

def build(label,factory,left,right,bottom,top):
    m.PARTS=[];m.ENERGY=[]
    cx=(left+right)/2;w=(right-left)/2-.0015;depth=.0255 if label=='Steel' else .024
    retain_interfaces(factory,left,right,bottom)
    low=bottom+.012;high=top;cz=(high+low)/2;h=(high-low)*.5
    loft('Continuous_black_iron_load_core',cx,[(low,w*.65,depth*.78),(low+.009,w*.86,depth),(low+.023,w*.97,depth),
        (high-.021,w*.97,depth),(high-.010,w*.82,depth*.9),(high,w*.68,depth*.80)],iron)
    for sy in (-1,1):
        f=m.frame((cx,sy*depth,cz),(0,sy,0),(-sy,0,0))
        outer=arch(w*.88,h*.91);inner=arch(w*.66,h*.76)
        ring('Solid_pointed_gothic_vault',f,outer,inner,-.001,.009,iron)
        ring('Embedded_bronze_arch_arris',f,arch(w*.70,h*.80),inner,.008,.0095,bronze)
        # A real cavity with its rear wall and a separate solid tone plate.
        m.strip('Deep_arch_rear_wall',f,inner,-.0005,.0006,dark,.00025)
        plate=m.strip('Solid_vertical_resonance_plate',f,arch(w*.29,h*.72),.0007,.0045,bronze,.0004)
        s=h/.06
        lightning=[[(.002,.040),(-.004,.022),(.002,.023),(-.006,.001),(.003,.005),(-.003,-.023),(.001,-.040)],
                   [(-.001,.013),(.006,.020),(.005,.030)],[(0,-.009),(-.007,-.015),(-.006,-.023)]]
        cut_inlay(plate,f,[[(x*s,z*s) for x,z in path] for path in lightning],.0045,width=.00062)
        for side in (-1,1):
            # Turned conductive columns sit between the plate and structural arch.
            x=side*w*.46
            cf=m.frame(m.pt(f,x,-h*.68,.0042),(0,0,1),(1,0,0))
            m.disk('Supported_bronze_conductor',cf,.0019,0,h*1.25,bronze,40)
            for dz,r,hh in ((0,.0032,.004),(h*.11,.0027,.002),(h*.98,.0028,.0025),(h*1.20,.0031,.004)):
                m.disk('Turned_conductor_contact',cf,r,dz,dz+hh,silver if dz==0 else bronze,40)
            rail=m.strip('Solid_inscribed_outer_buttress',f,[(side*w*.79-.0022,-h*.68),(side*w*.79+.0022,-h*.68),(side*w*.79+.0022,h*.52),(side*w*.79-.0022,h*.52)],.006,.011,bronze,.0003)
            glyphs=[]
            for j in range(10):
                zz=-h*.58+j*h*.105
                for path in m.GLYPHS[(j*3+(sy+1))%len(m.GLYPHS)]:glyphs.append([(side*w*.79+a*.0023,zz+b*.0031) for a,b in path])
            cut_inlay(rail,f,glyphs,.011,silver,.00018)
            for z in (-h*.71,h*.55):
                m.strip('Recessed_square_pin_seat',f,[(side*w*.79-.0035,z-.0035),(side*w*.79+.0035,z-.0035),(side*w*.79+.0035,z+.0035),(side*w*.79-.0035,z+.0035)],.008,.0122,bronze,.00035)
                m.disk('Silver_captive_pin',m.frame(m.pt(f,side*w*.79,z,.0122),f[3],f[1]),.0012,0,.0009,silver,32)
            path=[m.pt(f,side*x,z,.0098) for x,z in [(w*.70,-h*.83),(w*.91,-h*.61),(w*.96,-h*.36),(w*.96,h*.45),(w*.74,h*.75),(w*.49,h*.93)]]
            m.stroke('Continuous_ivory_silver_edge',path,.00075,silver,10)
        star(f,0,h*.76,.0083,.0095)
        # Fine seated bronze tracing under the pointed cap and base.
        for z in (-h*.84,h*.94):
            for j in range(-3,4):
                x=j*w*.18
                m.disk('Small_flush_binding_rivet',m.frame(m.pt(f,x,z,.0045),f[3],f[1]),.0007,-.0002,.00035,bronze,20)
    # Roof and collar are continuous, beveled, fixed solids.
    for z,ww,dd,th,mat in [(high+.001,w*.70,depth*.83,.004,silver),(high-.004,w*.78,depth*.94,.003,bronze),
                           (low+.004,w*.75,depth*.91,.004,bronze),(bottom+.010,w*.64,depth*.78,.004,silver)]:
        loft('Stepped_gothic_cap_and_binding',cx,[(z-th/2,ww*.96,dd*.96),(z,ww,dd),(z+th/2,ww*.96,dd*.96)],mat,.0003)
    collar=m.frame((cx,0,bottom+.008),(0,0,1),(1,0,0))
    m.disk('Continuous_retained_socket_sleeve',collar,w*.63,-.002,.009,iron,80)
    for z in (0,.007):m.annulus('Bronze_socket_band',collar,w*.60,w*.65,z,z+.0015,bronze,80,bevel=.0002)
    for obj in m.PARTS+m.ENERGY:obj['host_variant']=label
    bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(P/('StormDrive_'+label+'_Construction.blend')))
    metal=m.join_group(m.PARTS,'StormDrive_'+label+'_Atlas');m.unwrap(metal)
    start=code.index('def bake_maps(');end=code.index('\ndef finalize(',start)
    bake=code[start:end].replace('T_FinalToll_','T_StormDrive_'+label+'_').replace('M_FinalToll_PBR_Surface','M_StormDrive_'+label+'_Surface')
    exec(compile(bake,'<storm_drive_4k_pbr>','exec'),m.__dict__);m.bake_maps(metal)
    glow=m.join_group(m.ENERGY,'StormDrive_'+label+'_GoldInlay');m.unwrap(glow)
    obj=m.join_group([metal,glow],'SM_'+label+'Warhammer_StormDrive_V1');obj.location=(0,0,0)
    obj['native_cut_planes']=[left,right,bottom];obj['slot']='head_mount';obj['option_id']='storm_drive_seat'
    m.activate(obj);fbx=P/'Export'/(obj.name+'.fbx')
    bpy.ops.export_scene.fbx(filepath=str(fbx),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',bake_anim=False,mesh_smooth_type='FACE',use_tspace=True,path_mode='COPY',embed_textures=False)
    obj.data.calc_loop_triangles()
    row={'variant':label,'mesh':obj.name,'fbx':str(fbx),'triangles':len(obj.data.loop_triangles),'materials':[v.name for v in obj.data.materials],
        'native_cut_planes_m':[left,right,bottom],'location_cm':[0,0,0],'center_cm':[cx*100,0,cz*100]}
    print('STORM_DRIVE_VARIANT_EXPORTED '+json.dumps(row),flush=True)
    return obj,row

models=[];rows=[]
for args in [('Steel',steel,-.04,.04,.865,.985),('Runebound',bpy.data.objects['SM_RuneboundWarhammer_head_mount_factory'],-.0354452141,.0345547859,.842,.980)]:
    obj,row=build(*args);models.append(obj);rows.append(row);obj.hide_render=True;obj.hide_set(True)
    (P/'production_receipt.json').write_text(json.dumps({'complete':False,'parts':rows},indent=2),encoding='utf-8')
for obj in list(bpy.context.scene.objects):
    if obj not in models:bpy.data.objects.remove(obj,do_unlink=True)
for i,obj in enumerate(models):obj.hide_render=i>0;obj.hide_set(i>0)
bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(P/'StormDriveSeats_Editable.blend'))
(P/'production_receipt.json').write_text(json.dumps({'complete':True,'parts':rows,'pbr_resolution':4096,'normal_convention':'OpenGL tangent; UE flip green','visual_tested':False},indent=2),encoding='utf-8')
print('STORM_DRIVE_BOTH_MODELS_EXPORTED',flush=True)
