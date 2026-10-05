"""Create continuous soft-death shapes; preserve source faces, skin and living actions."""
from pathlib import Path
import bpy, json, math
import numpy as np

ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/SpiralPillarM14Meshy20261004')
OUT=ROOT/'ProductionV06'
for folder in ('Authoring','Exports','Records'):(OUT/folder).mkdir(parents=True,exist_ok=True)
source=ROOT/'ProductionV05/Authoring/M14_Rigged_Animated_v05.blend'
bpy.ops.wm.open_mainfile(filepath=str(source))
scene=bpy.context.scene;rig=bpy.data.objects['M14_Rig']
rig.animation_data.action=None
for bone in rig.pose.bones:
    bone.location=(0,0,0);bone.rotation_quaternion=(1,0,0,0);bone.scale=(1,1,1)
scene.frame_set(0)
parts=[ob for ob in scene.objects if ob.type=='MESH']
bpy.ops.object.select_all(action='DESELECT')
for ob in parts:ob.select_set(True)
bpy.context.view_layer.objects.active=next(ob for ob in parts if ob.name=='M14_Body_RootSkirt')
# One export object gives each full-surface morph one stable UE name. Joining
# retains every face, UV corner, material assignment and vertex-group weight.
bpy.ops.object.join()
mesh=bpy.context.object;mesh.name='M14_SoftDeathMesh'
coords=np.empty(len(mesh.data.vertices)*3,dtype=np.float32)
mesh.data.vertices.foreach_get('co',coords);p=coords.reshape(-1,3).astype(np.float64)
x,y,z=p.T
def smooth(value):
    q=np.clip(value,0.,1.);return q*q*(3.-2.*q)

# A continuous spatial field is shared by all tissue/metal partitions and seam
# duplicates. It releases height into a broad, gently curved ground footprint.
final=np.column_stack((x*(1.32+.10*np.sin(z*1.7))+.20*np.sin(z*1.45),
    y*1.20+.65*z+.12*np.sin(z*2.0),
    .014+.080*z+.025*np.sin(z*3.0)**2))

# The mouth retains a thick lip/teeth pocket, turned upward instead of crushed
# flat. Blend spatially across gums and adjoining skin, never by cut object ID.
mouth=np.array(rig.data.bones['maw'].head_local)
mouth_delta=p-mouth
r=np.sqrt((mouth_delta[:,0]/.30)**2+(mouth_delta[:,1]/.22)**2+(mouth_delta[:,2]/.28)**2)
w=1.-smooth((r-.72)/.78)
angle=math.radians(-76);c,s=math.cos(angle),math.sin(angle)
rotation=np.array([[1,0,0],[0,c,-s],[0,s,c]])
mouth_at=np.array([.20*math.sin(mouth[2]*1.45),mouth[1]*1.2+.65*mouth[2]+.12*math.sin(mouth[2]*2),.23])
rigid=mouth_delta@rotation.T+mouth_at
final=final*(1-w[:,None])+rigid*w[:,None]

# Retain the restraint's thickness. The adjacent body folds around its low
# landing position; no different displacement is applied at duplicated seams.
band=np.array([0.,0.,2.03]);delta=p-band
r=np.sqrt((delta[:,0]/.42)**2+(delta[:,1]/.37)**2+(delta[:,2]/.15)**2)
w=1.-smooth((r-.88)/.72)
band_at=np.array([.20*math.sin(band[2]*1.45),.65*band[2]+.12*math.sin(band[2]*2),.18])
final=final*(1-w[:,None])+(delta+band_at)*w[:,None]
for side in ('L','R'):
    sac=np.array(rig.data.bones['sac_'+side].head_local);sac[2]-=.18
    d=p-sac
    pocket=np.exp(-((d[:,0]/.23)**2+(d[:,1]/.21)**2+(d[:,2]/.30)**2)*2.0)
    final[:,2]+=.11*pocket
final[:,2]=np.maximum(.012,final[:,2])

mesh.shape_key_add(name='Basis',from_mix=False)
times=[.75,1.60,2.70]
names=['M14_DeathSag','M14_DeathFold','M14_DeathSpread']
for number,(name,time) in enumerate(zip(names,times)):
    # Lower tissue loses support first. The top and the two sacs arrive with
    # a small delay; the three shape samples are blended by the same death clock.
    delay=.07+.16*np.clip(z,0,3)+.08*smooth(x+.5)
    phase=smooth((time-delay)/(1.55+.12*np.clip(z,0,3)))
    if number==2:phase=np.ones_like(z)
    target=p+(final-p)*phase[:,None]
    if number<2:
        sway=np.sin(np.pi*phase)*.13
        target[:,0]+=sway*np.sin(z*1.8)
        target[:,1]-=sway*.35
    key=mesh.shape_key_add(name=name,from_mix=False)
    key.data.foreach_set('co',target.astype(np.float32).ravel())
    key.value=0.

# Author exact weights in the .blend too, for editable DCC playback. Runtime
# holds the terminal weights on the mesh so corpse pose snapshots retain them.
for frame in range(109):
    t=frame/30.;weights=[0.,0.,0.]
    if t<=times[0]:weights[0]=float(smooth(t/times[0]))
    elif t<=times[1]:
        a=float(smooth((t-times[0])/(times[1]-times[0])));weights=[1-a,a,0.]
    elif t<=times[2]:
        a=float(smooth((t-times[1])/(times[2]-times[1])));weights=[0.,1-a,a]
    else:weights[2]=1.
    for name,weight in zip(names,weights):
        key=mesh.data.shape_keys.key_blocks[name];key.value=weight;key.keyframe_insert('value',frame=frame)

action=bpy.data.actions.new('A_M14_Death_v06');action.use_fake_user=True
rig.animation_data.action=action
scene.render.fps=30;scene.frame_start=0;scene.frame_end=108
for frame in (0,108):
    for bone in rig.pose.bones:
        bone.keyframe_insert('location',frame=frame,group=bone.name)
        bone.keyframe_insert('rotation_quaternion',frame=frame,group=bone.name)
        bone.keyframe_insert('scale',frame=frame,group=bone.name)
scene.frame_set(0)
settings=dict(use_selection=True,apply_unit_scale=True,apply_scale_options='FBX_SCALE_UNITS',
    axis_forward='-Z',axis_up='Y',add_leaf_bones=False,use_armature_deform_only=True,
    armature_nodetype='NULL',path_mode='STRIP',use_mesh_modifiers=False)
bpy.ops.object.select_all(action='DESELECT');rig.select_set(True);mesh.select_set(True)
bpy.context.view_layer.objects.active=rig
bpy.ops.export_scene.fbx(filepath=str(OUT/'Exports/M14_SoftDeath_v06.fbx'),
    object_types={'ARMATURE','MESH'},bake_anim=False,mesh_smooth_type='FACE',**settings)
mesh.select_set(False)
bpy.ops.export_scene.fbx(filepath=str(OUT/'Exports/A_M14_Death_v06.fbx'),object_types={'ARMATURE'},
    bake_anim=True,bake_anim_use_all_actions=False,bake_anim_use_nla_strips=False,bake_anim_simplify_factor=0.,**settings)

# Collision authoring uses this same terminal surface, not the standing body's
# hulls. Spatial cells retain thickness and concavity with one compound body.
step=.62
cells=np.floor(final[:,:2]/step).astype(np.int32)
groups,ids=np.unique(cells,axis=0,return_inverse=True)
directions=np.array([(a,b,c) for a in (-1,0,1) for b in (-1,0,1) for c in (-1,0,1) if (a,b,c)!=(0,0,0)])
hulls=[]
for index,cell in enumerate(groups):
    region=final[ids==index]
    if len(region)<4:continue
    # A finite support point set is sufficient for a convex cook; no source
    # surface is simplified or removed from the visible mesh.
    extreme=region[np.argmax(region@directions.T,axis=0)]
    hull=np.unique(extreme,axis=0)
    if hull[:,2].max()-hull[:,2].min()<.008:
        bottom=hull.copy();bottom[:,2]-=.004
        top=hull.copy();top[:,2]+=.004
        hull=np.concatenate((bottom,top))
    hulls.append((hull*100).tolist())
(OUT/'Exports/soft_corpse_hulls.json').write_text(json.dumps({'coordinates':'Blender armature cm','hulls':hulls},indent=2)+'\n',encoding='utf8')
scene.frame_set(0)
blend=OUT/'Authoring/M14_Rigged_SoftDeath_v06.blend'
bpy.ops.wm.save_as_mainfile(filepath=str(blend),compress=True)
record=dict(source_blend=str(source),blend=str(blend),mesh_fbx=str(OUT/'Exports/M14_SoftDeath_v06.fbx'),
    death_fbx=str(OUT/'Exports/A_M14_Death_v06.fbx'),death_seconds=3.6,morphs=names,morph_key_seconds=times,
    physics_fraction=.9,physics_handoff_seconds=3.24,terminal_hulls=len(hulls),
    source_triangles=len(mesh.data.polygons),mesh_faces_removed=0,weights_changed=False,
    other_source_actions_changed=False,rendered=False,tested=False,
    method='Continuous tissue-space morph stages; neutral bone scale; terminal flattened compound collision.')
(OUT/'Records/authoring.json').write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
print('M14_V06_SOFT_DEATH_AUTHORED',flush=True)
