"""Requested two-pose preview using actual native V9 arms, M1911 and spellbook.

Background Blender only. First-person images use a fixed eye and the gameplay
vertical FOVs. Shape keys are static pose snapshots, not finished transitions.
"""
import bpy, json, math
from pathlib import Path
import numpy as np
from mathutils import Matrix, Vector

P=Path(__file__).resolve().parent;ROOT=P.parents[1]
data=json.loads((P/'candidate.json').read_text())
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.context.preferences.filepaths.save_version=0
scene=bpy.context.scene
def material(name,color,metal=0,rough=.45):
    mat=bpy.data.materials.new(name);mat.use_nodes=True
    bs=mat.node_tree.nodes.get('Principled BSDF')
    bs.inputs['Base Color'].default_value=(*color,1)
    bs.inputs['Metallic'].default_value=metal;bs.inputs['Roughness'].default_value=rough
    return mat
skin=material('V9 natural bare skin',(.48,.28,.18))
nt=skin.node_tree;bs=nt.nodes.get('Principled BSDF')
tex=ROOT/'SourceAssets/BareSkinV9M4_20261017/Work'
def image(name,space):
    n=nt.nodes.new('ShaderNodeTexImage');n.image=bpy.data.images.load(str(tex/name),check_existing=True)
    n.image.colorspace_settings.name=space;return n
colour=image('T_M4SkinV9_Colour.png','sRGB');normal=image('normal_gl16.png','Non-Color');masks=image('T_M4SkinV9_Masks.png','Non-Color')
nm=nt.nodes.new('ShaderNodeNormalMap');nm.uv_map='V9 UV';nm.inputs['Strength'].default_value=.8
sep=nt.nodes.new('ShaderNodeSeparateColor')
nt.links.new(colour.outputs['Color'],bs.inputs['Base Color']);nt.links.new(normal.outputs['Color'],nm.inputs['Color']);nt.links.new(nm.outputs['Normal'],bs.inputs['Normal'])
nt.links.new(masks.outputs['Color'],sep.inputs['Color']);nt.links.new(sep.outputs['Green'],bs.inputs['Roughness'])
bs.inputs['Subsurface Weight'].default_value=.16;bs.inputs['Subsurface Scale'].default_value=.005
bs.inputs['Subsurface Radius'].default_value=(1,.4,.2)
steel=material('M1911 steel preview',(.12,.145,.17),.8,.28)
coating=material('M1911 slide coating preview',(.035,.042,.05),.7,.36)
wood=material('M1911 grip panels preview',(.12,.045,.018),.0,.4)
dark=material('M1911 rear sight preview',(.009,.012,.016),.2,.5)
brass=material('M1911 cartridge brass preview',(.38,.23,.075),.8,.25)
S=np.array([1,-1,1])
def make_arm(side):
    hip=np.load(P/f'hip_{side}.npz');aim=np.load(P/f'aim_{side}.npz')
    t=hip['T'][:,::-1];x=hip['X']*S*.01
    mesh=bpy.data.meshes.new(side+'_native_V9');mesh.from_pydata(x.tolist(),[],t.tolist());mesh.update()
    obj=bpy.data.objects.new(side+'_native_V9',mesh);scene.collection.objects.link(obj)
    for mat in [skin,steel,coating,wood,dark,brass]:mesh.materials.append(mat)
    skin_slots=set(hip['skin_slots'].tolist())
    for poly,slot in zip(mesh.polygons,hip['slots']):
        poly.use_smooth=True
        poly.material_index=0 if int(slot) in skin_slots else {0:5,1:2,2:2,3:3,4:1,5:1,6:4}.get(int(slot),1)
    # Average coincident split-vertex normals, retaining the native surface.
    # Material/UV seams otherwise create false facets in Blender.
    _,weld=np.unique(np.round(x,7),axis=0,return_inverse=True)
    f=np.cross(x[t[:,1]]-x[t[:,0]],x[t[:,2]]-x[t[:,0]])
    normals=np.zeros((weld.max()+1,3))
    for k in range(3):np.add.at(normals,weld[t[:,k]],f)
    normals/=np.maximum(np.linalg.norm(normals,axis=1,keepdims=True),1.e-10)
    mesh.normals_split_custom_set(normals[weld[t]].reshape(-1,3).tolist())
    uv=hip['UV'][:,::-1].copy();uv[:,:,1]=1-uv[:,:,1]
    lay=mesh.uv_layers.new(name='V9 UV');lay.data.foreach_set('uv',uv.reshape(-1))
    obj.shape_key_add(name='Hip low book')
    key=obj.shape_key_add(name='Aim forearm shelf');key.data.foreach_set('co',(aim['X']*S*.01).reshape(-1))
    for f,v in [(1,0),(2,1)]:key.value=v;key.keyframe_insert('value',frame=f)
    return obj
arms=[make_arm(side) for side in ('left','right')]
gun_source=json.loads((P/'contact_source.json').read_text())
with bpy.data.libraries.load(gun_source['source'],link=False) as (available,loaded):
    loaded.materials=gun_source['gun_materials']
g0=np.load(P/'gun_camera_idle.npz');g1=np.load(P/'gun_camera_aim.npz')
gm=bpy.data.meshes.new('Actual M1911 contact geometry');gm.from_pydata((g0['X']*S*.01).tolist(),[],g0['T'][:,::-1].tolist());gm.update()
gun=bpy.data.objects.new(gm.name,gm);scene.collection.objects.link(gun)
for mat in loaded.materials:gm.materials.append(mat)
for p,s in zip(gm.polygons,g0['slots']):p.material_index=int(s);p.use_smooth=True
guv=gm.uv_layers.new(name='Original gun UV');guv.data.foreach_set('uv',g0['UV'][:,::-1].reshape(-1))
gun.shape_key_add(name='Hip');gkey=gun.shape_key_add(name='Aim')
gkey.data.foreach_set('co',(g1['X']*S*.01).reshape(-1))
for f,v in [(1,0),(2,1)]:gkey.value=v;gkey.keyframe_insert('value',frame=f)

with bpy.data.libraries.load(str(ROOT/'SourceAssets/SpellbookEvildeer20261009/Spellbook_Alchemy.blend'),link=False) as (available,loaded):
    loaded.objects=['SM_Spellbook_Alchemy_Closed']
book=loaded.objects[0];scene.collection.objects.link(book)
book.parent=None;book.animation_data_clear();book.constraints.clear()
book.hide_render=False;book.hide_viewport=False;book.hide_set(False)
for f,label in [(1,'hip'),(2,'aim')]:
    m=np.array(data['book_frames'][label]);r=np.diag(S)@m[:3,:3]@np.diag(S)
    xf=Matrix(r).to_4x4();xf.translation=Vector(m[:3,3]*S*.01)
    book.matrix_world=xf@Matrix.Diagonal((.01,.01,.01,1));book.rotation_mode='QUATERNION'
    for prop in ('location','rotation_quaternion','scale'):book.keyframe_insert(prop,frame=f)

# Keep complete native bone frames as editable guides for the two authored keys.
for side in ('left','right'):
    collection=bpy.data.collections.new(side+' pose guides');scene.collection.children.link(collection)
    for n in ('clavicle','upperarm','lowerarm','hand'):
        guide=bpy.data.objects.new(side+'_'+n,None);collection.objects.link(guide)
        guide.empty_display_type='ARROWS';guide.empty_display_size=.025
        for f,label in [(1,'hip'),(2,'aim')]:
            m=np.array(data['poses'][label][side][n+'_'+side[0]])
            xf=Matrix(np.diag(S)@m[:3,:3]@np.diag(S)).to_4x4();xf.translation=Vector(m[:3,3]*S*.01)
            guide.matrix_world=xf;guide.rotation_mode='QUATERNION'
            for prop in ('location','rotation_quaternion'):guide.keyframe_insert(prop,frame=f)

scene.frame_start=1;scene.frame_end=2;scene.timeline_markers.new('HIP - low left book',frame=1);scene.timeline_markers.new('AIM - separated forearms',frame=2)
scene.render.engine='CYCLES';scene.cycles.samples=32;scene.cycles.use_denoising=True
scene.cycles.device='GPU'
prefs=bpy.context.preferences.addons['cycles'].preferences
try:
    prefs.compute_device_type='OPTIX';prefs.get_devices()
    for d in prefs.devices:d.use=d.type!='CPU'
    if not any(d.use for d in prefs.devices):scene.cycles.device='CPU'
except Exception:scene.cycles.device='CPU'
scene.render.resolution_x=1280;scene.render.resolution_y=720;scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG';scene.view_settings.view_transform='AgX'
world=bpy.data.worlds.new('Neutral charcoal studio');world.use_nodes=True;scene.world=world
world.node_tree.nodes['Background'].inputs['Color'].default_value=(.075,.085,.1,1)
world.node_tree.nodes['Background'].inputs['Strength'].default_value=.45
for name,loc,power,size in [('Key',(-.15,-.45,.65),22,.75),('Fill',(.15,.65,.3),12,.6),('Rim',(.85,-.08,.35),18,.5)]:
    light=bpy.data.lights.new(name,'AREA');light.energy=power;light.shape='DISK';light.size=size
    obj=bpy.data.objects.new(name,light);scene.collection.objects.link(obj);obj.location=loc
    obj.rotation_euler=(Vector((.34,0,-.14))-obj.location).to_track_quat('-Z','Y').to_euler()
camera=bpy.data.cameras.new('Player eye - no camera displacement');cam=bpy.data.objects.new(camera.name,camera);scene.collection.objects.link(cam)
scene.camera=cam;camera.sensor_fit='VERTICAL';camera.sensor_height=24;camera.clip_start=.01;camera.clip_end=100
cam.rotation_euler=Matrix(((0,0,-1),(-1,0,0),(0,1,0))).to_euler()
for f,label in [(1,'hip'),(2,'aim')]:
    scene.frame_set(f);camera.lens=24/(2*math.tan(math.radians(data['controls'][label]['vertical_fov']/2)))
    camera.keyframe_insert('lens',frame=f)
    scene.render.filepath=str(P/(label+'.png'));bpy.ops.render.render(write_still=True)
    print('SAVED',label,flush=True)
scene.frame_set(2)
# An oblique detail explicitly differs from the fixed-eye first-person images.
detail=bpy.data.cameras.new('Oblique wrist contact detail');dc=bpy.data.objects.new(detail.name,detail);scene.collection.objects.link(dc)
detail.lens=55;detail.clip_start=.01;dc.location=(-.02,-.48,.10)
dc.rotation_euler=(Vector((.36,-.01,-.16))-dc.location).to_track_quat('-Z','Y').to_euler()
scene.camera=dc;scene.render.filepath=str(P/'aim-detail.png');bpy.ops.render.render(write_still=True)
scene.camera=cam;scene.frame_set(1)
scene['status']='V4 static authoring candidate; not a game screenshot; not installed'
scene['pose_source']='pose_controls.json and author_poses.py; shape keys hold two static poses only'
bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(P/'PistolBook_V4_StaticCandidate.blend'))
(P/'preview_receipt.json').write_text(json.dumps({'candidate_only':True,'runtime_integrated':False,'rendered':['hip.png','aim.png','aim-detail.png'],
    'camera':'fixed eye at origin; hip 75 and aim 55 degree vertical FOV; separate oblique detail',
    'surface':'native V9 mesh, UV, skin textures, joint and pose4 shapes; Blender lighting',
    'equipment':'actual M1911 Contact scene mesh/materials and closed spellbook asset',
    'not_included':['runtime transitions','firing','reload','clothing','third-person changes']},indent=2))
print('STATIC_CANDIDATE_SAVED',flush=True)
