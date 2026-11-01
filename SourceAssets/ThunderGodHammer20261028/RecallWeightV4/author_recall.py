"""Heavy palm impact: quick compression, loaded brace, then deliberate recovery."""
import ast,copy,json,math
from pathlib import Path
import bpy
from mathutils import Matrix,Quaternion,Vector

P=Path(__file__).resolve().parent;R=P.parents[2];OUT=P/'Export';OUT.mkdir(parents=True,exist_ok=True)
source=P.parent/'RecallCatchV2/ThunderHammer_RecallCatch_Editable.blend'
bpy.ops.wm.open_mainfile(filepath=str(source));bpy.context.preferences.filepaths.save_version=0
scene=bpy.context.scene;rig=bpy.data.objects['SK_RusticPickaxe_Rig'];rig.data.pose_position='POSE'
FPS=240;READY=.32;LOOP=1.;CATCH=.60;IMPACT=.025
names=['A_ThunderHammer_RecallReady_V2','A_ThunderHammer_Catch_V2'];original={}
for name in names:
    action=bpy.data.actions[name];rig.animation_data.action=action;rig.animation_data.action_slot=action.slots[0]
    rows=[]
    for frame in range(round(action.frame_range[1])+1):
        scene.frame_set(frame);rows.append({b.name:b.matrix.copy() for b in rig.pose.bones})
    original[name]=rows
rest={b.name:b.matrix_local.copy() for b in rig.data.bones}
local_rest={b.name:rest[b.parent.name].inverted()@rest[b.name] if b.parent else rest[b.name] for b in rig.data.bones}
idle=copy.deepcopy(original[names[1]][-1]);start=original[names[0]][0];receive=original[names[0]][-1]
closed={b.name:idle[b.parent.name].inverted()@idle[b.name] for b in rig.data.bones if b.name.startswith(('thumb','index','middle','ring','pinky'))}
# Reuse the complete hinged-arm solver from the current throw revision, not
# the older recall solver that puts hand roll directly through the elbow.
common=ast.parse((P.parent/'ThrowRefineV3/author_motion.py').read_text(encoding='utf-8'))
functions={'smooth','blend','unwrap','framed','project','pose_local','blend_local','blend_grip','solve'}
exec(compile(ast.Module(body=[n for n in common.body if isinstance(n,ast.FunctionDef) and n.name in functions],type_ignores=[]),'<current_hinged_solver>','exec'))
receive_r=receive['WPN_root'].inverted()@receive['hand_r']
idle_grips={s:idle['WPN_root'].inverted()@idle['hand_'+s] for s in ('l','r')}
attached=original[names[1]][round(.36*FPS)]
left_grip=attached['WPN_root'].inverted()@attached['hand_l']
hang_shoulder=Vector((-.25,-.075,-.235))
a=(rest['lowerarm_l'].translation-rest['upperarm_l'].translation).normalized()
b=(rest['hand_l'].translation-rest['lowerarm_l'].translation).normalized();rn=a.cross(b).normalized()
l1=(rest['lowerarm_l'].translation-rest['upperarm_l'].translation).length
l2=(rest['hand_l'].translation-rest['lowerarm_l'].translation).length
ua=Vector((-.06,.08,-.995)).normalized();fa=Vector((.08,.50,-.862)).normalized();normal=ua.cross(fa).normalized()
hang_rotation=framed(fa,normal)@framed(b,rn).inverted()@rest['hand_l'].to_quaternion()
hang=Matrix.LocRotScale(hang_shoulder+ua*l1+fa*l2,hang_rotation,Vector((1,1,1)))
relaxed={n:blend(m,local_rest[n],.58) for n,m in closed.items() if n.endswith('_l')}
receive_local=pose_local(receive);start_local=pose_local(start);idle_local=pose_local(idle)

# Author metres: X right, Y forward, Z up. These are palm/weapon keys,
# not a tiny oscillation layered over the old slow catch. A loaded pause
# makes the elbow absorb the hammer before the hand lifts it back to idle.
catch_keys=[
    (0.,   0.,  (0,0,0),                 (0,0,0)),
    (.025, 0.,  (0,.012,.006),           (1.5,0,0)),
    (.105, 0.,  (.020,-.165,-.090),       (-12,2.5,-3)),
    (.155, 0.,  (.023,-.174,-.098),       (-14,3,-3.5)),
    (.250, .18, (.012,-.082,-.045),       (-5,1.5,-1.5)),
    (.350, .55, (.004,-.028,-.016),       (-1.8,.6,-.5)),
    (.460, .86, (0,-.010,-.005),          (-.6,0,0)),
    (.600, 1.,  (0,0,0),                 (0,0,0)),
]

def catch_key(t):
    for a,b in zip(catch_keys,catch_keys[1:]):
        if t<=b[0]+1e-6:
            w=smooth((t-a[0])/(b[0]-a[0]))
            return (a[1]+(b[1]-a[1])*w,Vector(a[2]).lerp(Vector(b[2]),w),Vector(a[3]).lerp(Vector(b[3]),w))
    return 1.,Vector((0,0,0)),Vector((0,0,0))

grasp_local=pose_local(original[names[1]][round(.10*FPS)])
finger_close={'index':(.020,.065),'middle':(.016,.058),'ring':(.020,.064),'pinky':(.024,.070),'thumb':(.035,.082)}

defs=[]
for i in range(round((READY+LOOP)*FPS)+1):
    t=i/FPS;w=smooth(t/READY)
    hand=blend(start['hand_r'],receive['hand_r'],w)
    if t>=READY:
        u=t-READY
        hand.translation+=Vector((.0015*math.sin(2*math.pi*6*u)+.0004*math.sin(2*math.pi*11*u),
                                  .0012*math.sin(2*math.pi*7*u),.0016*math.sin(2*math.pi*5*u)))
        shake=Quaternion((1,0,0),math.radians(.42)*math.sin(2*math.pi*6*u))@Quaternion((0,0,1),math.radians(.20)*math.sin(2*math.pi*7*u))
        hand=Matrix.LocRotScale(hand.translation,shake@hand.to_quaternion(),Vector((1,1,1)))
    wpn=hand@receive_r.inverted() if t>=READY else blend(start['WPN_root'],receive['WPN_root'],w)
    fingers={n:(relaxed[n] if n.endswith('_l') else blend(start_local[n],receive_local[n],w)) for n in closed}
    defs.append({'kind':'ready','t':t,'wpn':wpn,'hands':{'l':hang.copy(),'r':hand},
                 'shoulders':{'l':hang_shoulder.copy(),'r':start['upperarm_r'].translation.lerp(receive['upperarm_r'].translation,w)},'fingers':fingers})
ready_count=len(defs)
for i,src in enumerate(original[names[1]]):
    t=i/FPS;recover,offset,angles=catch_key(t)
    right=blend(receive['hand_r'],idle['hand_r'],recover)
    # A brief loaded-arm shudder follows the large compression, rather than
    # replacing it. Right palm and weapon share every translation/rotation.
    s=max(0.,t-.105)
    envelope=math.exp(-10.*s)*smooth(s/.018)*(1.-smooth((t-.35)/.11))
    spring=math.sin(58.*s)*envelope
    right.translation+=offset+Vector((.004*math.sin(73.*s)*envelope,-.009*spring,-.0045*spring))
    angles.x+=1.8*spring;angles.z+=.65*math.sin(67.*s)*envelope
    kick=Quaternion((1,0,0),math.radians(angles.x))@Quaternion((0,1,0),math.radians(angles.y))@Quaternion((0,0,1),math.radians(angles.z))
    right=Matrix.LocRotScale(right.translation,kick@right.to_quaternion(),Vector((1,1,1)))
    # Keep the previously delivered final idle handoff after the new impact.
    tail=smooth((t-.35)/.13)
    right=blend(right,src['hand_r'],tail)
    right_grip=blend_grip(blend_grip(receive_r,idle_grips['r'],recover),src['WPN_root'].inverted()@src['hand_r'],tail)
    wpn=right@right_grip.inverted()
    left=blend(hang,wpn@blend_grip(left_grip,idle_grips['l'],smooth((t-.34)/.26)),smooth((t-.25)/.23))
    fingers={}
    for n in closed:
        if n.endswith('_l'):fingers[n]=blend(relaxed[n],idle_local[n],smooth((t-.34)/.14))
        else:
            lo,hi=next(window for prefix,window in finger_close.items() if n.startswith(prefix))
            clenched=blend(grasp_local[n],idle_local[n],recover)
            fingers[n]=blend(receive_local[n],clenched,smooth((t-lo)/(hi-lo)))
    load=max(0.,-offset.y/.174)
    defs.append({'kind':'catch','t':t,'source':src,'wpn':wpn,'hands':{'l':left,'r':right},
                 'shoulders':{'l':hang_shoulder.lerp(idle['upperarm_l'].translation,smooth((t-.25)/.25)),
                              'r':receive['upperarm_r'].translation.lerp(idle['upperarm_r'].translation,recover)+Vector((0,-.012,-.010))*load},'fingers':fingers})

# Exact two-bone circles; elbow flexion and forearm axial rotation are separate.
arm={}
for s in ('l','r'):
    U,F,H=['upperarm_'+s,'lowerarm_'+s,'hand_'+s];sgn=1 if s=='r' else -1
    a=(rest[F].translation-rest[U].translation).normalized();b=(rest[H].translation-rest[F].translation).normalized();rn=a.cross(b).normalized()
    l1=(rest[F].translation-rest[U].translation).length;l2=(rest[H].translation-rest[F].translation).length
    specs=[];angles=[]
    for d in defs:
        shoulder=d['shoulders'][s].copy();hand=d['hands'][s];v=hand.translation-shoulder;limit=(l1+l2)*.965
        if v.length>limit:shoulder+=v.normalized()*(v.length-limit);v=hand.translation-shoulder
        axis=v.normalized();dist=v.length;along=(l1*l1-l2*l2+dist*dist)/(2*dist)
        center=shoulder+axis*along;radius=math.sqrt(max(0.,l1*l1-along*along));guide=project(Vector((sgn*.85,-.15,-.40)),axis)
        neutral=hand.to_quaternion()@rest[H].to_quaternion().inverted()@b;best=None
        for j in range(-90,91):
            angle=math.radians(j*2.);elbow=center+Quaternion(axis,angle)@guide*radius
            upper=(elbow-shoulder).normalized();fore=(hand.translation-elbow).normalized();bend=upper.cross(fore).normalized()
            hinge=framed(fore,bend)@framed(b,rn).inverted();full=neutral.rotation_difference(fore)@hand.to_quaternion()@rest[H].to_quaternion().inverted()
            dq=full@hinge.inverted();twist=(2*math.atan2(Vector((dq.x,dq.y,dq.z)).dot(fore),dq.w)+math.pi)%(2*math.pi)-math.pi
            cost=neutral.angle(fore)**2+.18*twist*twist+.02*angle*angle
            cost+=600*max(0.,.095-sgn*elbow.x)**2+280*max(0.,.15-elbow.length)**2
            cost+=70*max(0.,elbow.z-hand.translation.z+.018)**2+25*max(0.,.075-elbow.y)**2
            if best is None or cost<best[0]:best=(cost,angle)
        angles.append(unwrap(best[1],angles[-1] if angles else None));specs.append((shoulder,axis,center,radius,guide,hand))
    # Smooth within each action separately; never blend the loop tail into catch.
    kernel=[1,2,3,4,5,4,3,2,1]
    for _ in range(2):
        smoothed=[]
        for lo,hi in ((0,ready_count),(ready_count,len(defs))):
            for i in range(lo,hi):smoothed.append(sum(angles[max(lo,min(hi-1,i+j-4))]*v for j,v in enumerate(kernel))/sum(kernel))
        angles=smoothed
    arm[s]=(specs,angles,a,b,rn)

poses=[];twists={}
for i,d in enumerate(defs):
    if i==ready_count:twists={}
    out=copy.deepcopy(idle)
    for s in ('l','r'):solve(out,s,i,twists)
    out['WPN_root']=d['wpn'].copy();loc=pose_local(out);loc.update(d['fingers'])
    # Keep the original right-arm entry while the already-free left arm hangs.
    if d['kind']=='ready' and d['t']<.10:
        weight=1.-smooth(d['t']/.10)
        for n in loc:
            if n.endswith('_r'):loc[n]=blend(loc[n],start_local[n],weight)
    for bone in rig.data.bones:out[bone.name]=out[bone.parent.name]@loc[bone.name] if bone.parent else loc[bone.name]
    out['WPN_root']=d['wpn'].copy()
    if d['kind']=='catch':out=blend_local(out,d['source'],smooth((d['t']-.48)/.12))
    poses.append(out)
ready,catch=poses[:ready_count],poses[ready_count:];catch[-1]=copy.deepcopy(idle)
module=ast.parse((R/'SourceAssets/SteelWarhammer20261014/SprintDragV1/author_sprint.py').read_text(encoding='utf-8'))
exec(compile(ast.Module(body=[n for n in module.body if isinstance(n,ast.FunctionDef) and n.name in {'apply_pose','new_action','bake'}],type_ignores=[]),'<native_baker>','exec'))
for name,rows in zip(names,(ready,catch)):bake(name,rows,FPS)
rig.animation_data.action=bpy.data.actions[names[0]];rig.animation_data.action_slot=rig.animation_data.action.slots[0];scene.frame_set(90)
bpy.ops.wm.save_as_mainfile(filepath=str(P/'ThunderHammer_RecallWeightV4_Editable.blend'))
(P/'motion.json').write_text(json.dumps({'revision':'RecallWeightV4','fps':FPS,'clips':names,'ready_seconds':READY,'hold_loop_seconds':LOOP,
    'catch_seconds':CATCH,'impact_seconds':IMPACT,'left_rejoin_seconds':[.25,.48],'left_hang_shoulder_m':list(hang_shoulder),
    'left_hang_wrist_m':list(hang.translation),'forearm_twist':{'elbow':0,'twist_01':1,'twist_02':.5},
    'right_wait_tremor':'1.2-1.9 mm and 0.42 deg primary; only right chain and its virtual grip frame',
    'catch_keys':catch_keys,'finger_close_windows':finger_close,
    'catch_impulse':'17.4 cm backward / 9.8 cm downward palm compression, 14 deg weapon load, braced pause and loaded shudder',
    'source':str(source),'runtime_tested':False,'preview_rendered':False},indent=2),encoding='utf-8')
print('THUNDER_RECALL_WEIGHT_V4_AUTHORED',flush=True)
