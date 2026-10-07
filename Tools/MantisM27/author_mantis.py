"""Author M27's original Meshy surface, custom rig and in-place motion in centimeters.

This is a production/export script. It does not render, simulate, or run the game.
"""
from pathlib import Path
import json, math
import bpy
import numpy as np
from mathutils import Vector, Matrix, Quaternion

ROOT = Path('D:/FPS3D/FPSGAME/SourceAssets/MantisM27/ProductionV1')
OUT = ROOT/'Delivery'
OUT.mkdir(parents=True, exist_ok=True)
DATA = np.load(ROOT/'source_geometry.npz')
RAW = DATA['positions'].astype(float)
GROUND = float(RAW[:,1].min())
def point(xyz):
    x,y,z = xyz
    return Vector((x*100,-z*100,(y-GROUND)*100))
def direction(xyz):
    x,y,z=xyz
    return Vector((x,-z,y))

bpy.ops.wm.read_factory_settings(use_empty=True)
scene=bpy.context.scene
scene.unit_settings.system='METRIC'; scene.unit_settings.scale_length=.01
scene.render.fps=30
positions=np.column_stack((RAW[:,0],-RAW[:,2],RAW[:,1]-GROUND))*100
normals=DATA['normals'][:,[0,2,1]].copy(); normals[:,1]*=-1
triangles=DATA['indices']
mesh_data=bpy.data.meshes.new('M27_OriginalMeshySurface')
mesh_data.from_pydata(positions.tolist(),[],triangles.tolist()); mesh_data.update()
surface=bpy.data.objects.new('M27_OriginalSurface',mesh_data); scene.collection.objects.link(surface)
for polygon in mesh_data.polygons: polygon.use_smooth=True
mesh_data.normals_split_custom_set_from_vertices(normals.tolist())
uv=DATA['uv'].copy(); uv[:,1]=1-uv[:,1]
mesh_data.uv_layers.new(name='OriginalMeshyUV').data.foreach_set('uv',uv[triangles.reshape(-1)].reshape(-1))

material=bpy.data.materials.new('M27_OriginalPBR'); material.use_nodes=True
nodes=material.node_tree.nodes; links=material.node_tree.links
bsdf=nodes.get('Principled BSDF')
source=ROOT.parent/'MeshyImport20261005V1/Source'
for semantic,filename in [('color','texture_0.png'),('normal','normal.png'),('orm','texture_0_metallic_roughness.png')]:
    tex=nodes.new('ShaderNodeTexImage'); tex.image=bpy.data.images.load(str(source/filename)); tex.label=semantic
    if semantic=='color': links.new(tex.outputs['Color'],bsdf.inputs['Base Color'])
    else:
        tex.image.colorspace_settings.name='Non-Color'
        if semantic=='normal':
            node=nodes.new('ShaderNodeNormalMap'); links.new(tex.outputs['Color'],node.inputs['Color']); links.new(node.outputs['Normal'],bsdf.inputs['Normal'])
        else:
            node=nodes.new('ShaderNodeSeparateColor'); links.new(tex.outputs['Color'],node.inputs['Color'])
            links.new(node.outputs['Green'],bsdf.inputs['Roughness']); links.new(node.outputs['Blue'],bsdf.inputs['Metallic'])
surface.data.materials.append(material)

# Coordinates are joints on this source, not a replacement human display mesh.
spec={}
def add(name, xyz, parent=None, tail=None): spec[name]={'head':point(xyz),'parent':parent,'tail':point(tail) if tail else None}
add('root',(0,GROUND,0),None,(0,GROUND+.05,0))
add('pelvis',(0,-.04,-.06),'root',(0,.07,-.085))
spines=[(.07,-.085),(.20,-.095),(.34,-.10),(.47,-.095),(.60,-.075)]
for i,(y,z) in enumerate(spines): add('spine_%02d'%(i+1),(0,y,z),'pelvis' if i==0 else 'spine_%02d'%i)
add('neck_01',(0,.68,-.025),'spine_05'); add('neck_02',(0,.74,.025),'neck_01')
add('head',(0,.805,.105),'neck_02'); add('head_tip',(0,.94,.135),'head',(0,.97,.135))
add('headfront',(0,.835,.24),'head',(0,.835,.27))
for side,sign in [('l',1),('r',-1)]:
    def limb(n,xyz,p,t=None): add(n+'_'+side,(sign*xyz[0],xyz[1],xyz[2]),p+'_'+side if p in ('clavicle','upperarm','lowerarm','thigh','calf','foot','blade_root','blade_mid') else p,(sign*t[0],t[1],t[2]) if t else None)
    limb('clavicle',(.10,.60,-.08),'spine_05')
    limb('upperarm',(.205,.605,-.085),'clavicle')
    limb('lowerarm',(.30,.31,-.14),'upperarm',(.43,.00,-.195))
    limb('hand',(.43,.00,-.195),'lowerarm',(.45,-.06,-.20))
    limb('blade_root',(.35,.16,-.175),'lowerarm',(.50,-.32,-.218))
    limb('blade_mid',(.50,-.32,-.218),'blade_root',(.37,-.785,-.177))
    limb('blade_tip',(.37,-.785,-.177),'blade_mid',(.365,-.81,-.17))
    limb('thigh',(.12,-.08,-.055),'pelvis')
    limb('calf',(.19,-.36,.055),'thigh')
    limb('foot',(.195,-.82,-.09),'calf')
    limb('ball',(.19,-.918,.04),'foot',(.19,-.93,.10))
    limb('membrane',(.065,-.12,-.025),'pelvis',(.065,-.60,-.03))
    limb('chain',(.245,.37,-.07),'upperarm',(.28,.02,-.07))
arm=bpy.data.armatures.new('M27_AnatomicalRig')
rig=bpy.data.objects.new('Armature',arm); scene.collection.objects.link(rig)
bpy.context.view_layer.objects.active=rig; rig.select_set(True)
bpy.ops.object.mode_set(mode='EDIT')
for name,s in spec.items():
    b=arm.edit_bones.new(name); b.head=s['head']
    children=[v['head'] for v in spec.values() if v['parent']==name]
    b.tail=s['tail'] or (children[0] if children else b.head+Vector((0,0,4)))
    if s['parent']: b.parent=arm.edit_bones[s['parent']]
    b.use_connect=False; b.align_roll(Vector((0,-1,0)))
bpy.ops.object.mode_set(mode='OBJECT')
rest={b.name:b.matrix_local.copy() for b in arm.bones}
local={b.name:(b.parent.matrix_local.inverted()@b.matrix_local if b.parent else b.matrix_local.copy()) for b in arm.bones}
names=list(rest); index={n:i for i,n in enumerate(names)}

# Continuous anatomical fields; blades remain rigid below the elbow, while
# elbow/shoulder bridges and hanging torso tissue have separate influence sets.
W=np.zeros((len(RAW),len(names)),dtype=np.float32)
def smooth(a,b,x):
    t=np.clip((x-a)/(b-a),0,1); return t*t*(3-2*t)
def segment_distance(start,end):
    a=np.asarray(start); v=np.asarray(end)-a
    t=np.clip(((positions-a)@v)/max(float(v@v),1e-8),0,1)
    return np.linalg.norm(positions-a-t[:,None]*v,axis=1)
def field(group,mask,width=7):
    distances=np.column_stack([segment_distance(arm.bones[n].head_local,arm.bones[n].tail_local) for n in group])
    values=np.exp(-((distances-distances.min(axis=1,keepdims=True))/width)**2)
    values/=values.sum(axis=1,keepdims=True)
    for j,n in enumerate(group): W[:,index[n]]+=values[:,j]*mask
x,y,z=RAW.T; ax=np.abs(x)
arm_edge=np.interp(y,[-1,-.6,0,.35,.60,.72,1],[.30,.30,.28,.225,.16,.19,.3])
arm_mask=smooth(arm_edge-.025,arm_edge+.025,ax)*(1-smooth(.68,.78,y))
head_mask=smooth(.66,.79,y)*(1-arm_mask)
remaining=1-arm_mask-head_mask
leg_mask=(1-smooth(-.10,.015,y))*smooth(.075,.13,ax)*remaining
membrane_mask=(1-smooth(-.16,-.04,y))*(1-smooth(.085,.125,ax))*(remaining-leg_mask)
body_mask=np.maximum(remaining-leg_mask-membrane_mask,0)
field(['pelvis']+['spine_%02d'%i for i in range(1,6)]+['neck_01','neck_02'],body_mask,7)
field(['neck_02','head'],head_mask,4)
for side,sign in [('l',1),('r',-1)]:
    same=(x*sign>=0).astype(float)
    elbow=smooth(.20,.40,y)
    W[:,index['lowerarm_'+side]]+=arm_mask*same*(1-elbow)
    field(['clavicle_'+side,'upperarm_'+side,'lowerarm_'+side],arm_mask*same*elbow,5)
    field(['thigh_'+side,'calf_'+side,'foot_'+side,'ball_'+side],leg_mask*same,4)
    W[:,index['membrane_'+side]]+=membrane_mask*same
# Equal weights across UV seams, without welding or altering the display mesh.
_, inverse=np.unique(np.round(RAW,6),axis=0,return_inverse=True)
merged=np.zeros((inverse.max()+1,len(names)),dtype=np.float32)
np.add.at(merged,inverse,W); merged/=np.bincount(inverse)[:,None]; W=merged[inverse]
top=np.argpartition(W,-4,axis=1)[:,-4:]
limited=np.zeros_like(W); rows=np.arange(len(W))[:,None]; limited[rows,top]=W[rows,top]
limited/=limited.sum(axis=1,keepdims=True)
# Batch vertex groups using 12-bit weights, then normalize in Blender's deform data.
for j,name in enumerate(names):
    group=surface.vertex_groups.new(name=name)
    quantized=np.rint(limited[:,j]*4095).astype(np.int32)
    for q in np.unique(quantized):
        if q: group.add(np.flatnonzero(quantized==q).tolist(),float(q)/4095,'REPLACE')
surface.parent=rig
modifier=surface.modifiers.new('M27 anatomical skin','ARMATURE'); modifier.object=rig
bpy.context.view_layer.objects.active=surface; rig.select_set(False); surface.select_set(True)
bpy.ops.object.mode_set(mode='WEIGHT_PAINT'); bpy.ops.object.vertex_group_normalize_all(lock_active=False); bpy.ops.object.mode_set(mode='OBJECT')
print('M27 original surface bound to custom centimeter rig',flush=True)

donors={k:np.load(ROOT/(k+'_donor.npz')) for k in ['Idle','Walk','Dizzy','Fall','GetUp','ProneGetUp']}
di={k:{n:i for i,n in enumerate(d['names'])} for k,d in donors.items()}
def mat(k,frame,name): return Matrix(donors[k]['frames'][frame,di[k][name]].tolist())
def pos(k,frame,name): return mat(k,frame,name).translation
def quat(k,frame,name): return mat(k,frame,name).to_quaternion()
R={n:m.to_quaternion() for n,m in rest.items()}
def build(rot=None,hip=None):
    rot=rot or {}; transforms={}
    for name in names:
        parent=spec[name]['parent']
        t=transforms[parent]@local[name] if parent else local[name].copy()
        if name in rot:
            location=t.translation.copy(); t=rot[name].to_matrix().to_4x4(); t.translation=location
        if name=='pelvis' and hip is not None: t.translation=hip
        transforms[name]=t
    return transforms
def ik_leg(transforms,side,target,foot_rotation=None):
    a,b,c=['%s_%s'%(n,side) for n in ['thigh','calf','foot']]
    hip=transforms[a].translation; delta=target-hip
    l1=(rest[b].translation-rest[a].translation).length; l2=(rest[c].translation-rest[b].translation).length
    length=min(max(delta.length,abs(l1-l2)+.01),l1+l2-.02); axis=delta.normalized()
    bend=Vector((0,-1,0)); bend=(bend-axis*bend.dot(axis)).normalized()
    along=(l1*l1-l2*l2+length*length)/(2*length)
    knee=hip+axis*along+bend*math.sqrt(max(0,l1*l1-along*along))
    rotations={n:m.to_quaternion() for n,m in transforms.items()}
    rotations[a]=(rest[b].translation-rest[a].translation).rotation_difference(knee-hip)@R[a]
    rotations[b]=(rest[c].translation-rest[b].translation).rotation_difference(target-knee)@R[b]
    rotations[c]=foot_rotation or R[c]
    # Markers and secondary bones inherit, never counter-rotate against their parent.
    for n in list(rotations):
        if n.startswith(('blade_','hand_','headfront','head_tip','membrane_','chain_','ball_')): rotations.pop(n)
    return build(rotations,transforms['pelvis'].translation)
def planted(transforms):
    for side in ['l','r']: transforms=ik_leg(transforms,side,rest['foot_'+side].translation.copy())
    return transforms

def retarget(role,f):
    neutral_role='Idle' if role in ('Idle','Walk') else 'GetUp'
    neutral_f=0 if neutral_role=='Idle' else len(donors['GetUp']['frames'])-1
    rotations={}
    for name in names:
        if name not in di[role] or name not in di[neutral_role]: continue
        delta=quat(role,f,name)@quat(neutral_role,neutral_f,name).inverted()
        if role in ('Idle','Walk') and name.startswith(('upperarm','lowerarm','clavicle')):
            delta=Quaternion().slerp(delta,.30 if role=='Walk' else .50)
        rotations[name]=delta@R[name]
    ratio=(rest['pelvis'].translation.z-rest['foot_l'].translation.z)/(pos(neutral_role,neutral_f,'pelvis').z-pos(neutral_role,neutral_f,'foot_l').z)
    source_hip=pos(role,f,'pelvis'); reference=pos(neutral_role,neutral_f,'pelvis')
    motion=(source_hip-reference)*ratio
    if role=='Walk':
        # Root travel is handled by CharacterMovement. Retain bob and sway only.
        start=pos(role,0,'pelvis'); end=pos(role,len(donors[role]['frames'])-1,'pelvis')
        t=f/(len(donors[role]['frames'])-1); motion.y=(source_hip.y-start.lerp(end,t).y)*ratio
        motion.x=(source_hip.x-start.x)*ratio
    hip=rest['pelvis'].translation+motion
    trans=build(rotations,hip)
    if role=='Idle': return planted(trans)
    if role=='Walk':
        # Preserve the donor stance/swing rhythm at a shorter creature stride.
        for side in ['l','r']:
            n='foot_'+side; track=donors['Walk']['frames'][:,di['Walk'][n],:3,3]
            hips=donors['Walk']['frames'][:,di['Walk']['pelvis'],:3,3]
            relative=track-hips
            target=rest[n].translation.copy()
            target.y+=(relative[f,1]-relative[:,1].mean())*ratio*.40
            target.x+=(relative[f,0]-relative[:,0].mean())*ratio*.40
            target.z+=max(0,track[f,2]-track[:,2].min())*ratio*.65
            # Toe lift follows the motion without twisting the long claws sideways.
            footq=Quaternion((1,0,0),math.radians(-8)*min(1,(target.z-rest[n].translation.z)/8))@R[n]
            trans=ik_leg(trans,side,target,footq)
    return trans

def blend(a,b,t):
    t=max(0,min(1,t)); t=t*t*(3-2*t)
    rotations={n:a[n].to_quaternion().slerp(b[n].to_quaternion(),t) for n in names}
    return build(rotations,a['pelvis'].translation.lerp(b['pelvis'].translation,t))
idle=build()
def secondary(trans,t,amplitude=1):
    # Small baked membrane follow-through; no cloth simulation added to the runtime.
    rotations={n:m.to_quaternion() for n,m in trans.items() if not n.startswith(('blade_','hand_','headfront','head_tip','chain_'))}
    for side,phase in [('l',0),('r',1.3)]:
        n='membrane_'+side
        rotations[n]=trans[n].to_quaternion()@Quaternion((1,0,0),math.radians(2.0)*math.sin(t*math.pi*2+phase)*amplitude)
    return build(rotations,trans['pelvis'].translation)

def slash(side,t):
    sign=1 if side=='l' else -1
    # World directions for shoulder-to-elbow and rigid elbow-to-blade-tip.
    keys=[(0,None,None,0),(.30,(sign*.85,.1,.30),(sign*.80,-.2,-.55),-sign*18),
          (.46,(sign*.68,-.5,-.1),(sign*.48,-.85,-.20),-sign*8),
          (.58,(sign*.48,-.6,-.35),(-sign*.25,-.96,-.12),sign*12),
          (.72,(sign*.15,-.65,-.45),(-sign*.85,-.45,-.20),sign*21),
          (1.10,None,None,0),(1.35,None,None,0)]
    upper='upperarm_'+side; lower='lowerarm_'+side; tip='blade_tip_'+side
    def pose(k):
        _,u,v,twist=k
        if u is None: return idle
        rotations={}
        for i in range(1,6): rotations['spine_%02d'%i]=Quaternion((0,0,1),math.radians(twist*i/5))@R['spine_%02d'%i]
        rotations[upper]=(rest[lower].translation-rest[upper].translation).rotation_difference(Vector(u))@R[upper]
        rotations[lower]=(rest[tip].translation-rest[lower].translation).rotation_difference(Vector(v))@R[lower]
        opposite='r' if side=='l' else 'l'
        rotations['upperarm_'+opposite]=Quaternion((0,1,0),math.radians(-sign*8))@R['upperarm_'+opposite]
        return planted(build(rotations,rest['pelvis'].translation+Vector((0,0,-3))))
    for a,b in zip(keys,keys[1:]):
        if a[0]<=t<=b[0]: return secondary(planted(blend(pose(a),pose(b),(t-a[0])/(b[0]-a[0]))),t,.5)
    return idle

clips={}
for role in ['Idle','Walk','Dizzy','GetUp','ProneGetUp']:
    frames=[]; count=len(donors[role]['frames'])
    for f in range(count):
        trans=retarget(role,f)
        if role=='Dizzy':
            trans=planted(trans)
        if role in ['GetUp','ProneGetUp'] and f>count-10:
            trans=blend(trans,idle,(f-(count-10))/9)
        frames.append(secondary(trans,f/30,.5 if role in ['GetUp','ProneGetUp'] else 1))
    if role in ['Idle','Walk','Dizzy']:
        # Endpoint continuity authored into the final six samples.
        for f in range(max(0,count-6),count): frames[f]=blend(frames[f],frames[0],(f-(count-6))/5)
    clips[role]=frames
for side,role in [('l','LeftSlash'),('r','RightSlash')]: clips[role]=[slash(side,f/30) for f in range(42)]
clips['Hit']=[]
for f in range(22):
    t=f/21; impact=math.sin(min(1,t/.25)*math.pi/2)*(1-smooth(.28,1,t))
    rotations={n:Quaternion((1,0,0),math.radians(-11)*impact*i/5)@R[n] for i,n in enumerate(['spine_01','spine_02','spine_03','spine_04','spine_05'],1)}
    rotations['head']=Quaternion((1,0,0),math.radians(-15)*impact)@R['head']
    clips['Hit'].append(planted(build(rotations,rest['pelvis'].translation+Vector((0,3*impact,-2*impact)))))
# The local knockback donor supplies the initial recoil; end on the actual
# supine get-up start pose so transitions use the same anatomical reference.
recoil=retarget('Fall',0)
ground_pose=clips['GetUp'][0]
clips['Fall']=[]
for f in range(31):
    t=f/30
    trans=blend(idle,recoil,t/.22) if t<.22 else blend(recoil,ground_pose,(t-.22)/.68)
    clips['Fall'].append(trans)
clips['Death']=clips['Fall']+[ground_pose for _ in range(45)]

def select_rig(with_mesh=False):
    bpy.ops.object.select_all(action='DESELECT'); rig.select_set(True)
    if with_mesh: surface.select_set(True)
    bpy.context.view_layer.objects.active=rig
def export(path,animation=False):
    bpy.ops.export_scene.fbx(filepath=str(path),use_selection=True,object_types={'ARMATURE','MESH'} if not animation else {'ARMATURE'},
        apply_unit_scale=True,apply_scale_options='FBX_SCALE_NONE',global_scale=1.0,
        axis_forward='-Y',axis_up='Z',add_leaf_bones=False,use_armature_deform_only=False,
        armature_nodetype='NULL',mesh_smooth_type='FACE',use_mesh_modifiers=False,
        bake_anim=animation,bake_anim_use_all_bones=True,bake_anim_use_nla_strips=False,
        bake_anim_use_all_actions=False,bake_anim_force_startend_keying=True,bake_anim_step=1,bake_anim_simplify_factor=0,
        path_mode='STRIP',embed_textures=False)

rig.animation_data_create(); select_rig(True)
scene.frame_set(0)
export(OUT/'SK_MantisM27.fbx')
manifest={'name':'螳螂-M27','revision':'ProductionV1','fps':30,'height_cm':float(np.ptp(positions[:,2])),
    'source_geometry':'Meshy original, no decimation or display-mesh substitution','triangles':len(triangles),'bones':names,
    'source':'../../MeshyImport20261005V1/Source/Meshy_AI_M_27_Mawbound_Horror_1005150638_texture.glb',
    'units':'centimeter vertex/bone data, object scales one','clips':{},'tested':False,'user_review_pending':True}
walk=donors['Walk']; p0=pos('Walk',0,'pelvis'); p1=pos('Walk',len(walk['frames'])-1,'pelvis')
leg_ratio=(rest['pelvis'].translation.z-rest['foot_l'].translation.z)/(pos('Idle',0,'pelvis').z-pos('Idle',0,'foot_l').z)
stride_speed=abs(p1.y-p0.y)*leg_ratio*.40/((len(walk['frames'])-1)/30)
for role,frames in clips.items():
    action=bpy.data.actions.new('A_M27_'+role); rig.animation_data.action=action
    scene.frame_start=1; scene.frame_end=len(frames)
    for f,trans in enumerate(frames,1):
        for name in names:
            parent=spec[name]['parent']
            basis=local[name].inverted()@(trans[parent].inverted()@trans[name] if parent else trans[name])
            pb=rig.pose.bones[name]; loc,rotation,scale=basis.decompose()
            pb.rotation_mode='QUATERNION'; pb.location=loc; pb.rotation_quaternion=rotation; pb.scale=(1,1,1)
            pb.keyframe_insert('location',frame=f,group=name); pb.keyframe_insert('rotation_quaternion',frame=f,group=name)
    action.use_fake_user=True
    scene.frame_set(1); select_rig(); filename='A_M27_'+role+'.fbx'; export(OUT/filename,True)
    manifest['clips'][role]={'file':filename,'duration_seconds':(len(frames)-1)/30,'frames':len(frames),'loop':role in ('Idle','Walk','Dizzy')}
    if role=='Walk': manifest['clips'][role]['expected_speed_cm_s']=stride_speed
    if role in ('LeftSlash','RightSlash'): manifest['clips'][role]['contact_window_seconds']=[.48,.68]
    print('M27 exported '+role,flush=True)
rig.animation_data.action=bpy.data.actions['A_M27_Idle']; scene.frame_start=1; scene.frame_end=len(clips['Idle']); scene.frame_set(1)
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'MantisM27_ProductionV1.blend'))
(OUT/'motion_manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
(OUT/'source_and_license.json').write_text(json.dumps({'mesh':'User supplied Meshy export; preserve user account/license provenance',
    'donors':json.loads((ROOT/'donor_sources.json').read_text(encoding='utf-8')),
    'locomotion_license':'Existing project-local Epic template animation; subject to its original Unreal license',
    'reactions_license':'Existing project-local Mesh2Motion-derived reaction sources; see HumanoidStun20260926 and HumanoidKnockdown20260926 provenance',
    'original_actions':['LeftSlash','RightSlash','Hit'],'notes':'No external model download, donor display mesh, or automatic runtime acceptance'},ensure_ascii=False,indent=2),encoding='utf-8')
print('M27 authoring sources and FBX delivery saved',flush=True)
