"""Author V3: right/rear load, fast left/down cut and embedded-blade recovery.

KayKit's CC0 Slice/Chop are timing references, not retargeted skin or contacts.
H3 grips and V2 arm support stay; hit recovery and camera share a runtime profile.
"""
import bpy
import copy
import json
import math
import statistics
from pathlib import Path
from mathutils import Matrix, Quaternion, Vector

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
CFG = json.loads((HERE / 'motion.json').read_text(encoding='utf-8'))
PROFILE = json.loads((ROOT / CFG['runtime_profile']).read_text(encoding='utf-8'))
CONTACT = PROFILE['contact_seconds']
SWING_END = PROFILE['swing_seconds']
HIT_END = CONTACT + PROFILE['hit_recover_seconds']
OUT = HERE / 'Export'
OUT.mkdir(parents=True, exist_ok=True)
idle_dir = ROOT / 'SourceAssets/KimodoAxeIdle20260919'
receipt = json.loads((idle_dir / 'BuildH3/authoring.json').read_text(encoding='utf-8'))
IDLE = receipt['config']
bpy.ops.wm.open_mainfile(filepath=receipt['blend'])
bpy.context.preferences.filepaths.save_version = 0
scene = bpy.context.scene
rig = bpy.data.objects['SK_Harvest_Axe_Rig']
rig.data.pose_position = 'POSE'
rig.animation_data.action = bpy.data.actions[IDLE['name']]
rig.animation_data.action_slot = rig.animation_data.action.slots[0]
scene.frame_set(0)
bpy.context.view_layer.update()
rest = {b.name:b.matrix_local.copy() for b in rig.data.bones}
local_rest = {b.name:rest[b.parent.name].inverted() @ rest[b.name] if b.parent else rest[b.name]
              for b in rig.data.bones}
idle = {b.name:b.matrix.copy() for b in rig.pose.bones}
ready = idle['WPN_root'].copy()
grips = {s:ready.inverted() @ idle['hand_'+s] for s in ('r','l')}
fingers = {s:{b.name:idle['hand_'+s].inverted() @ idle[b.name] for b in rig.data.bones
              if b.name.endswith('_'+s) and b.name.startswith(('thumb','index','middle','ring','pinky'))}
           for s in ('r','l')}
pivot = Vector(CFG['grip_pivot_local_m'])
ready_center = ready @ pivot
shaft = ready.to_quaternion() @ Vector((0,0,1))
ready_values = [math.degrees(math.asin(shaft.y)), math.degrees(math.atan2(shaft.z,shaft.x)), *ready_center]


def ease(u):
    u = min(1.,max(0.,u))
    return u*u*u*(10-15*u+6*u*u)


def envelope(t,end):
    return ease(t/.12)*(1-ease((t-(end-.22))/.22))


def wrap(angle):
    return (angle+math.pi)%(2*math.pi)-math.pi


def unwrap(angle, previous):
    return angle if previous is None else previous+wrap(angle-previous)


def make_knot(k):
    center = Vector(k['center']) if 'center' in k else ready_center+Vector(k['center_offset'])
    return {'t':k['t'], 'v':[k['theta'],k['slope'],*center], 'stop':k.get('stop',False)}


def curve(knots):
    # Monotone cubic Hermite slopes retain passing motion at the intermediate
    # poses. Only the deliberate load and end points stop; no easing at each key.
    out = copy.deepcopy(knots)
    for i,k in enumerate(out):
        k['m'] = [0.]*5
        if i==0 or i==len(out)-1 or k.get('stop'):
            continue
        h0=k['t']-out[i-1]['t']; h1=out[i+1]['t']-k['t']
        for j in range(5):
            a=(k['v'][j]-out[i-1]['v'][j])/h0
            b=(out[i+1]['v'][j]-k['v'][j])/h1
            if a*b>0:
                w0=2*h1+h0; w1=h1+2*h0
                k['m'][j]=(w0+w1)/(w0/a+w1/b)
    return out


def sample(knots,t):
    if t<=knots[0]['t']: return knots[0]['v'][:]
    if t>=knots[-1]['t']: return knots[-1]['v'][:]
    for a,b in zip(knots,knots[1:]):
        if a['t']<=t<=b['t']:
            dt=b['t']-a['t']; u=(t-a['t'])/dt
            return [(2*u**3-3*u*u+1)*x+(u**3-2*u*u+u)*dt*vx+
                    (-2*u**3+3*u*u)*y+(u**3-u*u)*dt*vy
                    for x,y,vx,vy in zip(a['v'],b['v'],a['m'],b['m'])]


def tool_frame(values):
    theta,slope = [math.radians(x) for x in values[:2]]
    diagonal=Vector((math.cos(slope),0,math.sin(slope)))
    forward=Vector((0,1,0))
    shaft=diagonal*math.cos(theta)+forward*math.sin(theta)
    edge=-diagonal*math.sin(theta)+forward*math.cos(theta)
    q=Matrix((edge,shaft.cross(edge).normalized(),shaft)).transposed().to_quaternion()
    return Matrix.LocRotScale(Vector(values[2:])-q@pivot,q,Vector((1,1,1)))


swing_curve=curve([{'t':0.,'v':ready_values,'stop':True}]+
                  [make_knot(k) for k in CFG['swing_knots']]+
                  [{'t':SWING_END,'v':ready_values,'stop':True}])
contact_values=sample(swing_curve,CONTACT)
contact_frame=tool_frame(contact_values)

# Pick the leading edge of the actual axe head in its bind space. While lodged,
# this blade point stays fixed and the handle levers around it.
tool=bpy.data.objects['Harvest_Axe']
to_tool=rest['WPN_root'].inverted() @ rig.matrix_world.inverted() @ tool.matrix_world
vertices=[to_tool@v.co for v in tool.data.vertices]
leading=max(v.x for v in vertices)
edge_vertices=[v for v in vertices if v.x>=leading-.008]
blade_local=sum(edge_vertices,Vector())/len(edge_vertices)
blade_anchor=contact_frame@blade_local


def pry_angle(age):
    if age<PROFILE['pry_start_seconds']:
        u=(age-PROFILE['hit_stop_seconds'])/(PROFILE['pry_start_seconds']-PROFILE['hit_stop_seconds'])
        return .65*math.sin(2*math.pi*u)*math.sin(math.pi*u)**2 if 0<u<1 else 0.
    keys=PROFILE['pry_keys']
    for a,b in zip(keys,keys[1:]):
        if a['t']<=age<=b['t']:
            return a['angle']+(b['angle']-a['angle'])*ease((age-a['t'])/(b['t']-a['t']))
    return 0.


def anchored_frame(angle,offset):
    q=Quaternion(Vector((1,0,0)),math.radians(angle)) @ contact_frame.to_quaternion()
    return Matrix.LocRotScale(blade_anchor+offset-q@blade_local,q,Vector((1,1,1)))


extracted=anchored_frame(PROFILE['extract_pitch_degrees'],Vector(PROFILE['extract_offset_m']))
corner=tool_frame(make_knot({'t':0,**CFG['hit_return_corner']})['v'])


def hit_frame(age):
    if age<=PROFILE['pry_end_seconds']:
        return anchored_frame(pry_angle(age),Vector())
    if age<PROFILE['extract_end_seconds']:
        u=(age-PROFILE['pry_end_seconds'])/(PROFILE['extract_end_seconds']-PROFILE['pry_end_seconds'])
        pull=1-(1-u)**2.6
        return anchored_frame(PROFILE['extract_pitch_degrees']*ease(u),
                              Vector(PROFILE['extract_offset_m'])*pull)
    u=ease((age-PROFILE['extract_end_seconds'])/(PROFILE['hit_recover_seconds']-PROFILE['extract_end_seconds']))
    points=[extracted.translation,corner.translation,ready.translation+Vector((-.04,-.03,-.03)),ready.translation]
    quats=[extracted.to_quaternion(),corner.to_quaternion(),ready.to_quaternion(),ready.to_quaternion()]
    while len(points)>1:
        points=[a.lerp(b,u) for a,b in zip(points,points[1:])]
        quats=[a.slerp(b,u) for a,b in zip(quats,quats[1:])]
    return Matrix.LocRotScale(points[0],quats[0],Vector((1,1,1)))

# Read the actual skin's distribution instead of copying sword helper ratios.
stations={}
for side in ('r','l'):
    fore='lowerarm_'+side; hand='hand_'+side
    axis=rest[hand].translation-rest[fore].translation
    names=[fore,'lowerarm_twist_02_'+side,'lowerarm_twist_01_'+side]
    positions={n:[] for n in names}
    for obj in bpy.data.objects:
        if obj.type!='MESH' or not any(m.type=='ARMATURE' and m.object==rig for m in obj.modifiers): continue
        to_rig=rig.matrix_world.inverted() @ obj.matrix_world
        for v in obj.data.vertices:
            if not v.groups: continue
            group=max(v.groups,key=lambda g:g.weight)
            name=obj.vertex_groups[group.group].name
            if name in positions:
                p=to_rig@v.co
                positions[name].append((p-rest[fore].translation).dot(axis)/axis.length_squared)
    stations[side]={n:(0. if n==fore else min(1.,max(0.,statistics.median(positions[n])))) for n in names}


def support(side,hand,weight):
    upper,fore,wrist=[n+'_'+side for n in ('upperarm','lowerarm','hand')]
    shoulder=rest[upper].translation+Vector((0,IDLE['shoulder_forward_m'],-IDLE['shoulder_down_m']))
    target=hand.translation
    l1=(rest[fore].translation-rest[upper].translation).length
    l2=(rest[wrist].translation-rest[fore].translation).length
    delta=target-shoulder; direction=delta.normalized()
    shoulder+=direction*max(0.,delta.length-IDLE['reach_fraction']*(l1+l2))
    distance=(target-shoulder).length
    along=(l1*l1-l2*l2+distance*distance)/(2*distance)
    radius=math.sqrt(max(0.,l1*l1-along*along))
    center=shoulder+direction*along
    natural=Vector((IDLE['elbow_outward']*(1 if side=='r' else -1),IDLE['elbow_backward'],-1))
    natural=(natural-direction*natural.dot(direction)).normalized()
    hand_deform=hand.to_quaternion() @ rest[wrist].to_quaternion().inverted()
    neutral=hand_deform @ (rest[wrist].translation-rest[fore].translation).normalized()
    desired=target-neutral*l2-center
    desired-=direction*desired.dot(direction)
    preferred=desired+natural*radius*CFG['elbow_preference']
    angle=math.atan2(direction.dot(natural.cross(preferred)),natural.dot(preferred))
    limit=math.radians(CFG['elbow_pole_limit_deg'])
    angle=min(limit,max(-limit,angle))*weight
    pole=Quaternion(direction,angle) @ natural
    return shoulder,center+pole*radius,target,hand_deform


def elbow_roll(upper_deform, fore_deform, fore_rest, direction):
    no_roll=(upper_deform@fore_rest).rotation_difference(direction) @ upper_deform
    delta=fore_deform @ no_roll.inverted()
    return wrap(2*math.atan2(Vector((delta.x,delta.y,delta.z)).dot(direction),delta.w)),no_roll


def pose_frame(wpn,t,state,end):
    if t<1e-8 or t>=end-1e-8:
        return {n:m.copy() for n,m in idle.items()}
    pose={n:m.copy() for n,m in rest.items()}
    weight=envelope(t,end)
    for side in ('r','l'):
        upper,fore,wrist=[n+'_'+side for n in ('upperarm','lowerarm','hand')]
        hand=wpn @ grips[side]
        shoulder,elbow,target,hand_deform=support(side,hand,weight)
        rest_upper=(rest[fore].translation-rest[upper].translation).normalized()
        rest_fore=(rest[wrist].translation-rest[fore].translation).normalized()
        up_axis=(elbow-shoulder).normalized(); fore_axis=(target-elbow).normalized()
        fore_deform=(hand_deform@rest_fore).rotation_difference(fore_axis) @ hand_deform
        idle_deform=idle[upper].to_quaternion() @ rest[upper].to_quaternion().inverted()
        base_upper=(idle_deform@rest_upper).rotation_difference(up_axis) @ idle_deform
        previous=state.get(side+'_shoulder',0.)
        cap=math.radians(CFG['shoulder_roll_limit_deg'])
        def cost(a):
            deform=Quaternion(up_axis,a)@base_upper
            roll,_=elbow_roll(deform,fore_deform,rest_fore,fore_axis)
            return roll*roll+CFG['shoulder_roll_continuity']*(a-previous)**2+.002*a*a
        choices=[-cap+2*cap*i/96 for i in range(97)]
        chosen=min(choices,key=cost)
        lo=max(-cap,chosen-2*cap/96); hi=min(cap,chosen+2*cap/96)
        for _ in range(18):
            a=lo+(hi-lo)*.382; b=lo+(hi-lo)*.618
            if cost(a)<cost(b): hi=b
            else: lo=a
        chosen=(lo+hi)*.5
        state[side+'_shoulder']=chosen
        up_deform=Quaternion(up_axis,chosen*weight) @ base_upper
        roll,no_roll=elbow_roll(up_deform,fore_deform,rest_fore,fore_axis)
        roll=unwrap(roll,state.get(side+'_fore'))
        state[side+'_fore']=roll
        pose['clavicle_'+side].translation+=shoulder-rest[upper].translation
        pose[upper]=Matrix.LocRotScale(shoulder,up_deform@rest[upper].to_quaternion(),Vector((1,1,1)))
        full_fore=Matrix.LocRotScale(elbow,fore_deform@rest[fore].to_quaternion(),Vector((1,1,1)))
        for index in ('01','02'):
            n='upperarm_twist_'+index+'_'+side
            pose[n]=pose[upper] @ rest[upper].inverted() @ rest[n]
        # Shoulder takes most axial difference; only the remaining pronation is
        # distributed by this mesh's skin stations. Never layer fraction twist
        # on top of an already fully twisted parent.
        for n,station in stations[side].items():
            position=(full_fore@rest[fore].inverted()@rest[n]).translation
            remaining=roll*(1-weight*(1-station))
            q=Quaternion(fore_axis,remaining)@no_roll@rest[n].to_quaternion()
            pose[n]=Matrix.LocRotScale(position,q,Vector((1,1,1)))
        pose[wrist]=hand
        for bone in rig.pose.bones:
            if bone.name in fingers[side]:
                p=pose[bone.parent.name]@local_rest[bone.name].translation
                q=hand.to_quaternion()@fingers[side][bone.name].to_quaternion()
                pose[bone.name]=Matrix.LocRotScale(p,q,Vector((1,1,1)))
    pose['WPN_root']=wpn
    return pose


def apply_pose(pose):
    for b in rig.pose.bones:
        parent_inv=pose[b.parent.name].inverted() if b.parent else Matrix.Identity(4)
        b.matrix_basis=local_rest[b.name].inverted()@parent_inv@pose[b.name]
    bpy.context.view_layer.update()


report={'runtime_tested':False,'rendered':False,'config':CFG,'source':receipt['blend'],
        'reference':json.loads((HERE.parent/'V2/Reference/source.json').read_text(encoding='utf-8-sig')),
        'runtime_profile':PROFILE,'blade_pivot_tool_local_m':list(blade_local),
        'skin_stations':stations,'clips':{}}
contact_state=None
for clip,duration in [('Swing',.68),('HitRecover',.44)]:
    old=bpy.data.actions.get('A_Harvest_Axe_'+clip)
    if old: old.name='REF_SingleHand_'+old.name; old.use_fake_user=True
    action=bpy.data.actions.new('A_Harvest_Axe_'+clip)
    action.use_fake_user=True
    rig.animation_data.action=action
    scene.render.fps=CFG['fps']; scene.render.fps_base=1
    scene.frame_start=0; scene.frame_end=round(duration*CFG['fps'])
    state={} if clip=='Swing' else copy.deepcopy(contact_state)
    previous_quats={}
    for frame in range(scene.frame_end+1):
        scene.frame_set(frame)
        s=frame/CFG['fps']
        t=(CONTACT+s*PROFILE['hit_recover_seconds']/.44 if clip=='HitRecover' else
           (s*CONTACT/.24 if s<=.24 else CONTACT+(s-.24)*(SWING_END-CONTACT)/.44))
        wpn=hit_frame(t-CONTACT) if clip=='HitRecover' else tool_frame(sample(swing_curve,t))
        # Reuse the exact contact matrices and solver state at the branch seam.
        if clip=='HitRecover' and t<=CONTACT+PROFILE['hit_stop_seconds']:
            pose={n:m.copy() for n,m in contact_pose.items()}
        else:
            pose=pose_frame(wpn,t,state,HIT_END if clip=='HitRecover' else SWING_END)
        if clip=='Swing' and frame==round(.24*CFG['fps']):
            contact_state=copy.deepcopy(state)
            contact_pose={n:m.copy() for n,m in pose.items()}
        apply_pose(pose)
        for b in rig.pose.bones:
            b.rotation_mode='QUATERNION'
            q=b.rotation_quaternion.copy()
            if b.name in previous_quats and q.dot(previous_quats[b.name])<0: q.negate()
            b.rotation_quaternion=q; previous_quats[b.name]=q.copy()
            for channel in ('location','rotation_quaternion','scale'):
                b.keyframe_insert(channel,frame=frame,group=b.name)
    # Dense baking keeps the authored nonlinear curve; LINEAR is only the
    # interpolation between adjacent 300-Hz samples, not the motion's easing.
    for layer in action.layers:
        for strip in layer.strips:
            for bag in strip.channelbags:
                for fcurve in bag.fcurves:
                    for k in fcurve.keyframe_points: k.interpolation='LINEAR'
    bpy.ops.object.select_all(action='DESELECT')
    rig.hide_set(False); rig.select_set(True); bpy.context.view_layer.objects.active=rig
    path=OUT/(action.name+'.fbx')
    bpy.ops.export_scene.fbx(filepath=str(path),use_selection=True,object_types={'ARMATURE'},
        axis_forward='-Y',axis_up='Z',add_leaf_bones=False,bake_anim=True,
        bake_anim_use_all_actions=False,bake_anim_use_nla_strips=False,bake_anim_simplify_factor=0)
    report['clips'][clip]={'fbx':str(path),'source_seconds':duration}
    print('AXE_V3_EXPORTED '+clip,flush=True)

rig.animation_data.action=bpy.data.actions['A_Harvest_Axe_Swing']
rig.animation_data.action_slot=rig.animation_data.action.slots[0]
scene.frame_start=0; scene.frame_end=round(.68*CFG['fps']); scene.frame_set(0)
bpy.ops.file.pack_all()
blend=HERE/'Axe_TwoHand_Attack_V3_Editable.blend'
bpy.ops.wm.save_as_mainfile(filepath=str(blend))
report['blend']=str(blend)
(HERE/'authoring.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('AXE_TWO_HAND_ATTACK_V3_AUTHORED',flush=True)
