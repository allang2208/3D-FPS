"""Preview of the dual idle candidate from the game eye: V9 bare arms, actual M1911 Contact gun, accepted kukri.

Background Blender only; fixed eye at the origin with the gameplay vertical FOV. Not a game screenshot.
Outputs idle<tag>.png, idle<tag>-grip.png (eye, narrow FOV on the fist), idle<tag>-detail.png and
DualPistolKukri_IdleCandidate<tag>.blend. `-- --ads` renders the ADS candidate (tag _ads).
"""
import bpy, json, math, sys
from pathlib import Path
import numpy as np
from mathutils import Matrix, Vector

P=Path(__file__).resolve().parent;ROOT=P.parents[1]
V4=ROOT/'SourceAssets/PistolBookPoseV4_20261020'
ARGS=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []
TAG='_ads' if '--ads' in ARGS else ''
data=json.loads((P/('candidate'+TAG+'.json')).read_text(encoding='utf-8'))
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.context.preferences.filepaths.save_version=0
scene=bpy.context.scene
S=np.array([1,-1,1])

def smooth_normals(mesh,x,t):
    # Average coincident split-vertex normals so UV/material seams do not facet.
    _,weld=np.unique(np.round(x,7),axis=0,return_inverse=True)
    f=np.cross(x[t[:,1]]-x[t[:,0]],x[t[:,2]]-x[t[:,0]])
    normals=np.zeros((weld.max()+1,3))
    for k in range(3):np.add.at(normals,weld[t[:,k]],f)
    normals/=np.maximum(np.linalg.norm(normals,axis=1,keepdims=True),1.e-10)
    mesh.normals_split_custom_set(normals[weld[t]].reshape(-1,3).tolist())

def make_mesh(name,x,t,uv,uv_name):
    mesh=bpy.data.meshes.new(name);mesh.from_pydata(x.tolist(),[],t.tolist());mesh.update()
    obj=bpy.data.objects.new(name,mesh);scene.collection.objects.link(obj)
    for poly in mesh.polygons:poly.use_smooth=True
    smooth_normals(mesh,x,t)
    lay=mesh.uv_layers.new(name=uv_name);lay.data.foreach_set('uv',uv.reshape(-1))
    return obj,mesh

# V9 bare skin, as in the V4 preview.
skin=bpy.data.materials.new('V9 natural bare skin');skin.use_nodes=True
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

arms=np.load(P/('arms_camera'+TAG+'.npz'))
uv=arms['UV'][:,::-1].copy();uv[:,:,1]=1-uv[:,:,1]
arm_obj,arm_mesh=make_mesh('V9_bare_arms_dual_idle',arms['X']*S*.01,arms['T'][:,::-1],uv,'V9 UV')
arm_mesh.materials.append(skin)

gun_source=json.loads((V4/'contact_source.json').read_text())
with bpy.data.libraries.load(gun_source['source'],link=False) as (available,loaded):
    loaded.materials=gun_source['gun_materials']
g=np.load(P/('gun_camera'+TAG+'.npz'))
# gun_camera.npz keeps the V4 reversed winding; reverse again as the V4 preview did.
gun_obj,gun_mesh=make_mesh('M1911_contact_geometry',g['X']*S*.01,g['T'][:,::-1],g['UV'][:,::-1],'Original gun UV')
for mat in loaded.materials:gun_mesh.materials.append(mat)
for p,s in zip(gun_mesh.polygons,g['slots']):p.material_index=int(s)

# The game's reworked kukri textures (M_Kukri inputs); the editable blend's Fab PBR paths are not on this machine.
steel=bpy.data.materials.new('M_Kukri preview');steel.use_nodes=True
kt=steel.node_tree;kb=kt.nodes.get('Principled BSDF');ktex=ROOT/'SourceAssets/Kukri20261020/Textures'
def kimage(name,space):
    n=kt.nodes.new('ShaderNodeTexImage');n.image=bpy.data.images.load(str(ktex/name),check_existing=True)
    n.image.colorspace_settings.name=space;return n
kc=kimage('T_Kukri_BaseColor.png','sRGB');kn=kimage('T_Kukri_Normal.png','Non-Color');ko=kimage('T_Kukri_ORM.png','Non-Color')
knm=kt.nodes.new('ShaderNodeNormalMap');knm.uv_map='UVMap';ksep=kt.nodes.new('ShaderNodeSeparateColor')
kt.links.new(kc.outputs['Color'],kb.inputs['Base Color']);kt.links.new(kn.outputs['Color'],knm.inputs['Color']);kt.links.new(knm.outputs['Normal'],kb.inputs['Normal'])
kt.links.new(ko.outputs['Color'],ksep.inputs['Color']);kt.links.new(ksep.outputs['Green'],kb.inputs['Roughness']);kt.links.new(ksep.outputs['Blue'],kb.inputs['Metallic'])
k=np.load(P/('kukri_camera'+TAG+'.npz'))
# kukri_mesh.npz kept the Blender winding; the UE Y mirror is undone with S, which restores it.
k_obj,k_mesh=make_mesh('SM_Kukri_reverse_grip',k['X']*S*.01,k['T'],k['UV'],'UVMap')
k_mesh.materials.append(steel)

# Native bone frames as editable guides.
for side in ('left','right'):
    collection=bpy.data.collections.new(side+' pose guides');scene.collection.children.link(collection)
    for n in ('clavicle','upperarm','lowerarm','hand'):
        m=np.array(data['poses'][side][n+'_'+side[0]])
        guide=bpy.data.objects.new(side+'_'+n,None);collection.objects.link(guide)
        guide.empty_display_type='ARROWS';guide.empty_display_size=.025
        xf=Matrix((np.diag(S)@m[:3,:3]@np.diag(S)).tolist()).to_4x4();xf.translation=Vector((m[:3,3]*S*.01).tolist())
        guide.matrix_world=xf

scene.render.engine='CYCLES';scene.cycles.samples=48;scene.cycles.use_denoising=True
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
    obj.rotation_euler=(Vector((.30,-.08,-.10))-obj.location).to_track_quat('-Z','Y').to_euler()
camera=bpy.data.cameras.new('Player eye - no camera displacement');cam=bpy.data.objects.new(camera.name,camera);scene.collection.objects.link(cam)
scene.camera=cam;camera.sensor_fit='VERTICAL';camera.sensor_height=24;camera.clip_start=.01;camera.clip_end=100
cam.rotation_euler=Matrix(((0,0,-1),(-1,0,0),(0,1,0))).to_euler()
camera.lens=24/(2*math.tan(math.radians(data['controls']['vertical_fov']/2)))
scene.render.filepath=str(P/('idle'+TAG+'.png'));bpy.ops.render.render(write_still=True);print('SAVED idle',flush=True)
# Same eye, narrow lens aimed at the fist: the handle / finger contact at readable size.
fist=Vector((np.array(data['controls']['kukri']['fist_centre'])*S*.01).tolist())
grip=bpy.data.cameras.new('Eye close-up on the left fist');gc=bpy.data.objects.new(grip.name,grip);scene.collection.objects.link(gc)
grip.sensor_fit='VERTICAL';grip.sensor_height=24;grip.lens=24/(2*math.tan(math.radians(16/2)));grip.clip_start=.01
gc.location=(0,0,0);gc.rotation_euler=fist.to_track_quat('-Z','Z').to_euler()
scene.camera=gc;scene.render.filepath=str(P/('idle'+TAG+'-grip.png'));bpy.ops.render.render(write_still=True);print('SAVED grip',flush=True)
# From below the fist, looking up into the palm side.
under=bpy.data.cameras.new('Palm side of the left fist');uc=bpy.data.objects.new(under.name,under);scene.collection.objects.link(uc)
under.lens=60;under.clip_start=.01;uc.location=fist+Vector((-.02,-.10,-.16))
uc.rotation_euler=(fist-uc.location).to_track_quat('-Z','Z').to_euler()
scene.camera=uc;scene.render.filepath=str(P/('idle'+TAG+'-palm.png'));bpy.ops.render.render(write_still=True);print('SAVED palm',flush=True)
scene.camera=cam
# Oblique look at the crossed wrists and the reversed kukri; explicitly not the player view.
detail=bpy.data.cameras.new('Oblique crossed-wrist detail');dc=bpy.data.objects.new(detail.name,detail);scene.collection.objects.link(dc)
detail.lens=40;detail.clip_start=.01;dc.location=(.05,.45,.05)
dc.rotation_euler=(Vector((.30,-.10,-.10))-dc.location).to_track_quat('-Z','Y').to_euler()
scene.camera=dc;scene.render.filepath=str(P/('idle'+TAG+'-detail.png'));bpy.ops.render.render(write_still=True);print('SAVED detail',flush=True)
scene.camera=cam
scene['status']='Dual pistol + kukri '+('ADS' if TAG else 'idle')+' static authoring candidate; not a game screenshot; not installed'
scene['pose_source']='pose_controls.json, fit_idle.py and author_idle.py'
# Textures stay external: the kukri set derives from a Fab asset without redistribution review.
bpy.ops.wm.save_as_mainfile(filepath=str(P/('DualPistolKukri_IdleCandidate'+TAG+'.blend')))
print('CANDIDATE_SAVED',flush=True)
