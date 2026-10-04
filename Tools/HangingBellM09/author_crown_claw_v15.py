"""M09-specific paired rake: continuous elbow plane and bounded wrist articulation.

Uses the accepted Attack_D contact pacing, with a newly authored spatial path for
M09's short proximal arm, long forearm, crossed guard and ceiling support.
"""
import bpy, json, math
from pathlib import Path
from mathutils import Matrix, Quaternion, Vector
ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/HangingBellM09Meshy20261003')
OUT=ROOT/'CrownClawV15'
for folder in ('Authoring','Exports','Records'):(OUT/folder).mkdir(parents=True,exist_ok=True)
FPS=60;DURATION=1.1
bpy.ops.wm.open_mainfile(filepath=str(OUT/'Authoring/M09_Rigged_ClawV15.blend'))
rig=bpy.data.objects['M09_Rig_V03'];scene=bpy.context.scene
scene.render.fps=FPS;scene.render.fps_base=1.;scene.frame_start=1;scene.frame_end=67
rig.data.pose_position='POSE';rig.animation_data_clear();rig.animation_data_create()
for p in rig.pose.bones:
    for c in list(p.constraints):p.constraints.remove(c)
    p.rotation_mode='QUATERNION'
rest={b.name:b.matrix_local.copy() for b in rig.data.bones}
local={b.name:(rest[b.parent.name].inverted()@rest[b.name] if b.parent else rest[b.name]) for b in rig.data.bones}
donor=json.loads((ROOT/'CrownClawV11/Records/donor_motion.json').read_text())

def smooth(x):
    x=max(0.,min(1.,x));return x*x*x*(10+x*(-15+6*x))

def env(t,a,b,c,d):return smooth((t-a)/(b-a))*(1-smooth((t-c)/(d-c)))

def frame(direction,normal):
    y=direction.normalized();z=(normal-y*normal.dot(y)).normalized()
    return Matrix((y.cross(z).normalized(),y,z)).transposed().to_quaternion()

def curve(t,knots):
    if t<=knots[0][0]:return knots[0][1].copy()
    if t>=knots[-1][0]:return knots[-1][1].copy()
    for k,((a,p),(b,q)) in enumerate(zip(knots,knots[1:])):
        if t>b:continue
        v0=Vector((0,0,0)) if k==0 else (q-knots[k-1][1])/(b-knots[k-1][0])
        v1=Vector((0,0,0)) if k+2==len(knots) else (knots[k+2][1]-p)/(knots[k+2][0]-a)
        u=(t-a)/(b-a)
        return (2*u**3-3*u*u+1)*p+(u**3-2*u*u+u)*(b-a)*v0+(-2*u**3+3*u*u)*q+(u**3-u*u)*(b-a)*v1

# Full accepted donor samples inform the rapid contact progression, rather than
# transferring its standing humanoid's shoulder elevation to the hanging body.
progress={}
for side in ('L','R'):
    samples=donor['clips'][side];suffix=side.lower();points=[]
    for p in samples[30:43]:
        torso=Matrix(p['spine_05']);hand=Matrix(p['hand_'+suffix])
        points.append((torso.inverted()@hand).translation)
    arc=[0.]
    for a,b in zip(points,points[1:]):arc.append(arc[-1]+(b-a).length)
    progress[side]=[v/arc[-1] for v in arc]

def paced(t,side):
    if not .35<t<.55:return t
    u=(t-.35)/.2;f=u*12;i=min(11,int(f));v=progress[side][i]*(1-(f-i))+progress[side][i+1]*(f-i)
    # Smoothly bring in the donor acceleration; preserve endpoint speeds.
    return t+.2*(v-u)*math.sin(math.pi*u)**2*.65

chains={}
for side,sign in [('L',1),('R',-1)]:
    upper,fore,hand=[f'small_{n}_{side}' for n in ('upperarm','forearm','hand')]
    s,e,w=[rest[n].translation for n in (upper,fore,hand)]
    u=e-s;f=w-e;n=u.cross(f).normalized();reach=(w-s).normalized()
    pole=(u-reach*u.dot(reach)).normalized()
    # Wrist locations, metres, front = -Y. Contact rakes in front of the eye
    # crown and down toward the player, never above the small-arm shoulder.
    knots=[(0.,w.copy()),(.20,Vector((sign*.255,-.565,1.06))),
           (.32,Vector((sign*.245,-.695,1.17))),
           (.40,Vector((sign*.205,-.715,1.115))),
           (.55,Vector((sign*.085,-.635,.985))),
           (.66,Vector((sign*.025,-.550,.925))),
           (.84,Vector((sign*.025,-.480,.950))),(DURATION,w.copy())]
    chains[side]=(upper,fore,hand,s,e,w,u,f,n,reach,pole,knots)

def set_global_rotation(name,q,globals_):
    parent=rig.data.bones[name].parent
    parent_q=globals_[parent.name] if parent else Quaternion()
    rig.pose.bones[name].rotation_quaternion=local[name].to_quaternion().inverted()@parent_q.inverted()@q
    globals_[name]=q

action=bpy.data.actions.new('A_M09_CrownClaw_V15');action.use_fake_user=True
rig.animation_data.action=action
names=[b.name for b in rig.data.bones if b.use_deform]
records=[]
for i in range(67):
    t=i/FPS
    for p in rig.pose.bones:p.location=(0,0,0);p.rotation_quaternion=Quaternion();p.scale=(1,1,1)
    globals_={n:m.to_quaternion() for n,m in rest.items()}
    for side,delay in [('R',0.),('L',.025)]:
        upper,fore,hand,s,e0,w0,u0,f0,n0,reach0,pole0,knots=chains[side]
        # Both return to the exact guard on the shared 1.10 s boundary.
        ts=max(0.,t-delay) if t<=.7 else .7-delay+(t-.7)*(DURATION-.7+delay)/(DURATION-.7)
        wrist=curve(paced(ts,side),knots)
        reach=wrist-s;distance=reach.length;r=reach.normalized()
        a,b=u0.length,f0.length
        distance=max(abs(b-a)+.008,min(a+b-.008,distance));wrist=s+r*distance
        # Parallel transport the original signed bend plane. It cannot choose
        # the opposite elbow branch or independently twist the two arm segments.
        transported=reach0.rotation_difference(r)
        pole=transported@pole0;pole=(pole-r*pole.dot(r)).normalized()
        along=(a*a-b*b+distance*distance)/(2*distance)
        elbow=s+r*along+pole*math.sqrt(max(0.,a*a-along*along))
        u,f=elbow-s,wrist-elbow;n=u.cross(f).normalized()
        qu=frame(u,n)@frame(u0,n0).inverted()@rest[upper].to_quaternion()
        qf=frame(f,n)@frame(f0,n0).inverted()@rest[fore].to_quaternion()
        set_global_rotation(upper,qu,globals_);set_global_rotation(fore,qf,globals_)
        # Carry the palm with its forearm. Only a small anatomical flexion is
        # added, avoiding the V11 world-space palm target and crossed wrists.
        palm_delta=qf@rest[fore].to_quaternion().inverted()
        wrist_flex=-7*env(ts,.05,.25,.32,.47)+11*env(ts,.31,.50,.62,DURATION)
        local_hinge=rest[hand].to_quaternion().inverted()@n0
        qh=palm_delta@rest[hand].to_quaternion()@Quaternion(local_hinge,math.radians(wrist_flex))
        set_global_rotation(hand,qh,globals_)
        index=rest[f'smallfinger_{side}_02_01'].translation-w0
        little=rest[f'smallfinger_{side}_05_01'].translation-w0
        palm_normal=index.cross(little).normalized()
        if palm_normal.y<0:palm_normal=-palm_normal
        for digit in range(1,6):
            for joint in range(1,4):
                name=f'smallfinger_{side}_{digit:02d}_{joint:02d}'
                bone=rig.data.bones[name];direction=bone.tail_local-bone.head_local
                axis=rest[name].to_quaternion().inverted()@direction.normalized().cross(palm_normal).normalized()
                open_=env(ts,.03,.24,.32,.48);hook=env(ts,.30,.49,.65,DURATION)
                angle=(-(3+2*joint)*open_+(5+4*joint)*hook)*(.55 if digit==1 else 1.)
                rig.pose.bones[name].rotation_quaternion=Quaternion(axis,math.radians(angle))
        records.append({'t':t,'side':side,'wrist':list(wrist),'elbow':list(elbow),
                        'wrist_flex_deg':wrist_flex,'elbow_bend_deg':math.degrees(u.angle(f))})
    for name in names:
        for channel in ('location','rotation_quaternion','scale'):
            rig.pose.bones[name].keyframe_insert(channel,frame=i+1,group=name)
for slot in action.slots:
    for layer in action.layers:
        for strip in layer.strips:
            bag=strip.channelbag(slot)
            if bag:
                for fc in bag.fcurves:
                    for k in fc.keyframe_points:k.interpolation='LINEAR'
scene.frame_set(1)
bpy.ops.object.select_all(action='DESELECT');rig.select_set(True);bpy.context.view_layer.objects.active=rig
fbx=OUT/'Exports/A_M09_CrownClaw_V15.fbx'
bpy.ops.export_scene.fbx(filepath=str(fbx),use_selection=True,object_types={'ARMATURE'},
    apply_unit_scale=True,apply_scale_options='FBX_SCALE_UNITS',axis_forward='-Z',axis_up='Y',
    bake_anim=True,bake_anim_use_all_actions=False,bake_anim_use_nla_strips=False,
    bake_anim_simplify_factor=0,add_leaf_bones=False,use_armature_deform_only=True)
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'Authoring/M09_CrownClaw_V15.blend'),compress=True)
(OUT/'Records/authored_pose.json').write_text(json.dumps(records,indent=2),encoding='utf8')
(OUT/'Records/motion_manifest.json').write_text(json.dumps({
    'version':'CrownClawV15','duration':DURATION,'fps':FPS,'contact':[.35,.55],
    'design':'Uncross guard, reach forward, inward downward rake, reclose; fixed ceiling supports',
    'reference':'M07 accepted Attack_D contact acceleration; newly authored M09-specific whole-arm paths',
    'mesh_source':'CrownClawV15/Authoring/M09_Rigged_ClawV15.blend','geometry_modified':False,
    'weights_modified':'Small-arm elbow and wrist transition only, from V13 owner-separated model',
    'rig_or_bind_modified':False,'damage_cooldown_AI_unchanged':True,
    'game_tested':False,'user_accepted':False,'output':str(fbx)},indent=2),encoding='utf8')
print('M09_CROWN_CLAW_V15_AUTHORED',flush=True)
