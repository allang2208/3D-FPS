"""V3: first-person arrow-step/upward cut, two demonstrations at 0-8 s.

Visual reference: https://www.bilibili.com/video/BV1fB4y1v72r/
Original 3D keys; fixed installed V7 grip frames, no third-party motion data.
Run with Blender 5.1 in background. V1 author source/assets remain recoverable.
"""
import bpy
import json
import math
from pathlib import Path
from mathutils import Matrix, Quaternion, Vector

P = Path(__file__).parent
ROOT = P.parents[2]
DATA = json.loads((P.parent/'inputs.json').read_text(encoding='utf-8'))
SOURCE = ROOT/'SourceAssets/ModularOutfit20260925/BarePalmV7/Editable/RuneSword_BareArmsV7.blend'
FPS, END = 120, 2.10
C = Matrix.Diagonal(Vector((1,-1,1)))
NAMES = list(DATA['parents'])

def canonical(row):
    return Matrix.LocRotScale(C@Vector(row['p'])*.01,
        (C@Quaternion(row['q']).to_matrix()@C).to_quaternion(),Vector((1,1,1)))

def smooth(x):
    x=max(0.,min(1.,x))
    return x*x*x*(10+x*(-15+6*x))

def frame(axis, normal):
    y=axis.normalized()
    x=(normal-y*normal.dot(y)).normalized()
    return Matrix((x,y,x.cross(y))).transposed().to_quaternion()

def axis_twist(q,axis):
    if q.w<0:q=-q
    return 2*math.atan2(Vector((q.x,q.y,q.z)).dot(axis),q.w)

def unwrap(a,previous):
    return previous+(a-previous+math.pi)%(2*math.pi)-math.pi

def pose_matrix(p,q):
    return Matrix.LocRotScale(p,q,Vector((1,1,1)))

def arm_solution(idle, side, hand, prior_pole=None):
    """Constant-length two-bone IK, nearest supported wrist, bounded shoulder give."""
    U,F,H=['upperarm_'+side,'lowerarm_'+side,'hand_'+side]
    s0,e0,w0=[idle[n].translation for n in (U,F,H)]
    a,b=(e0-s0).length,(w0-e0).length
    target=hand.translation
    hand_delta=hand.to_quaternion()@idle[H].to_quaternion().inverted()
    wanted_fore=hand_delta@(w0-e0).normalized()
    wanted_elbow=target-wanted_fore*b
    desired_shoulder=wanted_elbow+(s0-wanted_elbow).normalized()*a
    shift=desired_shoulder-s0
    # The shoulder girdle may accompany the cut, but never drags the whole arm
    # around the hilt. Segment lengths and the two hand contacts remain fixed.
    cap=Vector((.065,.09,.065))
    shift=Vector(tuple(max(-cap[i],min(cap[i],shift[i])) for i in range(3)))
    shoulder=s0+shift
    ray=target-shoulder
    distance=ray.length
    maximum=(a+b)*.94
    if distance>maximum:
        shoulder+=ray.normalized()*(distance-maximum)
        ray=target-shoulder;distance=ray.length
    axis=ray.normalized()
    pole=wanted_elbow-shoulder
    pole-=axis*pole.dot(axis)
    fallback=e0-s0-axis*(e0-s0).dot(axis)
    if pole.length<1e-6:pole=fallback
    pole.normalize()
    if prior_pole is not None:
        transported=prior_pole-axis*prior_pole.dot(axis)
        if transported.length>1e-6:
            transported.normalize()
            # Rate-bound the elbow bend plane; no pole flip at singular poses.
            turn=transported.rotation_difference(pole)
            angle=turn.angle
            if angle>math.radians(3.0):
                pole=Quaternion().slerp(turn,math.radians(3.0)/angle)@transported
    along=(a*a-b*b+distance*distance)/(2*distance)
    elbow=shoulder+axis*along+pole*math.sqrt(max(0,a*a-along*along))
    fore=(target-elbow).normalized()
    upper=(elbow-shoulder).normalized()
    old_upper=(e0-s0).normalized();old_fore=(w0-e0).normalized()
    normal=upper.cross(fore).normalized();old_normal=old_upper.cross(old_fore).normalized()
    upper_delta=frame(upper,normal)@frame(old_upper,old_normal).inverted()
    fore_delta=frame(fore,normal)@frame(old_fore,old_normal).inverted()
    wanted_q=hand_delta@idle[F].to_quaternion()
    distal_q=(wanted_fore.rotation_difference(fore)@wanted_q).normalized()
    base_q=fore_delta@idle[F].to_quaternion()
    twist=axis_twist(distal_q@base_q.inverted(),fore)
    bend=wanted_fore.angle(fore)
    cost=bend*bend*8+twist*twist*.30+(shoulder-s0).length_squared*24
    cost+=max(0,elbow.z+.06)**2*30+max(0,.055-elbow.y)**2*60
    cost+=max(0,(-elbow.x if side=='r' else elbow.x)+.03)**2*25
    return dict(U=U,F=F,H=H,shoulder=shoulder,elbow=elbow,hand=hand,
                upper_delta=upper_delta,fore_delta=fore_delta,axis=fore,
                twist=twist,pole=pole,cost=cost,bend=bend)

def apply_arm(pose,idle,sol,twist):
    U,F,H=sol['U'],sol['F'],sol['H'];side=H[-1]
    du,df=sol['upper_delta'],sol['fore_delta']
    pose[U]=pose_matrix(sol['shoulder'],du@idle[U].to_quaternion())
    pose[F]=pose_matrix(sol['elbow'],df@idle[F].to_quaternion())
    # Preserve each helper's accepted rest/idle offset and distribute only the
    # NEW pronation. This leaves both idle seams exactly in their current pose.
    for segment,delta,origin,old in [('upperarm',du,sol['shoulder'],idle[U].translation),
                                     ('lowerarm',df,sol['elbow'],idle[F].translation)]:
        for suffix,station in [('02',.2739),('01',.8634)]:
            name=segment+'_twist_'+suffix+'_'+side
            if name not in idle:continue
            rotation=delta@idle[name].to_quaternion()
            if segment=='lowerarm':rotation=Quaternion(sol['axis'],twist*station)@rotation
            pose[name]=pose_matrix(origin+delta@(idle[name].translation-old),rotation)
    pose[H]=sol['hand']
    clavicle='clavicle_'+side
    pose[clavicle]=idle[clavicle].copy()
    pose[clavicle].translation+=sol['shoulder']-idle[U].translation
    hand_delta=pose[H]@idle[H].inverted()
    for name in NAMES:
        ancestor=DATA['parents'][name]
        while ancestor in DATA['parents']:
            if ancestor==H:
                pose[name]=hand_delta@idle[name];break
            ancestor=DATA['parents'][ancestor]

def hermite(a,b,va,vb,u,duration):
    return ((2*u**3-3*u*u+1)*a+(u**3-2*u*u+u)*duration*va
            +(-2*u**3+3*u*u)*b+(u**3-u*u)*duration*vb)

def trajectory(t,idle):
    """Plant low, brace, explode upward, carry over, unload along the side.

    Both reference demonstrations use a distinct planted preparation before
    the rising release. The finishing arc continues past the top; there is
    no V2 head-side forward-pointing guard hold. Runtime supplies the grounded
    step and eye-height weight transfer, never by stretching these arm chains.
    """
    original=idle['WPN_root']
    d0=(idle['Blade_Tip'].translation-idle['Blade_Base'].translation).normalized()
    idle_pitch=math.degrees(math.atan2(d0.z,math.hypot(d0.x,d0.y)))
    def blade_rotation(pitch,yaw):
        # A continuous sagittal arc carries the blade through vertical. Taking
        # a fresh shortest-direction rotation each frame can change twist branch
        # at the low load or the over-shoulder follow-through.
        return Quaternion((0,0,1),math.radians(-yaw))@Quaternion((1,0,0),math.radians(pitch-idle_pitch))
    # Position velocities are metres/second, pitch/yaw velocities degrees/second.
    # The drive/catch keys share nonzero tangents: there is no stop halfway up.
    knots=[
        (0., original.translation,Vector((0,0,0)),idle_pitch,0.,0.,0.),
        (.18,Vector(( .245,.360,-.205)),Vector(( .45,-.24,-.60)), -26.,38.,-510.,125.),
        (.36,Vector(( .285,.310,-.295)),Vector(( .08,-.04,-.10)), -78.,48., -65.,  0.),
        (.58,Vector(( .300,.295,-.315)),Vector((0,0,0)),         -84.,48.,   0.,  0.),
        (.70,Vector(( .300,.305,-.315)),Vector((-.15,.12,.08)),  -80.,45., 115.,-80.),
        (.82,Vector(( .180,.460,-.175)),Vector((-1.4,.50,1.90)),-30.,20., 740.,-170.),
        (.94,Vector(( .015,.485, .085)),Vector((-1.2,-.30,1.6)), 60.,-6., 590.,  0.),
        (1.05,Vector((-.120,.405,.165)),Vector((-1.,-.70,-.10)),110.,12.,245.,150.),
        (1.20,Vector((-.250,.310,.040)),Vector((0,0,0)),        128.,30.,  0.,  0.),
        (1.48,Vector((-.150,.400,-.160)),Vector((.35,.06,0)),    65.,-25., 0.,0.),
        (END,original.translation,Vector((0,0,0)),idle_pitch,0.,0.,0.)]
    first,last=knots[0],knots[-1]
    influence=smooth(t/.18)*(1-smooth((t-1.48)/(END-1.48)))
    for a,b in zip(knots,knots[1:]):
        if t>b[0]:continue
        dt=b[0]-a[0];u=(t-a[0])/dt
        pos=hermite(a[1],b[1],a[2],b[2],u,dt)
        pitch=hermite(a[3],b[3],a[5],b[5],u,dt)
        yaw=hermite(a[4],b[4],a[6],b[6],u,dt)
        return pos,blade_rotation(pitch,yaw),influence
    return original.translation.copy(),Quaternion(),0.

receipts={}
for variant,entry in DATA['variants'].items():
    bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
    bpy.context.preferences.filepaths.save_version=0
    scene=bpy.context.scene;rig=next(o for o in scene.objects if o.type=='ARMATURE')
    rig.animation_data_clear()
    rest={b.name:b.matrix_local.copy() for b in rig.data.bones}
    parents={b.name:(b.parent.name if b.parent else None) for b in rig.data.bones}
    local_rest={n:(rest[parents[n]].inverted()@m if parents[n] else m) for n,m in rest.items()}
    idle={n:canonical(row) for n,row in entry['world'].items()}
    reference={n:canonical(row) for n,row in DATA['reference'].items()}
    correction={n:reference[n].to_quaternion().inverted()@rest[n].to_quaternion() for n in rest}
    rig.animation_data_create()
    action=bpy.data.actions.new('Sword_UppercutV3_'+variant)
    action.use_fake_user=True;rig.animation_data.action=action
    frames=int(round(FPS*END));samples=[];previous={};blend_previous={}
    states={side:dict(pole=None,twist=0.) for side in ('l','r')}
    roll_previous=0.
    grip={side:idle['WPN_root'].inverted()@idle['hand_'+side] for side in ('l','r')}
    for i in range(frames+1):
        t=i/FPS
        position,rotation,influence=trajectory(t,idle)
        pose={n:m.copy() for n,m in idle.items()}
        if i not in (0,frames):
            sword_q=rotation@idle['WPN_root'].to_quaternion()
            d0=(idle['Blade_Tip'].translation-idle['Blade_Base'].translation).normalized()
            axis=rotation@d0
            candidates=[]
            for degrees in range(-34,35):
                roll=math.radians(degrees)*influence
                if abs(roll-roll_previous)>math.radians(1.5):continue
                weapon=pose_matrix(position,Quaternion(axis,roll)@sword_q)
                solutions={side:arm_solution(idle,side,weapon@grip[side],states[side]['pole']) for side in ('l','r')}
                score=sum(s['cost'] for s in solutions.values())+.10*roll*roll+2*(roll-roll_previous)**2
                candidates.append((score,roll,weapon,solutions))
            if not candidates:
                roll=roll_previous*influence
                weapon=pose_matrix(position,Quaternion(axis,roll)@sword_q)
                solutions={side:arm_solution(idle,side,weapon@grip[side],states[side]['pole']) for side in ('l','r')}
            else:
                _,roll,weapon,solutions=min(candidates,key=lambda a:a[0])
            roll_previous=roll
            pose['WPN_root']=weapon
            for side,solution in solutions.items():
                twist=unwrap(solution['twist'],states[side]['twist'])
                states[side]=dict(twist=twist,pole=solution['pole'])
                apply_arm(pose,idle,solution,twist)
            weapon_delta=weapon@idle['WPN_root'].inverted()
            for name in NAMES:
                ancestor=DATA['parents'][name]
                while ancestor in DATA['parents']:
                    if ancestor=='WPN_root':pose[name]=weapon_delta@idle[name];break
                    ancestor=DATA['parents'][ancestor]
        # Native UE transforms retain their original scale channels. No FBX
        # retarget/scale heuristics are involved in installing these tracks.
        ue={n:Matrix.LocRotScale(C@m.translation*100,
            (C@m.to_quaternion().to_matrix()@C).to_quaternion(),Vector(entry['world'][n]['s'])) for n,m in pose.items()}
        keys={}
        for n in NAMES:
            par=DATA['parents'][n]
            local=ue[par].inverted()@ue[n] if par in ue else ue[n]
            p,q,s=local.decompose()
            if n in previous and q.dot(previous[n])<0:q=-q
            previous[n]=q.copy();keys[n]=dict(p=list(p),q=list(q),s=list(s))
        samples.append(dict(seconds=t,bones=keys))
        scene.frame_set(i)
        worlds={n:pose_matrix(pose[n].translation,pose[n].to_quaternion()@correction[n]) for n in rest}
        for bone in rig.pose.bones:
            parent_world=worlds[bone.parent.name] if bone.parent else Matrix.Identity(4)
            basis=local_rest[bone.name].inverted()@parent_world.inverted()@worlds[bone.name]
            bone.matrix_basis=basis;bone.rotation_mode='QUATERNION'
            q=bone.rotation_quaternion.copy()
            if bone.name in blend_previous and q.dot(blend_previous[bone.name])<0:q=-q
            bone.rotation_quaternion=q;blend_previous[bone.name]=q.copy()
            for channel in ('location','rotation_quaternion','scale'):bone.keyframe_insert(channel,frame=i,group=bone.name)
    for layer in action.layers:
        for strip in layer.strips:
            for bag in strip.channelbags:
                for curve in bag.fcurves:
                    for key in curve.keyframe_points:key.interpolation='LINEAR'
    scene.render.fps=FPS;scene.render.fps_base=1
    scene.frame_start=0;scene.frame_end=frames;scene.frame_set(0)
    out=P/variant;out.mkdir(exist_ok=True)
    patch=dict(revision='ArrowStepUppercutV3',variant=variant,source_idle=entry['idle'],
               fps=FPS,intervals=frames,seconds=END,samples=samples)
    (out/'editable_keys.json').write_text(json.dumps(patch,separators=(',',':')),encoding='utf-8')
    bpy.ops.wm.save_as_mainfile(filepath=str(out/'Sword_UppercutV3_Editable.blend'))
    receipts[variant]=dict(blend=str(out/'Sword_UppercutV3_Editable.blend'),keys=str(out/'editable_keys.json'),seconds=END)
    print('ARROW_STEP_UPPERCUT_V3_AUTHORED '+variant,flush=True)
(P/'authoring.json').write_text(json.dumps(dict(revision='ArrowStepUppercutV3',
    sources='Installed V7 arms and idle grip; original 3D adaptation from visual reference',
    reference=dict(url='https://www.bilibili.com/video/BV1fB4y1v72r/',seconds=[0,8],subject='player arrow step and upward cut, both demonstrations',viewed_in_browser=True),
    paid_motion_used=False,phases=dict(step=[.10,.36],brace=[.36,.70],rising_cut=[.70,1.05],carry_over=[1.05,1.20],recover=[1.20,END]),
    fps=FPS,variants=receipts,runtime_tested=False,rendered=False),indent=2),encoding='utf-8')
