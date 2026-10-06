"""Author the square legendary thermal sight; model-only production stage.
Metres. +X forward, +Z up, origin at the top-rail bearing plane.
No preview render, application launch, gameplay change or acceptance test.
"""
import bpy,bmesh,json,math
from pathlib import Path
from mathutils import Matrix,Vector
P=Path(__file__).resolve().parents[3];O=P/'SourceAssets/ThermalScope20261006'
for sub in ('Model','Exports','Research'):(O/sub).mkdir(parents=True,exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True);bpy.context.preferences.filepaths.save_version=0
S=bpy.context.scene;S.unit_settings.system='METRIC';S.unit_settings.scale_length=1
M={};groups={k:[] for k in ('Body','RailMount','Display','ZoomSelector')};current='Body'
settings=[
 ('Thermal_Graphite',(.035,.043,.052,1),.78,.36),
 ('Thermal_Rubber',(.008,.010,.012,1),.0,.64),
 ('Thermal_Titanium',(.19,.23,.26,1),.9,.29),
 ('Thermal_Copper',(.53,.27,.075,1),.9,.3),
 ('Thermal_LegendRed',(.37,.015,.023,1),.65,.38),
 ('Thermal_Marking',(.56,.60,.58,1),.2,.5),
 ('Thermal_Objective',(.11,.047,.014,1),.72,.13),
 ('Thermal_Display',(.004,.008,.010,1),.0,.3),
]
for name,color,metal,rough in settings:
    mat=bpy.data.materials.new(name);mat.diffuse_color=color;mat.use_nodes=True
    bs=mat.node_tree.nodes.get('Principled BSDF');bs.inputs['Base Color'].default_value=color;bs.inputs['Metallic'].default_value=metal;bs.inputs['Roughness'].default_value=rough
    M[name]=mat

def select(ob):
    bpy.ops.object.select_all(action='DESELECT');ob.select_set(True);bpy.context.view_layer.objects.active=ob

def solid(name,verts,faces,mat='Thermal_Graphite',bevel=0):
    data=bpy.data.meshes.new(name);data.from_pydata(verts,[],faces);data.update()
    ob=bpy.data.objects.new(name,data);S.collection.objects.link(ob);data.materials.append(M[mat]);groups[current].append(ob)
    bm=bmesh.new();bm.from_mesh(data);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(data);bm.free()
    if bevel:
        select(ob);mod=ob.modifiers.new('Machined fillet','BEVEL');mod.width=bevel;mod.segments=3;bpy.ops.object.modifier_apply(modifier=mod.name)
    return ob

def prism(name,poly,axis,a,b,mat='Thermal_Graphite',bevel=0):
    n=len(poly);axes=[i for i in range(3) if i!=axis];vs=[]
    for c in (a,b):
        for p in poly:
            v=[0,0,0];v[axis]=c;v[axes[0]]=p[0];v[axes[1]]=p[1];vs.append(v)
    faces=[tuple(range(n-1,-1,-1)),tuple(range(n,n*2))]+[(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)]
    return solid(name,vs,faces,mat,bevel)

def box(name,center,size,mat='Thermal_Graphite',bevel=.00035):
    x,y,z=center;a,b,c=[s/2 for s in size]
    return prism(name,[(x-a,z-c),(x+a,z-c),(x+a,z+c),(x-a,z+c)],1,y-b,y+b,mat,bevel)

def octagon(w,h,c):return [(-w,-h+c),(-w+c,-h),(w-c,-h),(w,-h+c),(w,h-c),(w-c,h),(-w+c,h),(-w,h-c)]

def ring(name,x0,x1,outer,inner,z,mat='Thermal_Graphite',bevel=.00025):
    # Closed wall volume, open optical centre. No hidden cap across the window.
    loops=[octagon(*outer),octagon(*inner)];verts=[]
    for x,points in ((x0,loops[0]),(x1,loops[0]),(x0,loops[1]),(x1,loops[1])):verts.extend((x,y,z+v) for y,v in points)
    faces=[]
    for i in range(8):
        j=(i+1)%8;faces.extend([(i,j,j+8,i+8),(16+j,16+i,24+i,24+j),(i,16+i,16+j,j),(8+j,24+j,24+i,8+i)])
    return solid(name,verts,faces,mat,bevel)

def cylinder(name,center,radius,depth,axis='Z',mat='Thermal_Titanium',segments=48,bevel=.00015):
    bpy.ops.mesh.primitive_cylinder_add(vertices=segments,radius=radius,depth=depth,location=center)
    ob=bpy.context.object;ob.name=name
    if axis=='X':ob.rotation_euler.y=math.pi/2
    elif axis=='Y':ob.rotation_euler.x=math.pi/2
    ob.data.materials.append(M[mat]);groups[current].append(ob);bpy.ops.object.transform_apply(location=True,rotation=True,scale=True)
    if bevel:
        mod=ob.modifiers.new('Circular edge break','BEVEL');mod.width=bevel;mod.segments=3;bpy.ops.object.modifier_apply(modifier=mod.name)
    for f in ob.data.polygons:f.use_smooth=len(f.vertices)==4
    return ob

def label(name,text,position,size,basis,mat='Thermal_Marking'):
    curve=bpy.data.curves.new(name,'FONT');curve.body=text;curve.size=size;curve.extrude=.000012;curve.resolution_u=3;curve.align_x='CENTER';curve.align_y='CENTER'
    ob=bpy.data.objects.new(name,curve);S.collection.objects.link(ob);ob.location=position;ob.rotation_euler=basis.to_euler();curve.materials.append(M[mat]);select(ob);bpy.ops.object.convert(target='MESH');bpy.ops.object.transform_apply(location=True,rotation=True,scale=True);groups[current].append(ob)
    return ob

zc=.0375
# A thick square hood and stepped rear eyecup establish the silhouette.
ring('Continuous sealed square optical chassis',-.037,.036,(.0225,.0225,.004),(.0186,.0164,.0028),zc,bevel=.0006)
ring('Front impact shroud',.031,.045,(.0235,.0235,.005),(.0188,.0172,.0032),zc,bevel=.00055)
ring('Copper objective rim',.0405,.0417,(.0195,.018,.003),(.0177,.0162,.0025),zc,'Thermal_Copper',.00018)
ring('Objective light baffle',.034,.041,(.0178,.0163,.0025),(.0158,.0143,.002),zc,'Thermal_Rubber',.00018)
prism('Recessed coated IR sensor window',[(y,zc+z) for y,z in octagon(.0158,.0143,.002)],0,.033,.0337,'Thermal_Objective',.0002)
# Separate window well and permanent internal electronics bulkhead. The rear
# display is intentionally digital; it will not be used as a glass-through ADS.
ring('Rear eyepiece armor',-.044,-.032,(.024,.0225,.0045),(.0188,.0165,.0028),zc,bevel=.0005)
ring('Soft rectangular eye seal',-.054,-.040,(.0248,.0233,.0048),(.0185,.0160,.0026),zc,'Thermal_Rubber',.00045)
ring('Inner display blackout surround',-.042,-.024,(.0185,.0160,.0026),(.0173,.0141,.0018),zc,'Thermal_Rubber',.0002)
box('Internal electronics housing',(.022,0,.0375),(.012,.035,.031),'Thermal_Graphite',.0007)
# Side armor, battery cassette, cooling ribs and service covers have thickness.
panel=[(-.030,.018),(.026,.018),(.034,.026),(.034,.049),(.026,.056),(-.030,.056)]
for side in (-1,1):
    prism('Chamfered side armor',panel,1,side*.0224,side*.0234,'Thermal_Graphite',.00045)
    for x,z in ((-.026,.021),(-.026,.053),(.026,.022),(.029,.050)):
        cylinder('Captive panel screw',(x,side*.02365,z),.00125,.00085,'Y','Thermal_Titanium',24)
    box('Side copper identification inlay',(-.014,side*.0235,.054),(.019,.00042,.00055),'Thermal_Copper',.00014)
box('Replaceable side battery cassette',(.010,-.0255,.0335),(.044,.008,.021),'Thermal_Graphite',.0012)
box('Battery hatch rubber gasket',(.010,-.0293,.0335),(.039,.0005,.017),'Thermal_Rubber',.0005)
box('Battery hatch cover',(.010,-.0297,.0335),(.036,.0012,.014),'Thermal_Graphite',.0006)
for x in (-.004,.024):cylinder('Battery hatch screw',(x,-.0305,.0335),.0014,.0007,'Y','Thermal_Titanium',24)
for x in (.014,.019,.024,.029):box('Front thermal management rib',(x,.024,.043),(.002,.003,.018),'Thermal_Graphite',.0003)
box('Legendary red identity tab',(-.022,-.0237,.034),(.003,.001,.009),'Thermal_LegendRed',.0004)
# Upper buttons are tactile and individually recessed into the top housing.
for x in (-.021,-.004):
    box('Recessed button surround',(x,0,.0600),(.011,.012,.0014),'Thermal_Titanium',.001)
    box('Top control rubber', (x,0,.0607),(.0088,.0098,.002),'Thermal_Rubber',.001)
label('Power key symbol','I',(-.021,0,.06171),.003,Matrix.Identity(3))
label('Mode key symbol','M',(-.004,0,.06171),.003,Matrix.Identity(3))
topbasis=Matrix.Identity(3)
box('Inset upper designation plate',(.021,0,.0604),(.021,.010,.0012),'Thermal_Graphite',.00035)
label('Top designation','IR-X8',(.021,0,.06101),.0044,topbasis)
# Local text X = weapon X, local text Y = weapon Z, outward = -Y.
sidebasis=Matrix(((1,0,0),(0,0,-1),(0,1,0)))
label('Battery designation','THERMAL',(.010,-.03031,.0338),.0036,sidebasis)
positive_y_text=Matrix(((-1,0,0),(0,0,1),(0,1,0)))
label('Body magnification specification','1.5 / 3 / 8',(-.007,.02342,.0200),.0021,positive_y_text)
cylinder('Fixed zoom spindle boss',(-.010,.0245,.040),.006,.004,'Y','Thermal_Titanium',48)

# Detachable low-profile interface. Its rail-contact plane is the master origin.
current='RailMount'
box('Rail bearing plate',(0,0,.0035),(.055,.026,.007),'Thermal_Graphite',.0006)
for x in (-.016,.016):box('Integrated body pedestal',(x,0,.0108),(.015,.026,.0098),'Thermal_Graphite',.0005)
for sign in (-1,1):
    section=[(sign*y,z) for y,z in ((.0105,.0001),(.0105,.0048),(.015,.0048),(.0140,-.0035),(.0120,-.0035),(.0107,-.0018))]
    prism('Angled rail clamping jaw',section,0,-.022,.022,'Thermal_Titanium',.00025)
box('Rail recoil key',(0,0,-.0008),(.0046,.020,.002),'Thermal_Titanium',.00015)
cylinder('QD lever pivot',(-.014,-.0162,.0022),.0042,.003,'Y','Thermal_Titanium',48)
box('QD locking lever',(-.002,-.0186,.003),(.028,.005,.0055),'Thermal_Graphite',.001)
box('QD grip insert',(.007,-.0213,.003),(.008,.0008,.0035),'Thermal_Rubber',.0004)
for x in (-.016,.016):cylinder('Clamp captive bolt',(x,.0152,.0027),.0021,.0014,'Y','Thermal_Titanium',32)

# Display panel is a separate mesh with a dedicated 0..1 image UV.
current='Display'
display=prism('Replaceable rectangular thermal display',[(y,zc+z) for y,z in octagon(.0172,.014,.0018)],0,-.029,-.0285,'Thermal_Display',0)

current='ZoomSelector';pivot=Vector((-.010,.027,.040))
cylinder('Three detent selector base',pivot,.010,.005,'Y','Thermal_Graphite',64,.0003)
cylinder('Selector copper rim',(-.010,.030,.040),.0093,.0012,'Y','Thermal_Copper',64)
cylinder('Selector finger face',(-.010,.0309,.040),.0084,.0011,'Y','Thermal_Rubber',64)
for i in range(32):
    a=math.tau*i/32;ob=box('Selector knurl',(-.010+math.sin(a)*.0098,.0275,.040+math.cos(a)*.0098),(.0009,.005,.0012),'Thermal_Graphite',.00018)
    # Box vertices are absolute; rotate each tooth around its own centre.
    centre=Vector((-.010+math.sin(a)*.0098,.0275,.040+math.cos(a)*.0098));ob.data.transform(Matrix.Translation(centre)@Matrix.Rotation(a,4,'Y')@Matrix.Translation(-centre))
box('Selector index bar',(-.010,.0317,.0450),(.001,.0007,.004),'Thermal_Marking',.0001)
current='Body'
for angle,number in ((-70,'1.5'),(0,'3'),(70,'8')):
    a=math.radians(angle);label('Fixed zoom detent '+number,number,(-.010+math.sin(a)*.0130,.02342,.040+math.cos(a)*.0130),.0023,positive_y_text)
# The saved model starts at the requested 1.5x detent.
default_selector=Matrix.Translation(pivot)@Matrix.Rotation(math.radians(-70),4,'Y')@Matrix.Translation(-pivot)
for ob in groups['ZoomSelector']:ob.data.transform(default_selector)

def uv_and_tri(ob):
    select(ob);tri=ob.modifiers.new('Export triangles','TRIANGULATE');bpy.ops.object.modifier_apply(modifier=tri.name)
    mesh=ob.data;uv=mesh.uv_layers.new(name='SurfaceUV')
    for f in mesh.polygons:
        axis=max(range(3),key=lambda k:abs(f.normal[k]));axes=[k for k in range(3) if k!=axis]
        for li in f.loop_indices:
            v=mesh.vertices[mesh.loops[li].vertex_index].co
            uv.data[li].uv=((v.y+.0172)/.0344,(v.z-(zc-.014))/.028) if ob==display else (v[axes[0]]/.020,v[axes[1]]/.020)
for group in groups.values():
    for ob in group:uv_and_tri(ob)

SOCKETS={'Mount':(0,0,0),'SightRear':(-.055,0,zc),'SightFront':(.044,0,zc),'SightUp':(-.055,0,zc+.01),'DisplayCenter':(-.029,0,zc),'ZoomPivot':tuple(pivot)}
for name,position in SOCKETS.items():
    ob=bpy.data.objects.new(name,None);S.collection.objects.link(ob);ob.location=position;ob.empty_display_size=.003
    ob['Purpose']='Interface marker; reference only, not additional mesh'
S['ThermalScopeStage']='model_only';S['MagnificationSteps']='1.5,3,8';S['MountPlane']='Rail bearing Z=0; forward +X';S['OpticalDisplay']='Separate digital panel; thermal feed not connected'
bpy.ops.wm.save_as_mainfile(filepath=str(O/'Model/ThermalScope_Editable.blend'))

def combined(name,objects,origin=Vector()):
    copies=[]
    for old in objects:
        ob=old.copy();ob.data=old.data.copy();S.collection.objects.link(ob);copies.append(ob)
    bpy.ops.object.select_all(action='DESELECT')
    for ob in copies:ob.select_set(True)
    bpy.context.view_layer.objects.active=copies[0]
    if len(copies)>1:bpy.ops.object.join()
    ob=bpy.context.object;ob.name=name
    S.cursor.location=origin;bpy.ops.object.origin_set(type='ORIGIN_CURSOR');return ob

def export(ob,name,sockets=None):
    select(ob);empties=[]
    for key,pos in (sockets or {}).items():
        e=bpy.data.objects.new('SOCKET_'+key,None);S.collection.objects.link(e);e.parent=ob;e.location=Vector(pos)-ob.location;e.select_set(True);empties.append(e)
    path=O/'Exports'/(name+'.fbx');bpy.ops.export_scene.fbx(filepath=str(path),use_selection=True,object_types={'MESH','EMPTY'},axis_forward='-Y',axis_up='Z',add_leaf_bones=False,bake_anim=False,mesh_smooth_type='FACE',use_tspace=True)
    ob.data.calc_loop_triangles();result={'fbx':str(path),'triangles':len(ob.data.loop_triangles),'slots':[m.name for m in ob.data.materials],'sockets_ue_cm':{k:[p[0]*100,-p[1]*100,p[2]*100] for k,p in (sockets or {}).items()}}
    for e in empties:bpy.data.objects.remove(e,do_unlink=True)
    return result

models={}
allparts=[ob for group in groups.values() for ob in group]
assembly=combined('SM_ThermalScope_Assembly',allparts);models[assembly.name]=export(assembly,assembly.name,SOCKETS)
select(assembly);bpy.ops.export_scene.gltf(filepath=str(O/'Model/ThermalScope_Assembly.glb'),export_format='GLB',use_selection=True,export_yup=True)
bpy.data.objects.remove(assembly,do_unlink=True)
for key,objects in groups.items():
    ob=combined('SM_ThermalScope_'+key,objects,pivot if key=='ZoomSelector' else Vector())
    # Part FBXs share the master frame except for the independently rotating dial.
    if key=='ZoomSelector':ob.location=Vector()
    models[ob.name]=export(ob,ob.name,SOCKETS if key=='Body' else None)
    bpy.data.objects.remove(ob,do_unlink=True)
report={'name':'热成像瞄准镜','id':'thermal_scope','rarity':'legendary','card_color':'red','stage':'model_only','default_magnification':1.5,'magnification_steps':[1.5,3,8],
 'forward_axis':'+X','units':'metres in Blender; centimetres in UE','origin':'rail bearing plane','optical_axis_height_mm':zc*1000,
 'rear_display_mm':[34.4,28.0],'body_envelope_mm':[99,49.6,46.6],'nominal_rail_width_mm':21.2,'zoom_selector_component_offset_ue_cm':[pivot.x*100,-pivot.y*100,pivot.z*100],
 'selector_relative_detents_blender_y_degrees':[0,70,140],
 'models':models,'materials':[dict(name=n,color=c,metallic=m,roughness=r) for n,c,m,r in settings],
 'target_visual_design':{'background':'cold dark grayscale','monsters':'white-hot body with warm yellow/orange edge','fire':'white/yellow core and orange falloff','cloaked_monsters':'thermal target mask independent of visible cloak alpha','occlusion':'solid walls occlude; no wall vision implied'},
 'runtime_integrated':False,'game_tested':False,'model_provenance':'Original parametric hard-surface geometry; no third-party meshes or texture maps copied'}
(O/'authoring.json').write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding='utf-8')
print('THERMAL_SCOPE_MODELS_EXPORTED '+json.dumps({k:v['triangles'] for k,v in models.items()}))
