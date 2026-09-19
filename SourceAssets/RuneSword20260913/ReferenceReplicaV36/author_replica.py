"""Build editable native-frame reference and game Inspect on the retained rig.

No old inspection action is sampled. Accepted V23 end pose supplies the original
model, full closed grasp and the game idle endpoints. No render or test is run.
"""
import bpy
import json
import math
from pathlib import Path
from mathutils import Matrix, Vector, Quaternion

P=Path(__file__).parent
data=json.loads((P/'authoring_inputs.json').read_text())
replica=json.loads((P/'reference_poses.json').read_text())
SOURCE=Path(data['source'])
FPS=120
ENTRY,REFERENCE,EXIT=.35,2.,.55
DURATION=ENTRY+REFERENCE+EXIT
ONE=Vector((1,1,1))
OUT=P/'Export';OUT.mkdir(exist_ok=True)
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
s=bpy.context.scene;r=bpy.data.objects[data['rig']]
rest={n:Matrix(v['rest']) for n,v in data['bones'].items()}
idle={n:Matrix(v['idle']) for n,v in data['bones'].items()}
parent={n:v['parent'] for n,v in data['bones'].items()}
local_rest={n:rest[parent[n]].inverted()@m if parent[n] else m for n,m in rest.items()}
local_idle={n:idle[parent[n]].inverted()@m if parent[n] else m for n,m in idle.items()}
native=[{'hand':Matrix(v['hand_r']),'weapon':Matrix(v['weapon']),
         'fingers':{n:Matrix(m) for n,m in v['finger_local'].items()}} for v in replica['frames']]
grips={side:idle['WPN_root'].inverted()@idle['hand_'+side] for side in ('l','r')}
fingers={side:[n for n in rest if n.endswith('_'+side) and n.startswith(('thumb','index','middle','ring','pinky'))] for side in ('l','r')}
def depth(n):return 1+depth(parent[n]) if parent[n] else 0
for side in fingers:fingers[side].sort(key=depth)

def ease(v):
    v=max(0.,min(1.,v));return max(0.,min(1.,v*v*v*(v*(6*v-15)+10)))

def mix(a,b,w):
    w=max(0.,min(1.,w))
    return Matrix.LocRotScale(a.translation.lerp(b.translation,w),a.to_quaternion().slerp(b.to_quaternion(),w),ONE)

def window(t,a,b,c,d):return ease((t-a)/(b-a))*(1-ease((t-c)/(d-c)))

def native_at(t):
    f=max(0.,min(60.,t*30));i=min(59,int(f));u=f-i
    a,b=native[i],native[i+1]
    W=mix(a['weapon'],b['weapon'],u)
    if i>=9 or (i==0 and u==0):
        H=W@grips['r']
    else:
        H=mix(a['hand'],b['hand'],u)
        # Interpolate the weapon in hand-local contact coordinates during the
        # change of grip. The native authored endpoints are retained exactly.
        relative=mix(a['hand'].inverted()@a['weapon'],b['hand'].inverted()@b['weapon'],u)
        W=H@relative
    fs={n:mix(a['fingers'][n],b['fingers'][n],u) for n in fingers['r']}
    return H,W,fs

FREE_LEFT=idle['hand_l'].copy();FREE_LEFT.translation=Vector((-.24,.15,-.44))
reference_start_deform=native[0]['hand'].to_quaternion()@rest['hand_r'].to_quaternion().inverted()
ROLL_KEYS=[0.,.12,.22,.35,.46,.52,.45,.34,.18,.08,.08,.10,.12,.14,.15]

def arm_pose(side,H,reference_t,active):
    un,fn,hn=[n+'_'+side for n in ('upperarm','lowerarm','hand')]
    shoulder=idle[un].translation.copy()
    target=H.translation
    ru=rest[fn].translation-rest[un].translation
    rf=rest[hn].translation-rest[fn].translation
    l1,l2=ru.length,rf.length
    reach=target-shoulder;axis=reach.normalized();dist=reach.length
    if dist>l1+l2-.014:
        shoulder+=axis*(dist-(l1+l2-.014));dist=(target-shoulder).length
    hand_deform=H.to_quaternion()@rest[hn].to_quaternion().inverted()
    if side=='r':
        f=max(0.,min(14.,reference_t*30));i=min(13,int(f));u=f-i
        amount=ROLL_KEYS[i]*(1-u)+ROLL_KEYS[i+1]*u
        # Palm/forearm cooperation remains an independent track, with complete
        # bone-segment transport. It is neither a frozen forearm nor a full
        # sword rotation imposed on the forearm.
        driven=reference_start_deform.slerp(hand_deform,amount)
        if reference_t>.45:
            driven=driven.slerp(hand_deform,ease((reference_t-.45)/.50)*.45)
    else:driven=hand_deform
    ideal=target-(driven@rf.normalized())*l2
    hint=ideal-shoulder;hint-=axis*hint.dot(axis)
    outward=Vector((-.7 if side=='l' else .7,.05,-1))
    outward-=axis*outward.dot(axis);outward.normalize()
    pole=(hint/l2+outward*.42).normalized()
    old_pole=idle[fn].translation-shoulder;old_pole-=axis*old_pole.dot(axis)
    pole=old_pole.normalized().lerp(pole,active).normalized()
    along=(l1*l1-l2*l2+dist*dist)/(2*max(dist,.0001))
    elbow=shoulder+axis*along+pole*math.sqrt(max(0.,l1*l1-along*along))
    fore_axis=(target-elbow).normalized();upper_axis=(elbow-shoulder).normalized()
    fore_deform=(driven@rf.normalized()).rotation_difference(fore_axis)@driven
    fq=fore_deform@rest[fn].to_quaternion()
    # Accepted V21/V22 transport method: the upper arm and forearm share one
    # deformation frame, preventing an independently selected elbow roll.
    uq=(fore_deform@ru.normalized()).rotation_difference(upper_axis)@fore_deform@rest[un].to_quaternion()
    old_upper=(idle[fn].translation-idle[un].translation).normalized()
    old_fore=(idle[hn].translation-idle[fn].translation).normalized()
    uq=(old_upper.rotation_difference(upper_axis)@idle[un].to_quaternion()).slerp(uq,active)
    fq=(old_fore.rotation_difference(fore_axis)@idle[fn].to_quaternion()).slerp(fq,active)
    return Matrix.LocRotScale(shoulder,uq,ONE),Matrix.LocRotScale(elbow,fq,ONE)

def pose_at(t,pure=False):
    reference_t=t if pure else max(0.,min(2.,t-ENTRY))
    H,W,fs=native_at(reference_t)
    active=1. if pure else ease(t/ENTRY)*(1-ease((t-ENTRY-REFERENCE)/EXIT))
    if not pure:
        if t<ENTRY:
            W=mix(idle['WPN_root'],W,active);H=W@grips['r']
        elif t>ENTRY+REFERENCE:
            W=mix(idle['WPN_root'],W,active);H=W@grips['r']
    p={n:m.copy() for n,m in idle.items()}
    p['WPN_root']=W
    for n in ('Blade_Base','Blade_Tip'):p[n]=W@idle['WPN_root'].inverted()@idle[n]
    # The reference has a brief left-hand entrance during the late side carry.
    left_join=window(reference_t,1.26,1.38,1.43,1.55)
    left_goal=W@grips['l']
    left_goal.translation+=Vector((-.035,-.01,-.025))*(1-left_join)
    LH=mix(FREE_LEFT,left_goal,left_join)
    if not pure:LH=mix(idle['hand_l'],LH,active)
    for side,hand in (('r',H),('l',LH)):
        un,fn,hn=[n+'_'+side for n in ('upperarm','lowerarm','hand')]
        p[un],p[fn]=arm_pose(side,hand,reference_t,active)
        upper_delta=p[un]@idle[un].inverted();fore_delta=p[fn]@idle[fn].inverted()
        p['clavicle_'+side]=upper_delta@idle['clavicle_'+side]
        for segment,delta in (('upperarm',upper_delta),('lowerarm',fore_delta)):
            for number in ('01','02'):
                n=f'{segment}_twist_{number}_{side}'
                p[n]=delta@idle[n]
        p[hn]=hand
        for n in fingers[side]:
            if side=='r':m=mix(local_idle[n],fs[n],active)
            else:
                loc,q,scale=local_idle[n].decompose()
                relaxed=local_rest[n].to_quaternion().slerp(q,.43)
                m=Matrix.LocRotScale(loc,q.slerp(relaxed,active*(1-left_join*.7)),scale)
            p[n]=p[parent[n]]@m
    if not pure and (t<=0. or t>=DURATION):return {n:m.copy() for n,m in idle.items()}
    return p

def build_action(name,duration,step,pure=False):
    if name in bpy.data.actions:bpy.data.actions[name].name='RETAINED_BEFORE_V36_'+name
    action=bpy.data.actions.new(name);action.use_fake_user=True
    r.animation_data.action=action
    frames=list(range(0,round(duration*FPS)+1,step))
    if frames[-1]!=round(duration*FPS):frames.append(round(duration*FPS))
    previous={}
    for f in frames:
        p=pose_at(f/FPS,pure)
        # Cache all world targets, then reconstruct local transforms in one pass.
        for n,b in r.pose.bones.items():
            local_pose=p[parent[n]].inverted()@p[n] if parent[n] else p[n]
            loc,q,scale=(local_rest[n].inverted()@local_pose).decompose()
            if n in previous and q.dot(previous[n])<0:q.negate()
            previous[n]=q.copy()
            b.rotation_mode='QUATERNION';b.location=loc;b.rotation_quaternion=q;b.scale=scale
            for channel in ('location','rotation_quaternion','scale'):
                b.keyframe_insert(channel,frame=f,group=n)
    r.animation_data.action_slot=action.slots[0]
    for layer in action.layers:
        for strip in layer.strips:
            for bag in strip.channelbags:
                for curve in bag.fcurves:
                    for key in curve.keyframe_points:key.interpolation='LINEAR'
    s.frame_start=0;s.frame_end=round(duration*FPS);s.frame_set(0)
    return action

s.render.fps=FPS;s.render.fps_base=1.
native_action=build_action('A_RuneSword_Reference_76_78',2.,4,pure=True)
game_action=build_action('A_RuneSword_Inspect',DURATION,1)
bpy.ops.object.select_all(action='DESELECT')
r.hide_set(False);r.select_set(True);bpy.context.view_layer.objects.active=r
for action,duration in ((native_action,2.),(game_action,DURATION)):
    r.animation_data.action=action;r.animation_data.action_slot=action.slots[0]
    s.frame_start=0;s.frame_end=round(duration*FPS)
    bpy.ops.export_scene.fbx(filepath=str(OUT/(action.name+'.fbx')),use_selection=True,object_types={'ARMATURE'},
        axis_forward='-Y',axis_up='Z',add_leaf_bones=False,bake_anim=True,
        bake_anim_use_all_actions=False,bake_anim_use_nla_strips=False,bake_anim_simplify_factor=0)
    print('REFERENCE_REPLICA_EXPORTED',action.name,duration,flush=True)

# Editable reference camera only. Creating it does not render or start a preview.
camera_data=bpy.data.cameras.new('Reference_76_78_Camera')
camera=bpy.data.objects.new('Reference_76_78_Camera',camera_data);s.collection.objects.link(camera)
camera.location=(0,0,0);camera.rotation_euler=(math.pi/2,0,0)
camera_data.sensor_fit='VERTICAL';camera_data.sensor_height=24
camera_data.lens=24/(2*math.tan(math.radians(75/2)));camera_data.clip_start=.005
s.camera=camera;s.render.resolution_x=852;s.render.resolution_y=480;s.render.resolution_percentage=100
camera['ReferenceURL']='https://www.bilibili.com/video/BV1hCJFzQEyR/'
camera['ReferenceSeconds']='76.000-78.000; authored at original 30 fps'
camera['DepthNote']='Hidden depth reconstructed; original camera FOV unknown'
for marker in list(s.timeline_markers):s.timeline_markers.remove(marker)
for label,t in [('Game entry',0),('REF 76.000 closed',ENTRY),('REF 76.0667 release',ENTRY+2/30),
                ('REF 76.2000 palm open',ENTRY+6/30),('REF 76.3000 caught',ENTRY+9/30),
                ('REF 76.4667 side carry',ENTRY+14/30),('REF 77.3333 left entrance',ENTRY+40/30),
                ('REF 77.6000 lowered',ENTRY+1.6),('REF 78.000 end',ENTRY+2),('Game idle',DURATION)]:
    s.timeline_markers.new(label,frame=round(t*FPS))
r.animation_data.action=game_action;r.animation_data.action_slot=game_action.slots[0]
s.frame_start=0;s.frame_end=round(DURATION*FPS);s.frame_set(0)
r['ReferenceReplicaV36']='Native frame pose authoring; 61 source frames, no prior Inspect sampled'
text=bpy.data.texts.new('REFERENCE_REPLICA_README')
text.write('Pure reference: A_RuneSword_Reference_76_78, frame 0-240 at 120 fps; native keys every 4 frames.\n'
           'Game: A_RuneSword_Inspect, 2.90 s; exact-time reference is at 0.35-2.35 s.\n'
           'Edit reference_annotations.json, reference_poses.json or the sparse reference Action.\n'
           'No gameplay, rendered or collision acceptance has been performed.\n')
bpy.ops.file.pack_all()
bpy.ops.wm.save_as_mainfile(filepath=str(P/'AzureRunesword_ReferenceReplicaV36.blend'))
(P/'authoring.json').write_text(json.dumps({
    'revision':'ReferenceReplicaV36','source_model':str(SOURCE),
    'main_reference':'https://www.bilibili.com/video/BV1hCJFzQEyR/','reference_seconds':[76,78],
    'native_source_fps':30,'native_frame_count_including_endpoints':61,
    'editable_reference_action':native_action.name,'reference_action_seconds':2.,
    'game_action':game_action.name,'game_seconds':DURATION,'bake_fps':FPS,
    'reference_in_game_seconds':[ENTRY,ENTRY+REFERENCE],'entry_seconds':ENTRY,'exit_seconds':EXIT,
    'method':'Per-native-frame observed landmarks, independent digit poses, rigid closed grasp, complete arm segments',
    'old_inspection_motion_sampled':False,'depth_reconstruction':True,
    'mesh_weights_lengths_changed':False,'reference_camera_vertical_fov_degrees':75,
    'testing':'Not rendered, collision-tested or played in UE; user testing pending',
    'completion':'Authored reconstruction, not a verified 100 percent match'
},indent=2),encoding='utf-8')
print('REFERENCE_REPLICA_AUTHORING_COMPLETE',flush=True)
