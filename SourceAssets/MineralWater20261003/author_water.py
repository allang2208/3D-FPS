"""Fab source derivative and original water cavity; production assets and icons.
No UE launch, gameplay run, previews or acceptance renders.
"""
import bpy,bmesh,json,math,shutil
from pathlib import Path
from mathutils import Vector,Matrix
OUT=Path(__file__).resolve().parent
SRC=Path('D:/FPS3D/VaultCache/FabLibrary/Plastic_Water_Bottle-543bb27e/fbx/water_bottle_extracted/Files/Water Bottle.blend')
EXP=OUT/'Export';EXP.mkdir(exist_ok=True)
ICON=Path('D:/FPS3D/FPSGAME/Content/ColdSteelData/Icons')
bpy.ops.wm.open_mainfile(filepath=str(SRC))
body=bpy.data.objects['Cylinder_Material.003_0']
label=bpy.data.objects['Cylinder_water lable_0']
cap=bpy.data.objects['Object_5_Material.002_0']
points=[body.matrix_world@Vector(c) for c in body.bound_box]
floor=min(v.z for v in points)
cx=(min(v.x for v in points)+max(v.x for v in points))*.5
cy=(min(v.y for v in points)+max(v.y for v in points))*.5
top=max((cap.matrix_world@Vector(c)).z for c in cap.bound_box)
scale=.22/(top-floor)
keep=(body,label,cap)
for obj in list(bpy.data.objects):
    if obj not in keep:bpy.data.objects.remove(obj,do_unlink=True)
bpy.context.scene.unit_settings.system='METRIC';bpy.context.scene.unit_settings.scale_length=1
for obj in keep:
    obj.data=obj.data.copy()
    transform=obj.matrix_world.copy()
    for vertex in obj.data.vertices:
        vertex.co=(transform@vertex.co-Vector((cx,cy,floor)))*scale
    obj.matrix_world=Matrix.Identity(4)
    # Remove import seam duplicates while preserving the authored ribs and profile.
    bm=bmesh.new();bm.from_mesh(obj.data)
    bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=.000001)
    bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(obj.data);bm.free()
    for poly in obj.data.polygons:poly.use_smooth=True

def mat(name,color,rough,transmission=0):
    m=bpy.data.materials.new(name);m.use_nodes=True;m.diffuse_color=(*color,1)
    n=next((n for n in m.node_tree.nodes if n.type=='BSDF_PRINCIPLED'),None)
    if n is None:
        n=m.node_tree.nodes.new('ShaderNodeBsdfPrincipled')
        output=next((n for n in m.node_tree.nodes if n.type=='OUTPUT_MATERIAL'),None) or m.node_tree.nodes.new('ShaderNodeOutputMaterial')
        m.node_tree.links.new(n.outputs['BSDF'],output.inputs['Surface'])
    n.name='WaterPrincipled'
    n.inputs['Base Color'].default_value=(*color,1)
    n.inputs['Roughness'].default_value=rough
    n.inputs['Transmission Weight'].default_value=transmission
    n.inputs['IOR'].default_value=1.46 if name=='PET' else 1.333
    return m
pet=mat('PET',(.91,.96,.945),.11,1)
lid=mat('Cap',(.019,.19,.105),.32)
paper=mat('Label',(.86,.91,.85),.58)
watermat=mat('Liquid',(.80,.93,.965),.045,1)
tex=bpy.data.images.load(str(OUT/'Textures/T_MineralWater_Label.png'));tex.pack()
n=paper.node_tree.nodes.new('ShaderNodeTexImage');n.image=tex
paper.node_tree.links.new(n.outputs['Color'],paper.node_tree.nodes['WaterPrincipled'].inputs['Base Color'])
for obj,m,name in ((body,pet,'Body_Source'),(label,paper,'Label_Source'),(cap,lid,'SM_MineralWater_Cap')):
    obj.data.materials.clear();obj.data.materials.append(m);obj.name=name

# Expose the inner neck after uncapping. Preserve the original outer mouth rim.
bm=bmesh.new();bm.from_mesh(body.data)
faces=[f for f in bm.faces if min(v.co.z for v in f.verts)>.215 and max(math.hypot(v.co.x,v.co.y) for v in f.verts)<.0105 and abs(f.normal.z)>.8]
if faces:bmesh.ops.delete(bm,geom=faces,context='FACES')
bm.to_mesh(body.data);bm.free()

# A smaller label leaves the half-full meniscus visible below its bottom edge.
zlo=min(v.co.z for v in label.data.vertices);zhi=max(v.co.z for v in label.data.vertices)
for v in label.data.vertices:v.co.z=.102+(v.co.z-zlo)/(zhi-zlo)*.042
uv=label.data.uv_layers.active or label.data.uv_layers.new(name='UVMap')
for poly in label.data.polygons:
    values=[]
    for index in poly.loop_indices:
        v=label.data.vertices[label.data.loops[index].vertex_index].co
        values.append(((math.atan2(v.y,v.x)/(2*math.pi))%1,(v.z-.102)/.042,index))
    seam=max(v[0] for v in values)-min(v[0] for v in values)>.5
    for u,v,index in values:uv.data[index].uv=(u+1 if seam and u<.5 else u,v)

def lathe(name,profile,material,segments=96):
    verts=[];faces=[]
    for z,r in profile:
        for i in range(segments):
            a=i*math.tau/segments;verts.append((math.cos(a)*r,math.sin(a)*r,z))
    for j in range(len(profile)-1):
        for i in range(segments):
            k=(i+1)%segments;faces.append((j*segments+i,j*segments+k,(j+1)*segments+k,(j+1)*segments+i))
    faces.append(tuple(range(segments-1,-1,-1)))
    faces.append(tuple((len(profile)-1)*segments+i for i in range(segments)))
    mesh=bpy.data.meshes.new(name);mesh.from_pydata(verts,[],faces);mesh.materials.append(material)
    obj=bpy.data.objects.new(name,mesh);bpy.context.collection.objects.link(obj)
    for p in mesh.polygons:p.use_smooth=len(p.vertices)==4
    return obj
liquid=lathe('SM_MineralWater_Liquid',[(.0035,.024),(.007,.0261),(.013,.0270),(.030,.0270),(.085,.0270),(.130,.0270),(.153,.0269),(.165,.0257),(.175,.0234),(.1835,.0202),(.184,.0200)],watermat)
# The water mesh's upper rings collapse to the level, creating a closed flat cap.
half=liquid.copy();half.data=liquid.data.copy();half.name='Water_Half_Source';bpy.context.collection.objects.link(half)
halflevel=(.0035+.184)*.5
for v in half.data.vertices:v.co.z=min(v.co.z,halflevel)

def clone(obj):
    q=obj.copy();q.data=obj.data.copy();bpy.context.collection.objects.link(q);return q
def join(objects,name):
    bpy.ops.object.select_all(action='DESELECT')
    for obj in objects:obj.select_set(True)
    bpy.context.view_layer.objects.active=objects[0];bpy.ops.object.join()
    obj=bpy.context.object;obj.name=name
    obj.data.calc_loop_triangles()
    return obj
shell=join([body,label],'SM_MineralWater_Shell')
full=join([clone(shell),clone(cap),clone(liquid)],'SM_MineralWater_Full')
halfclosed=join([clone(shell),clone(cap),half],'SM_MineralWater_Half')
parts=[shell,cap,liquid,full,halfclosed]
receipt={'source':str(SRC),'listing':'https://www.fab.com/listings/543bb27e-896f-4603-aa12-5fb565b4ea60','height_cm':22,'fill_full_cm':18.4,'fill_half_cm':9.375,'meshes':{},'icons':[],'runtime_tested':False}

for obj in parts:
    bpy.ops.object.select_all(action='DESELECT');obj.select_set(True);bpy.context.view_layer.objects.active=obj
    # Explicit simple convex collisions are used for transient props; pickups have
    # the existing native box root, independent of transparent visual triangles.
    bb=[Vector(c) for c in obj.bound_box];lo=Vector(tuple(min(p[i] for p in bb) for i in range(3)));hi=Vector(tuple(max(p[i] for p in bb) for i in range(3)))
    bpy.ops.mesh.primitive_cube_add(size=1,location=(lo+hi)*.5)
    collision=bpy.context.object;collision.name='UCX_'+obj.name+'_00';collision.dimensions=hi-lo
    bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    bpy.ops.object.select_all(action='DESELECT');obj.select_set(True);collision.select_set(True);bpy.context.view_layer.objects.active=obj
    path=EXP/(obj.name+'.fbx')
    bpy.ops.export_scene.fbx(filepath=str(path),use_selection=True,object_types={'MESH'},global_scale=1,apply_unit_scale=True,axis_forward='-Y',axis_up='Z',add_leaf_bones=False,mesh_smooth_type='FACE',use_mesh_modifiers=True,path_mode='STRIP')
    bpy.data.objects.remove(collision,do_unlink=True)
    obj.data.calc_loop_triangles()
    receipt['meshes'][obj.name]={'file':str(path),'triangles':len(obj.data.loop_triangles),'materials':[m.name for m in obj.data.materials]}

# Production inventory icons from the same authored geometry. No review gallery.
scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=48
scene.cycles.use_denoising=True;scene.cycles.device='CPU'
scene.render.resolution_x=320;scene.render.resolution_y=640;scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG';scene.render.image_settings.color_mode='RGBA';scene.render.film_transparent=True
scene.view_settings.view_transform='AgX'
scene.world=bpy.data.worlds.new('WaterIcon_Studio');scene.world.use_nodes=True
background=next(n for n in scene.world.node_tree.nodes if n.type=='BACKGROUND')
background.inputs['Color'].default_value=(.76,.83,.78,1)
background.inputs['Strength'].default_value=.55
def aim(obj,target):obj.rotation_euler=(Vector(target)-obj.location).to_track_quat('-Z','Y').to_euler()
def light(name,loc,power,size,color):
    data=bpy.data.lights.new(name,'AREA');data.energy=power;data.shape='RECTANGLE';data.size=size;data.size_y=.32;data.color=color
    obj=bpy.data.objects.new(name,data);scene.collection.objects.link(obj);obj.location=loc;aim(obj,(0,0,.11))
light('Key',(-.22,-.30,.29),18,.14,(.92,1,.95))
light('Rim',(.20,.08,.23),20,.035,(.68,.88,1))
light('Softbox',(.12,-.28,.12),4,.10,(1,.94,.82))
camera=bpy.data.objects.new('InventoryIconCamera',bpy.data.cameras.new('InventoryIconCamera'));scene.collection.objects.link(camera)
camera.location=(.055,-.42,.19);camera.data.type='ORTHO';camera.data.ortho_scale=.253;aim(camera,(0,0,.108));scene.camera=camera
for obj in parts:obj.hide_render=True
for obj,state in ((full,'full'),(halfclosed,'half')):
    obj.hide_render=False;scene.render.filepath=str(ICON/('mineral_water_'+state+'.png'))
    bpy.ops.render.render(write_still=True)
    receipt['icons'].append(scene.render.filepath);obj.hide_render=True
for obj in parts:obj.hide_render=False
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'MineralWater_Authored.blend'))
(OUT/'manifest.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
print('MINERAL_WATER_SOURCE_SAVED '+str(len(parts)))
