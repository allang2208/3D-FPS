"""Requested concept board and editable visual blockout; no game export or integration."""
from pathlib import Path
import bpy, math, json
from mathutils import Vector, Euler

P=Path(__file__).parent
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.context.preferences.filepaths.save_version=0
scene=bpy.context.scene
font=bpy.data.fonts.load('C:/Windows/Fonts/msyh.ttc')
parts=[]

def mat(name,color,metal=0,rough=.4,flat=False):
    m=bpy.data.materials.new(name);m.diffuse_color=(*color,1);m.use_nodes=True
    n=m.node_tree.nodes;bs=n.get('Principled BSDF')
    bs.inputs['Base Color'].default_value=(*color,1)
    bs.inputs['Metallic'].default_value=metal;bs.inputs['Roughness'].default_value=rough
    if flat:
        n.remove(bs);emission=n.new('ShaderNodeEmission');emission.inputs[0].default_value=(*color,1)
        m.node_tree.links.new(emission.outputs[0],n.get('Material Output').inputs['Surface'])
    return m
silver=mat('Satin silver steel',(.40,.46,.48),.85,.30)
dark=mat('Dark inner steel',(.037,.050,.056),.7,.38)
brass=mat('Aged brass',(.40,.25,.095),.8,.34)
walnut=mat('Walnut saddle inlay',(.14,.048,.022),0,.47)
engraving=mat('Dark engraved marks',(.018,.022,.021),0,.7)
ink=mat('Board ink',(.045,.056,.060),0,.8,True)
muted=mat('Board secondary ink',(.085,.105,.11),0,.8,True)
line_mat=mat('Board rules',(.44,.46,.44),0,.8,True)
glass=bpy.data.materials.new('Clear cool optical glass');glass.use_nodes=True
n=glass.node_tree.nodes;n.clear();out=n.new('ShaderNodeOutputMaterial')
t=n.new('ShaderNodeBsdfTransparent');t.inputs[0].default_value=(.92,.97,1,1)
b=n.new('ShaderNodeBsdfPrincipled');b.inputs['Base Color'].default_value=(.18,.34,.40,1)
b.inputs['Roughness'].default_value=.16;b.inputs['Metallic'].default_value=.2
mix=n.new('ShaderNodeMixShader');mix.inputs[0].default_value=.065
glass.node_tree.links.new(t.outputs[0],mix.inputs[1]);glass.node_tree.links.new(b.outputs[0],mix.inputs[2]);glass.node_tree.links.new(mix.outputs[0],out.inputs['Surface'])
glass.surface_render_method='DITHERED'

def finish(obj,name,material,record=True,bevel=0):
    obj.name=name;obj.data.materials.append(material)
    if bevel:
        mod=obj.modifiers.new('Soft machined edge','BEVEL');mod.width=bevel;mod.segments=3
        obj.modifiers.new('Weighted normals','WEIGHTED_NORMAL')
    if record:parts.append(obj)
    return obj

def ring(name,outer,inner,y,depth,material):
    verts=[];faces=[];count=128
    for yy,rad in [(y-depth/2,outer),(y+depth/2,outer),(y-depth/2,inner),(y+depth/2,inner)]:
        verts.extend((rad*math.cos(i*2*math.pi/count),yy,rad*math.sin(i*2*math.pi/count)) for i in range(count))
    for i in range(count):
        j=(i+1)%count
        faces.extend([(i,j,count+j,count+i),(2*count+j,2*count+i,3*count+i,3*count+j),
                      (j,i,2*count+i,2*count+j),(count+i,count+j,3*count+j,3*count+i)])
    me=bpy.data.meshes.new(name);me.from_pydata(verts,[],faces);me.update()
    obj=bpy.data.objects.new(name,me);scene.collection.objects.link(obj)
    for face in me.polygons:face.use_smooth=True
    return finish(obj,name,material,bevel=.012)

def cube(name,loc,scale,material,bevel=.035,record=True):
    bpy.ops.mesh.primitive_cube_add(size=1,location=loc);obj=bpy.context.object
    obj.scale=scale;bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    return finish(obj,name,material,record,bevel)

def rod(name,a,b,r,material,record=True):
    a=Vector(a);b=Vector(b);d=b-a
    bpy.ops.mesh.primitive_cylinder_add(vertices=32,radius=r,depth=d.length,location=(a+b)/2)
    obj=bpy.context.object;obj.rotation_mode='QUATERNION';obj.rotation_quaternion=Vector((0,0,1)).rotation_difference(d.normalized())
    for f in obj.data.polygons:f.use_smooth=True
    return finish(obj,name,material,record,bevel=min(.012,r*.2))

def text(body,loc,size,material=ink,record=False,align='LEFT'):
    d=bpy.data.curves.new('Label '+body,'FONT');d.body=body;d.font=font;d.size=size;d.align_x=align;d.extrude=0
    o=bpy.data.objects.new('Label '+body,d);scene.collection.objects.link(o);o.location=loc;o.rotation_euler=(math.pi/2,0,0)
    return finish(o,o.name,material,record)

ring('Short optical housing',1.26,1.12,0,.74,dark)
ring('Thin front silver lip',1.28,1.14,-.44,.10,silver)
ring('Rear silver lip',1.26,1.12,.44,.09,silver)
ring('Calibrated magnification collar',1.40,1.23,-.24,.22,brass)
ring('Rear focusing ring',1.33,1.23,.30,.16,brass)
for i in range(80):
    angle=i*2*math.pi/80;x=1.405*math.cos(angle);z=1.405*math.sin(angle)
    rod('Magnification grip rib',(x,-.32,z),(x,-.15,z),.012,brass)
for i in range(64):
    angle=i*2*math.pi/64;x=1.334*math.cos(angle);z=1.334*math.sin(angle)
    rod('Focus grip rib',(x,.235,z),(x,.365,z),.010,brass)
for i in range(29):
    angle=math.radians(26+i*4.5);r1=1.35;r0=1.30 if i%7==0 else 1.325
    rod('Scale tick',(r0*math.cos(angle),-.365,r0*math.sin(angle)),(r1*math.cos(angle),-.365,r1*math.sin(angle)),.006,engraving)
for num,deg in zip(['3','4','5','6'],[35,72,109,146]):
    a=math.radians(deg)
    text(num,(1.35*math.cos(a),-.505,1.35*math.sin(a)-.045),.14,engraving,True,'CENTER')
cube('Fixed collar index',(0,-.39,1.405),(.045,.035,.13),silver,.008)

# The side knob and top knob stay outside the clear circular aperture.
rod('Lateral adjustment spindle',(1.22,.04,0),(1.62,.04,0),.12,dark)
rod('Lateral adjustment wheel',(1.56,.04,0),(1.75,.04,0),.29,brass)
for i in range(24):
    a=2*math.pi*i/24;y=.04+.292*math.cos(a);z=.292*math.sin(a)
    rod('Side wheel grip',(1.56,y,z),(1.75,y,z),.012,brass)
rod('Top knob stem',(.0,.06,1.23),(.0,.06,1.50),.10,dark)
rod('Top adjustment knob',(.0,.06,1.47),(.0,.06,1.60),.22,silver)

rod('Mount lower junction',(-.82,.1,-1.01),(-1.27,.1,-1.50),.095,silver)
rod('Offset support',(-1.27,.1,-1.50),(-1.85,.1,-1.50),.095,silver)
cube('Curved seat block',(-1.92,.14,-1.57),(.30,.39,1.00),silver,.12)
cube('Walnut seat inlay',(-1.92,-.069,-1.57),(.205,.035,.64),walnut,.045)
for z in [-1.96,-1.17]:
    rod('Seat screw',(-1.92,-.09,z),(-1.92,-.12,z),.055,brass)
    rod('Screw slit',(-1.96,-.126,z),(-1.88,-.126,z),.006,engraving)

# Glass and a very fine etched reticle remain independent objects.
rod('Clear circular lens',(0,-.32,0),(0,-.30,0),1.115,glass)
for a,b in [((-1.10,-.345,0),(-.075,-.345,0)),((.075,-.345,0),(1.10,-.345,0)),
            ((0,-.345,.075),(0,-.345,1.10)),((0,-.345,-.075),(0,-.345,-1.10))]:
    rod('Fine etched crosshair',a,b,.005,engraving)
rod('Reticle centre dot',(0,-.350,0),(0,-.355,0),.015,engraving)
for z,w in [(-.26,.06),(-.49,.085),(-.72,.11)]:
    rod('Reticle reference tick',(-w,-.345,z),(w,-.345,z),.004,engraving)

# One editable source, instanced as consistent concept views.
def view(name,location,scale,rotation,subset=None):
    root=bpy.data.objects.new(name,None);scene.collection.objects.link(root)
    root.location=location;root.scale=(scale,)*3;root.rotation_euler=Euler(rotation)
    for src in subset or parts:
        o=src.copy();scene.collection.objects.link(o);o.parent=root
    return root
view('Hero perspective',(-4.45,0,.4),1.40,(math.radians(8),math.radians(-12),math.radians(-27)))
view('Front view',(1.5,0,2.0),.76,(0,0,0))
view('Side view',(5.05,0,2.0),.76,(0,0,math.pi/2))
view('Rear view',(1.5,0,-1.43),.76,(0,0,math.pi))
detail=[o for o in parts if any(w in o.name for w in ['collar','Scale','Label','lip','lens','reticle','crosshair','Reticle'])]
view('Lens and calibration detail',(5.05,0,-1.5),.87,(math.radians(5),0,math.radians(-18)),detail)
for o in parts:bpy.data.objects.remove(o,do_unlink=True)

text('观峰变倍镜',(-7.65,-3,4.65),.59)
text('高地长弓专属  /  3–6×  /  特殊改造',(-7.62,-3,4.12),.23,muted)
rod('Top divider',(-7.65,-2.8,3.86),(7.65,-2.8,3.86),.007,line_mat,False)
text('正面',(1.35,-3,3.32),.23,muted,align='CENTER')
text('侧面',(5.0,-3,3.32),.23,muted,align='CENTER')
text('背面',(1.35,-3,-.04),.23,muted,align='CENTER')
text('镜片与刻度细节',(5.0,-3,-.04),.23,muted,align='CENTER')
text('薄圆镜框  ·  望远镜式调节组件',(-7.60,-3,-3.67),.26)
text('黄铜倍率刻度环 / 侧面微调旋钮 / 偏置钢制安装座',(-7.60,-3,-4.10),.205,muted)
rod('Bottom divider',(-7.65,-2.8,-4.44),(7.65,-2.8,-4.44),.007,line_mat,False)
text('结构草模设计  ·  胡桃木 / 亚光银钢 / 旧黄铜',(-7.60,-3,-4.83),.20,muted)
text('CONCEPT 01',(7.60,-3,-4.83),.20,muted,align='RIGHT')

# Neutral concept-board lighting. This render is the requested deliverable.
bg=mat('Warm neutral background',(.71,.71,.68),0,.9)
cube('Board background',(0,3,0),(40,.1,25),bg,0,False)
scene.world=bpy.data.worlds.new('Studio world');scene.world.use_nodes=True
scene.world.node_tree.nodes['Background'].inputs[0].default_value=(.65,.69,.72,1)
scene.world.node_tree.nodes['Background'].inputs[1].default_value=.5
for name,loc,power,size in [('Key',(-6,-8,9),1500,8),('Fill',(7,-5,4),1000,7),('Rim',(-1,2,8),1400,6)]:
    data=bpy.data.lights.new(name,'AREA');data.energy=power;data.shape='DISK';data.size=size
    obj=bpy.data.objects.new(name,data);scene.collection.objects.link(obj);obj.location=loc
    obj.rotation_euler=(-obj.location).to_track_quat('-Z','Y').to_euler()
data=bpy.data.cameras.new('Design board camera');cam=bpy.data.objects.new('Design board camera',data)
scene.collection.objects.link(cam);cam.location=(0,-24,0);cam.rotation_euler=(Vector((0,0,0))-cam.location).to_track_quat('-Z','Y').to_euler()
data.type='ORTHO';data.ortho_scale=16.8;scene.camera=cam
scene.render.engine='CYCLES';scene.cycles.samples=48;scene.cycles.use_denoising=True
scene.render.resolution_x=2304;scene.render.resolution_y=1536;scene.render.resolution_percentage=100
scene.view_settings.view_transform='AgX';scene.render.image_settings.file_format='PNG';scene.render.image_settings.color_mode='RGBA'
scene.render.filepath=str(P/'Highland_Scope3to6_Concept_v1.png')
bpy.ops.wm.save_as_mainfile(filepath=str(P/'Highland_Scope3to6_Concept_v1.blend'))
bpy.ops.render.render(write_still=True)
(P/'design.json').write_text(json.dumps({
    'name':'观峰变倍镜','name_status':'暂定','weapon':'bow_woodsteel','slot':'sight','tier':'Special',
    'magnification_min':3,'magnification_max':6,'stage':'concept_only','user_approved':False,
    'runtime_integrated':False,'balance_values':None,
    'concept_image':'Highland_Scope3to6_Concept_v1.png','editable_source':'Highland_Scope3to6_Concept_v1.blend',
    'generation':'Blender native concept blockout and requested render',
    'imagegen_attempt':{'status':'rejected','category':'violence','request_id':'619bed79-613f-4677-a444-e49d99765504','prompt':'imagegen-prompt.txt'},
    'features':['圆形清透镜片','3–6 倍倍率刻度环','望远镜式调节环与微调旋钮','细刻线准星','偏置钢制安装座'],
    'mounting':'Conceptual saddle follows existing upper socket arrangement; exact dimensions reserved for production modeling.',
    'gameplay_tested':False},ensure_ascii=False,indent=2),encoding='utf-8')
print('SCOPE_CONCEPT_SAVED',flush=True)
