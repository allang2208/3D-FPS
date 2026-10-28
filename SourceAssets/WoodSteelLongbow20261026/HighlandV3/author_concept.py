"""Editable appearance blockout and a requested concept plate; no game asset export."""
from pathlib import Path
import bpy,math,json,bmesh
from mathutils import Vector,Matrix
P=Path(__file__).parent;S=P.parent
bpy.ops.wm.open_mainfile(filepath=str(S/'WoodSteelLongbow_Editable.blend'))
bpy.context.preferences.filepaths.save_version=0
scene=bpy.context.scene
keep=['SK_WoodSteelLongbow_Original','SM_WoodSteelLongbow_Grip','SM_WoodSteelLongbow_Rest']
subjects=[bpy.data.objects[n] for n in keep]
for o in list(bpy.data.objects):
    if o not in subjects:bpy.data.objects.remove(o,do_unlink=True)
for o in subjects:
    o.hide_render=False;o.hide_set(False);o.parent=None;o.modifiers.clear();o.matrix_world=Matrix.Identity(4)
for im in bpy.data.images:
    path=S/'Textures'/(im.name.split('.')[0]+'.png')
    if path.exists():im.filepath=str(path);im.reload()
body=subjects[0];body.name='FarPeak_Body_Concept'
def material(name,color,metal=0,rough=.5,emission=False):
    m=bpy.data.materials.new(name);m.use_nodes=True
    n=m.node_tree.nodes;bs=next(x for x in n if x.type=='BSDF_PRINCIPLED')
    if emission:
        n.remove(bs);e=n.new('ShaderNodeEmission');e.inputs['Color'].default_value=(*color,1);e.inputs['Strength'].default_value=1
        m.node_tree.links.new(e.outputs[0],next(x for x in n if x.type=='OUTPUT_MATERIAL').inputs['Surface'])
    else:
        bs.inputs['Base Color'].default_value=(*color,1);bs.inputs['Metallic'].default_value=metal;bs.inputs['Roughness'].default_value=rough
    return m
steel=material('FarPeak_BlackenedSteel',(.15,.19,.21),.85,.32)
bronze=material('FarPeak_RubbedBronze',(.30,.18,.07),.75,.38)
wood=material('FarPeak_LaminateEdge',(.20,.085,.029),0,.65)
string=material('FarPeak_String',(.19,.17,.12),0,.8)
# Broaden the free limbs while leaving the grip/rest interfaces untouched.
bins={}
for v in body.data.vertices:bins.setdefault(round(v.co.z),[]).append(v.co.x)
centers={k:(min(xs)+max(xs))*.5 for k,xs in bins.items()}
for v in body.data.vertices:
    q=max(0,min(1,(abs(v.co.z)-12)/20));q=q*q*(3-2*q)
    v.co.y*=1+.60*q
    v.co.x=centers[round(v.co.z)]+(v.co.x-centers[round(v.co.z)])*(1+.4*q)
def profile(z):
    vs=[v.co for v in body.data.vertices if abs(v.co.z-z)<1.8]
    if not vs:vs=[min(body.data.vertices,key=lambda v:abs(v.co.z-z)).co]
    return (min(v.x for v in vs)+max(v.x for v in vs))*.5,min(v.y for v in vs)-.18
def mesh(name,verts,faces,mat):
    d=bpy.data.meshes.new(name);d.from_pydata(verts,[],faces);d.materials.append(mat);d.update()
    o=bpy.data.objects.new(name,d);scene.collection.objects.link(o);subjects.append(o)
    bevel=o.modifiers.new('Soft forged edges','BEVEL');bevel.width=.075;bevel.segments=2
    o.modifiers.new('Weighted normals','WEIGHTED_NORMAL');return o
def rib(name,z0,z1,offset,width,mat):
    verts=[];n=14
    for i in range(n):
        z=z0+(z1-z0)*i/(n-1);x,y=profile(z)
        taper=.48+.52*max(0.,math.sin(math.pi*i/(n-1)))**.45
        w=width*taper
        verts.extend([(x+offset-w,y,z),(x+offset+w,y,z),(x+offset+w*.85,y-.42,z),(x+offset-w*.85,y-.42,z)])
    faces=[]
    for i in range(n-1):
        for k in range(4):faces.append((i*4+k,i*4+(k+1)%4,(i+1)*4+(k+1)%4,(i+1)*4+k))
    faces.extend([(3,2,1,0),tuple(range((n-1)*4,n*4))]);return mesh(name,verts,faces,mat)
# Three separated sections per limb read as flexible steel backing, with
# warm exposed laminate shoulders instead of a single rigid metal plank.
for sign,segments in [(1,[(15,34),(36,57),(59,78)]),(-1,[(14,31),(33,50),(52,68)])]:
    for j,(a,b) in enumerate(segments):
        for side in (-1,1):rib('SegmentedSteel_%s_%s_%s'%(sign,j,side),sign*a,sign*b,side*.46,.35,steel)
        rib('ExposedWoodSpine_%s_%s'%(sign,j),sign*a,sign*b,0,.17,wood)
        for z in (sign*(a+1),sign*(b-1)):
            x,y=profile(z)
            # Compact bronze edge bindings, decorative and flush to the limb.
            mesh('BronzeCollar',[(x-.9,y-.13,z-.24),(x+.9,y-.13,z-.24),(x+.82,y-.55,z+.24),(x-.82,y-.55,z+.24)],[(0,1,2,3)],bronze)
# A restrained mountain-chevron badge on the upper rigid collar.
for z in (16.5,18.2,19.9):
    x,y=profile(z)
    mesh('MountainChevron',[(x-1.15,y-.65,z-.6),(x,y-.68,z+.25),(x+1.15,y-.65,z-.6),(x+1.15,y-.65,z-.3),(x,y-.68,z+.55),(x-1.15,y-.65,z-.3)],[(0,1,4,5),(1,2,3,4)],bronze)
info=json.loads((S/'authoring.json').read_text())
def point(key):
    x,y,z=info[key];return Vector((x,-y,z))
for key in ('nock_upper_cm','nock_lower_cm'):
    a,b=point(key),point('brace_nock_cm');delta=b-a
    bpy.ops.mesh.primitive_cylinder_add(vertices=12,radius=.1,depth=delta.length,location=(a+b)*.5)
    o=bpy.context.object;o.rotation_mode='QUATERNION';o.rotation_quaternion=Vector((0,0,1)).rotation_difference(delta.normalized());o.data.materials.append(string);subjects.append(o)
# Freeze only this concept's geometric bevels before composing views.
for o in subjects:
    bpy.context.view_layer.objects.active=o
    for m in list(o.modifiers):bpy.ops.object.modifier_apply(modifier=m.name)
    o.data.transform(o.matrix_world);o.matrix_world=Matrix.Identity(4)
    o.data.transform(Matrix.Scale(.01,4))
masters=subjects[:]
master_collection=bpy.data.collections.new('Editable_Concept_Master');scene.collection.children.link(master_collection)
for o in masters:
    for collection in list(o.users_collection):collection.objects.unlink(o)
    master_collection.objects.link(o)
master_collection.hide_render=True

def instance_view(name,x,z,angle,scale=1,crop=None):
    rotation=Matrix.Rotation(angle,4,'Z')
    for base in masters:
        o=base.copy();o.data=base.data.copy();o.name=name+'_'+base.name;scene.collection.objects.link(o)
        if crop:
            bm=bmesh.new();bm.from_mesh(o.data)
            bmesh.ops.delete(bm,geom=[v for v in bm.verts if v.co.z<crop[0] or v.co.z>crop[1]],context='VERTS')
            bm.to_mesh(o.data);bm.free()
        center=(crop[0]+crop[1])*.5 if crop else .052
        o.matrix_world=Matrix.Translation((x,0,z))@rotation@Matrix.Scale(scale,4)@Matrix.Translation((0,0,-center))
instance_view('Front',-1.78,.04,0)
instance_view('Side',-.98,.04,math.pi/2)
instance_view('Back',-.18,.04,math.pi)
instance_view('RootDetail',1.05,.56,-.32,3.4,(.10,.30))
instance_view('TipDetail',1.25,-.37,-.16,2.7,(.69,.96))

font=bpy.data.fonts.load('D:/FPS3D/FPSGAME/Content/UI/GunsmithWorkbench/Fonts/NotoSansSC-Regular.otf')
white=material('Type_Ivory',(.78,.80,.77),emission=True)
muted=material('Type_Muted',(.37,.42,.43),emission=True)
green=material('Type_Positive',(.40,.67,.51),emission=True)
copper=material('Type_Cost',(.76,.43,.30),emission=True)
def text(label,x,z,size=.055,mat=white):
    d=bpy.data.curves.new(label,'FONT');d.body=label;d.font=font;d.size=size*2.4
    o=bpy.data.objects.new(label,d);scene.collection.objects.link(o);o.location=(x,-.8,z);o.rotation_euler=(math.pi/2,0,0);d.materials.append(mat)
text('高地长弓',-2.10,1.20,.17)
text('专属弓体改造 · 远峰重弓体',-2.08,1.08,.065,muted)
text('外观草模 / CONCEPT 01',.88,1.23,.055,muted)
for label,x in [('正视',-1.9),('侧视',-1.10),('背视',-.30)]:text(label,x,-1.0,.058,muted)
text('分段钢背 × 层压木芯',.65,1.01,.060)
text('加厚弓臂 · 深色木纹 · 山脊纹饰',.65,.15,.044,muted)
text('强化叶形弓梢',.65,.045,.060)
text('保留原握持接口与配件接口',.65,-.88,.048,muted)
text('武器被动：有效射程 +50%',-2.08,-1.16,.073)
text('射程 ↑    伤害 ↑    暴击伤害 ↑',-2.08,-1.32,.066,green)
text('拉弓速度 ↓    体力消耗 ↑',.25,-1.32,.066,copper)

background=material('Board',(.018,.024,.028),emission=True)
mesh_bg=bpy.data.meshes.new('Board');mesh_bg.from_pydata([(-3,.8,-2),(3,.8,-2),(3,.8,2),(-3,.8,2)],[],[(0,1,2,3)]);mesh_bg.materials.append(background)
o=bpy.data.objects.new('Board',mesh_bg);scene.collection.objects.link(o)
def line(x0,z0,x1,z1):
    curve=bpy.data.curves.new('Divider','CURVE');curve.dimensions='3D';curve.bevel_depth=.001
    s=curve.splines.new('POLY');s.points.add(1);s.points[0].co=(x0,-.75,z0,1);s.points[1].co=(x1,-.75,z1,1)
    o=bpy.data.objects.new('Divider',curve);scene.collection.objects.link(o);curve.materials.append(muted)
line(-2.1,1.02,.38,1.02);line(.49,1.02,.49,-1.01);line(-2.1,-1.05,2.10,-1.05)
scene.world=bpy.data.worlds.new('ConceptStudio');scene.world.use_nodes=True
world_bg=next(x for x in scene.world.node_tree.nodes if x.type=='BACKGROUND')
world_bg.inputs[0].default_value=(.35,.39,.42,1)
world_bg.inputs[1].default_value=.45
for name,loc,energy,size in [('Key',(-2,-3,3),450,4),('Fill',(3,-2,1),300,3),('Rim',(0,2,2),450,3)]:
    d=bpy.data.lights.new(name,'AREA');d.energy=energy;d.size=size
    o=bpy.data.objects.new(name,d);scene.collection.objects.link(o);o.location=loc;o.rotation_euler=(-o.location).to_track_quat('-Z','Y').to_euler()
camdata=bpy.data.cameras.new('ConceptCamera');camdata.type='ORTHO';camdata.ortho_scale=4.5
cam=bpy.data.objects.new('ConceptCamera',camdata);scene.collection.objects.link(cam);cam.location=(0,-10,0);cam.rotation_euler=(Vector((0,0,0))-cam.location).to_track_quat('-Z','Y').to_euler();scene.camera=cam
scene.render.engine='CYCLES';scene.cycles.samples=48;scene.cycles.use_denoising=True
prefs=bpy.context.preferences.addons['cycles'].preferences
try:
    prefs.compute_device_type='OPTIX';prefs.get_devices()
    for device in prefs.devices:device.use=device.type=='OPTIX'
    if any(d.use for d in prefs.devices):scene.cycles.device='GPU'
except Exception:scene.cycles.device='CPU'
scene.render.resolution_x=1800;scene.render.resolution_y=1200;scene.render.resolution_percentage=100
scene.render.film_transparent=False;scene.render.image_settings.file_format='PNG';scene.render.image_settings.color_mode='RGB'
scene.view_settings.view_transform='AgX';scene.view_settings.look='AgX - Medium High Contrast';scene.view_settings.exposure=.15
scene.render.filepath=str(P/'HighlandLongbow_FarPeak_Concept_v2.png')
bpy.ops.wm.save_as_mainfile(filepath=str(P/'HighlandLongbow_FarPeak_Concept_v2.blend'))
bpy.ops.render.render(write_still=True)
print('HIGHLAND_CONCEPT_RENDERED')
