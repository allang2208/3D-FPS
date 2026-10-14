"""Crown-edge guillotine: authored motion, skinned contact path and original audio."""
import ast, bpy, json, math, wave, sys
import numpy as np
from pathlib import Path
from mathutils import Matrix, Vector, Quaternion
ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/RootCrown20261014')
FAST='--double-downstroke' in sys.argv
VERSION='V02' if FAST else 'V01'
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'Authored/RootCrown_LocomotionV01.blend'))
rig=next(o for o in bpy.context.scene.objects if o.type=='ARMATURE')
mesh=next(o for o in bpy.context.scene.objects if o.type=='MESH' and any(m.type=='ARMATURE' and m.object==rig for m in o.modifiers))
rest={b.name:b.matrix_local.copy() for b in rig.data.bones};head={n:m.translation.copy() for n,m in rest.items()}
chains=[['Bone_004','Bone_003','Bone_002'],['Bone_008','Bone_007','Bone_006','Bone_005'],['Bone_012','Bone_011','Bone_010','Bone_009']]
centers=[Vector((.085,.365,head['Bone_002'].z)),Vector((-.54,-.04,head['Bone_005'].z)),Vector((.365,-.39,head['Bone_009'].z))]
tree=ast.parse(Path('D:/FPS3D/FPSGAME/Tools/RootCrown/author_locomotion.py').read_text('utf8'))
exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='solve'],type_ignores=[]),'tripod_ik','exec'))
scene=bpy.context.scene;scene.render.fps=60;scene.unit_settings.system='METRIC';scene.unit_settings.scale_length=1.
rig.animation_data_create()
for pb in rig.pose.bones:pb.rotation_mode='QUATERNION'
vertices=np.array([v.co[:] for v in mesh.data.vertices])
radius=np.linalg.norm(vertices[:,[0,2]]-np.array([.18,.67]),axis=1)
angle=np.arctan2(vertices[:,2]-.67,vertices[:,0]-.18)
angle=np.where(angle<math.radians(-30),angle+math.tau,angle)
rim=[]
for theta in np.radians(np.linspace(-22,197,24)):
    ids=np.where((np.abs(angle-theta)<math.radians(5))&(vertices[:,2]>.53))[0]
    edge=ids[radius[ids]>=np.percentile(radius[ids],96)]
    # Use actual front-surface vertices; no invented socket beyond the skin.
    target=np.median(vertices[edge],axis=0);target[1]=np.percentile(vertices[edge,1],20)
    rim.append(int(edge[np.argmin(np.sum((vertices[edge]-target)**2,axis=1))]))

def ease(x):
    x=max(0.,min(1.,x));return x*x*x*(10+x*(-15+6*x))
def curve(t,keys):
    for (a,x),(b,y) in zip(keys,keys[1:]):
        if t<=b:return x+(y-x)*ease((t-a)/(b-a))
    return keys[-1][1]
def rotate_local(n,axis,degrees):
    return Quaternion(rest[n].to_quaternion().inverted()@Vector(axis),math.radians(degrees)).to_matrix().to_4x4()
def source_pose(t):
    for pb in rig.pose.bones:pb.matrix_basis=Matrix.Identity(4)
    # Long tightening, short acceleration, follow-through, low exposure,
    # then a delayed recovery. The feet remain planted throughout.
    pitch=curve(t,[(0,0),(.30,-5),(.85,-18),(1.0,-18),(1.12,18),(1.25,67),(1.40,76),(1.63,69),(2.60,67),(3.20,0)])
    yaw=curve(t,[(0,0),(.85,42),(1.,42),(1.14,25),(1.30,-27),(1.43,-42),(1.72,-35),(2.60,-32),(3.2,0)])
    roll=curve(t,[(0,0),(.85,-18),(1.,-18),(1.25,17),(1.43,25),(1.65,18),(2.60,16),(3.2,0)])
    retract=curve(t,[(0,0),(.85,.036),(1.,.036),(1.26,-.040),(1.43,-.020),(2.6,-.014),(3.2,0)])
    settle=curve(t,[(0,-.03),(.4,-.043),(1.,-.046),(1.30,-.026),(1.46,-.050),(2.6,-.041),(3.2,-.03)])
    pivot=head['Bone_000']
    body=Matrix.Translation(Vector((0,retract,settle)))@Matrix.Translation(pivot)@Matrix.Rotation(math.radians(pitch*.09),4,'X')@Matrix.Translation(-pivot)
    desired={'Root':rest['Root'].copy(),'Bone_000':body@rest['Bone_000'],'Bone_001':body@rest['Bone_001']}
    for chain,center in zip(chains,centers):solve(chain,body,center,Quaternion(),desired)
    for pb in rig.pose.bones:
        n=pb.name;parent=pb.parent.name if pb.parent else None
        if n not in desired:desired[n]=desired[parent]@rest[parent].inverted()@rest[n] if parent else rest[n].copy()
        if n in ('Stem_Lower','Stem_Upper','Crown_Base'):
            share={'Stem_Lower':.34,'Stem_Upper':.42,'Crown_Base':.15}[n]
            desired[n]=desired[n]@rotate_local(n,(0,0,1),yaw*share)@rotate_local(n,(1,0,0),pitch*share)@rotate_local(n,(0,1,0),roll*share)
        elif n.startswith('Crown_') and n!='Crown_Base':
            _,number,part=n.split('_');theta=math.radians(-25+25*(int(number)-1))
            lag={'Base':0.,'Flex':.025,'Rim':.055}[part]
            tension=curve(t-lag,[(0,0),(.85,-1.2),(1.,-1.2),(1.26,2.0),(1.50,-.7),(1.80,.3),(2.1,0),(3.2,0)])
            desired[n]=desired[n]@rotate_local(n,(-math.sin(theta),0,math.cos(theta)),tension*{'Base':.8,'Flex':1.6,'Rim':2.2}[part])
        pb.matrix_basis=rest[n].inverted()@rest[parent]@desired[parent].inverted()@desired[n] if parent else rest[n].inverted()@desired[n]
    bpy.context.view_layer.update()

def pose(t):
    # Keep the 3.2 s overall contract and all recovery poses. Add a brief
    # anticipation hold, execute the original 0.4 s fall in exactly 0.2 s,
    # then hold the contact pose for 0.1 s before the original recovery.
    if FAST:
        if 1.<t<1.1:t=1.
        elif 1.1<=t<=1.3:t=1.+2.*(t-1.1)
        elif 1.3<t<1.4:t=1.4
    source_pose(t)

action=bpy.data.actions.new('A_RootCrown_CrownSlash_'+VERSION);action.use_fake_user=True;rig.animation_data.action=action
scene.frame_start=1;scene.frame_end=193
frames=[]
for f in range(193):
    scene.frame_set(f+1);pose(f/60.)
    for pb in rig.pose.bones:
        for channel in ('location','rotation_quaternion','scale'):pb.keyframe_insert(data_path=channel,frame=f+1,group=pb.name)
    if (65 if FAST else 60)<=f<=(78 if FAST else 87):
        evaluated=mesh.evaluated_get(bpy.context.evaluated_depsgraph_get())
        # UE mesh coordinates before the character's -90 yaw and display scale.
        points=[[float(evaluated.data.vertices[i].co.x*100),float(-evaluated.data.vertices[i].co.y*100),float(evaluated.data.vertices[i].co.z*100)] for i in rim]
        frames.append(dict(time=f/60.,points=points))
for o in scene.objects:o.select_set(False)
rig.select_set(True);mesh.select_set(True);bpy.context.view_layer.objects.active=rig
exports=ROOT/('Exports/Slash'+VERSION);exports.mkdir(exist_ok=True)
bpy.ops.export_scene.fbx(filepath=str(exports/('A_RootCrown_CrownSlash_'+VERSION+'.fbx')),use_selection=True,object_types={'MESH','ARMATURE'},axis_forward='-Y',axis_up='Z',apply_unit_scale=True,apply_scale_options='FBX_SCALE_ALL',add_leaf_bones=False,mesh_smooth_type='FACE',use_tspace=True,bake_anim=True,bake_anim_use_all_actions=False,bake_anim_use_nla_strips=False,bake_anim_simplify_factor=0.)
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/('Authored/RootCrown_CrownSlash'+VERSION+'.blend')))
(exports/'contact.json').write_text(json.dumps(dict(frames=frames,vertices=rim,space='UE skeletal mesh cm before component transform',hit_start=1.10,hit_end=1.30 if FAST else 1.40,duration=3.20,downstroke_speed=2 if FAST else 1),indent=2),encoding='utf8')

# Original deterministic sound design, no external recording or listening run.
audio_dir=ROOT/('Audio/Slash'+VERSION);audio_dir.mkdir(parents=True,exist_ok=True)
rate=48000;rng=np.random.default_rng(141014)
def noise(n,width):return np.convolve(rng.normal(size=n),np.ones(width)/width,mode='same')
def save_wave(name,samples):
    samples=samples/max(1e-6,float(np.max(np.abs(samples))))*.65
    with wave.open(str(audio_dir/name),'wb') as stream:
        stream.setparams((1,2,rate,len(samples),'NONE','not compressed'));stream.writeframes((samples*32767).astype('<i2').tobytes())
t=np.arange(round(3.2*rate))/rate
wind=(np.clip(t/.22,0,1)*np.clip(((1.16 if FAST else 1.06)-t)/.12,0,1))*(.12+.60*np.clip(t,0,1)**2)
rubber=(noise(len(t),50)*.6+np.sin(2*np.pi*(72*t+11*t*t)+.6*np.sin(2*np.pi*7*t))*.07+noise(len(t),4)*.07)*wind
air=np.exp(-((t-(1.215 if FAST else 1.23))/(.0475 if FAST else .095))**2)*(noise(len(t),9)*.6+noise(len(t),45)*.5)
settle=np.exp(-((t-1.50)/.13)**2)*(noise(len(t),110)*.4+np.sin(2*np.pi*48*t)*.04)
save_wave('RootCrown_SlashGesture.wav',rubber+air+settle)
t=np.arange(round(.42*rate))/rate
hit=(noise(len(t),8)*.32+noise(len(t),70)*.75+np.sin(2*np.pi*(105*t-65*t*t))*.22)*np.exp(-t*13)*np.minimum(1,t/.004)
save_wave('RootCrown_SlashContact.wav',hit)
(ROOT/('Reports/slash_authoring_v2.json' if FAST else 'Reports/slash_authoring.json')).write_text(json.dumps(dict(clip='A_RootCrown_CrownSlash_'+VERSION,duration=3.2,windup=1.1 if FAST else 1.,downstroke_seconds=.2 if FAST else .4,downstroke_speed=2 if FAST else 1,hit_window=[1.1,1.3 if FAST else 1.4],contact_hold=[1.3,1.4] if FAST else [],low_recovery=[1.4,2.6],cooldown=5.,rim_points=24,audio_source='original deterministic synthesis',mesh_and_weights='unchanged',rendered=False,tested=False),indent=2),encoding='utf8')
print('ROOT_CROWN_SLASH_AUTHORED',flush=True)
