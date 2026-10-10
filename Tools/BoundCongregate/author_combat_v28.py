"""Full-body braced ground slaps and an emphatic load / bite / tear action.

Support constraints and quaternion hemisphere continuity are solved offline.
The same seconds contract generates animation and native hit-window timings.
"""
from pathlib import Path
import bpy, json, math
from mathutils import Matrix, Vector, Quaternion

PROJECT=Path('D:/FPS3D/FPSGAME')
ROOT=PROJECT/'SourceAssets/BoundCongregateMeshy20261006'
OUT=ROOT/'CombatV28'
OUT.mkdir(exist_ok=True)
CONTRACT=json.loads((OUT/'motion_contract.json').read_text())
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'GarmentDrapeV25/BoundCongregate_GarmentDrapeV25.blend'))
rig=next(o for o in bpy.context.scene.objects if o.type=='ARMATURE')
rig.data.pose_position='POSE'
scene=bpy.context.scene
scene.render.fps=CONTRACT['fps']
recipe=json.loads((ROOT/'Authoring/rig_recipe.json').read_text())
rest={b.name:b.matrix_local.copy() for b in rig.data.bones}
pose={}
# Calibrate the palm thickness from the current outfit's original flesh skin.
# The actor aligns the mesh lower bound with the floor. A wrist at Z=0 would
# bury the palm; a reference wrist height would leave several hands hovering.
body=bpy.data.objects['BC_Flesh']
floor_z=min(v.co.z for v in body.data.vertices)
palm_heights={}
for side in ('L1','R1','L2','R2'):
    name='leg_'+side+'_foot'
    head=rig.data.bones[name].head_local
    group=body.vertex_groups[name].index
    samples=[v.co.z-head.z for v in body.data.vertices
             if (v.co-head).length<.45 and any(g.group==group and g.weight>.55 for g in v.groups)]
    if not samples:raise RuntimeError('No palm surface for '+side)
    palm_heights[side]=floor_z+.015-min(samples)

def point(p):
    return Vector((p[0]*recipe['scale'],p[1]*recipe['scale'],(p[2]-recipe['ground_z'])*recipe['scale']))

def smooth(u):
    u=max(0.,min(1.,u))
    return u*u*u*(10+u*(-15+6*u))

def curve(t,keys):
    if t<=keys[0][0]:return keys[0][1]
    for a,b in zip(keys,keys[1:]):
        if t<=b[0]:
            u=max(0.,min(1.,(t-a[0])/(b[0]-a[0])))
            # Accelerate throughout a committed strike. Other arcs ease both ends.
            w=u*u*(2-u) if len(a)>2 and a[2]=='strike' else smooth(u)
            return a[1]+(b[1]-a[1])*w
    return keys[-1][1]

def convert(name,matrix,inverse=False):
    bone=rig.data.bones[name]
    args=dict(invert=inverse)
    if bone.parent:args.update(parent_matrix=pose[bone.parent.name],parent_matrix_local=rest[bone.parent.name])
    return bone.convert_local_to_pose(matrix,rest[name],**args)

def refresh():
    for bone in rig.data.bones:pose[bone.name]=convert(bone.name,rig.pose.bones[bone.name].matrix_basis)

def assign(name,matrix):
    rig.pose.bones[name].matrix_basis=convert(name,matrix,True)
    pose[name]=matrix.copy()

def rotate(name,axis,angle):
    local=(rest[name].to_3x3().inverted()@Vector(axis)).normalized()
    rig.pose.bones[name].rotation_quaternion @= Quaternion(local,angle)

def translate(name,offset):
    rig.pose.bones[name].location=rest[name].to_3x3().inverted()@Vector(offset)

def segment(name,head,tail):
    direction=rig.data.bones[name].tail_local-rig.data.bones[name].head_local
    parent=rig.data.bones[name].parent.name
    inherited=(pose[parent]@rest[parent].inverted()).to_quaternion()
    # Transport the existing frame with only the swing needed to aim the bone.
    # The elbow plane is NOT an axial-roll target for the fleshy shoulder.
    swing=(inherited@direction).rotation_difference(tail-head)
    matrix=(swing@inherited).to_matrix().to_4x4()@rest[name]
    matrix.translation=head
    assign(name,matrix)

def stance(leg):
    hip,_,ankle,_=[point(p) for p in leg['points']]
    return ankle+Vector((hip.x-ankle.x,hip.y-ankle.y,0))*.18

def support_goal(leg,role,t):
    base=stance(leg)
    side=leg['name']
    if role=='Flurry':
        if side in ('L1','R1','L2','R2'):return base
        group={'L3':0,'R4':0,'R3':1,'L4':1,'L5':2,'R5':2}[side]
        load0,load1=.01+group*.15,.16+group*.15
        recover0,recover1=2.01+group*.125,2.13+group*.125
        offset=Vector((-base.x*.085,-.12,0))
    else:
        # The front hands brace the lunge in place. Advancing them before the
        # backward load nearly straightened them and suppressed torso travel.
        if side in ('L1','R1','L2','R2'):return base
        group={'L3':0,'R4':0,'R3':1,'L4':1,'L5':2,'R5':2}[side]
        load0,load1=.015+group*.105,.135+group*.105
        recover0,recover1=.99+group*.145,1.12+group*.145
        offset=Vector((-base.x*.075,-.18,0))
    load=smooth((t-load0)/(load1-load0))
    release=smooth((t-recover0)/(recover1-recover0))
    # Move each support only while lifted. Several other legs stay planted.
    lift=.045*(math.sin(math.pi*load)+math.sin(math.pi*release))
    return base+offset*(load-release)+Vector((0,0,lift))

def constrain_support(role,t):
    """Limit torso excursion instead of dragging a planted sole after IK clamps."""
    channels={n:rig.pose.bones[n].matrix_basis.copy() for n in ('body','body_front','body_rear')}
    def set_fraction(fraction):
        for n,matrix in channels.items():
            p,q,s=matrix.decompose()
            rig.pose.bones[n].matrix_basis=Matrix.LocRotScale(p*fraction,Quaternion().slerp(q,fraction),s)
        refresh()
    def reachable():
        for leg in recipe['legs']:
            if role=='Flurry' and leg['name'] in ('L1','R1','L2','R2'):continue
            upper='leg_'+leg['name']+'_upper'
            parent=rig.data.bones[upper].parent.name
            hip,knee,ankle,_=[point(p) for p in leg['points']]
            start=pose[parent]@rest[parent].inverted()@hip
            a,b=(knee-hip).length,(ankle-knee).length
            if not abs(a-b)+.003<=(support_goal(leg,role,t)-start).length<=(a+b)*.966:return False
        return True
    set_fraction(1.)
    if reachable():return 1.
    lo,hi=0.,1.
    for _ in range(18):
        mid=(lo+hi)*.5;set_fraction(mid)
        if reachable():lo=mid
        else:hi=mid
    set_fraction(lo)
    return lo

def leg_pose(leg,goal,palm_pitch=0.,palm_roll=0.,flex=0.):
    upper,lower,foot=['leg_'+leg['name']+'_'+suffix for suffix in ('upper','lower','foot')]
    hip,knee,ankle,_=[point(p) for p in leg['points']]
    parent=rig.data.bones[upper].parent.name
    delta=pose[parent]@rest[parent].inverted()
    start,old_knee=delta@hip,delta@knee
    a,b=(knee-hip).length,(ankle-knee).length
    if leg['name'] in palm_heights and goal.z<=palm_heights[leg['name']]+.06:
        # Preserve ground height when a planted target is near full extension.
        # A 3D reach clamp would lift it above the floor again.
        planar=Vector((goal.x-start.x,goal.y-start.y,0))
        radius=math.sqrt(max(0.,((a+b)*.965)**2-(goal.z-start.z)**2))
        if planar.length>radius:
            planar.normalize();planar*=radius
            goal=Vector((start.x+planar.x,start.y+planar.y,goal.z))
    direction=(goal-start).normalized()
    distance=max(abs(a-b)+.002,min((goal-start).length,(a+b)*.97))
    pole=old_knee-start
    # Choose the elbow on the reach circle nearest its inherited upper-arm
    # direction. The old outward pole lerp rolled that circle around the root.
    pole-=direction*pole.dot(direction)
    if pole.length<.001:pole=Vector((0,0,1))-direction*direction.z
    along=(a*a-b*b+distance*distance)/(2*distance)
    joint=start+direction*along+pole.normalized()*math.sqrt(max(0,a*a-along*along))
    end=start+direction*distance
    palm_carry=Quaternion()
    if flex>0.:
        # Load by flexing the long forearm around a stable elbow, rather than
        # chasing a raised Cartesian wrist target through a flipping IK pole.
        lower_vector=end-joint
        axis=lower_vector.cross(Vector((0,0,1))).normalized()
        shoulder_angle=.075*min(1.,flex/1.70)
        shoulder=Quaternion(axis,shoulder_angle)
        joint=start+shoulder@(joint-start)
        end=joint+Quaternion(axis,flex+shoulder_angle)@lower_vector
        palm_carry=Quaternion(axis,flex*.60+shoulder_angle)
    segment(upper,start,joint)
    segment(lower,joint,end)
    matrix=(palm_carry@Quaternion((1,0,0),palm_pitch)@Quaternion((0,1,0),palm_roll)).to_matrix().to_4x4()@rest[foot]
    matrix.translation=end;assign(foot,matrix)

def flow(t,knots):
    """Cubic Hermite path with nonzero through-velocities at arc waypoints."""
    if t<=knots[0][0]:return knots[0][1]
    if t>=knots[-1][0]:return knots[-1][1]
    velocities=[]
    for i,k in enumerate(knots):
        if len(k)>2:velocities.append(k[2]);continue
        if i==0 or i==len(knots)-1:velocities.append(k[1]*0.);continue
        a,b=knots[i-1],knots[i+1]
        left=(k[1]-a[1])/(k[0]-a[0]);right=(b[1]-k[1])/(b[0]-k[0])
        velocities.append((left*(b[0]-k[0])+right*(k[0]-a[0]))/(b[0]-a[0]))
    for i,(a,b) in enumerate(zip(knots,knots[1:])):
        if t<=b[0]:
            dt=b[0]-a[0];u=(t-a[0])/dt
            return (2*u**3-3*u*u+1)*a[1]+(u**3-2*u*u+u)*dt*velocities[i]+(-2*u**3+3*u*u)*b[1]+(u**3-u*u)*dt*velocities[i+1]


def forelimb(t,side,base):
    sign=-1 if side[0]=='L' else 1
    second=side[1]=='2'
    data=CONTRACT['flurry']
    beat={'L1':0,'R1':1,'L2':2,'R2':3}[side]
    begin=data['load_begins'][beat]
    start,contact=data['strike_starts'][beat],data['contacts'][beat]
    heavy_start,heavy_contact=data['strike_starts'][-1],data['contacts'][-1]
    hold=data['contact_hold_seconds']
    top=1.70 if not second else 1.58
    depth={'L1':-1.95,'R1':-1.70,'L2':-1.50,'R2':-1.32}[side]
    hit=Vector((sign*(.85 if second else .42),depth,palm_heights[side]))
    reach=smooth((t-begin)/(start-begin))
    if second:reach*=1.-smooth((t-contact-.18)/.34)
    else:reach*=1.-smooth((t-heavy_contact-.17)/(.31+(.03 if sign>0 else 0.)))
    ground=base.lerp(hit,reach)
    if t<start:
        # Most of the stroke is visibly spent preparing. Near the top the
        # elbow settles before a separate, very short release interval.
        flex=top*curve(t,[(begin,0.),(start-.10,.93),(start,1.)])
    elif t<contact:
        u=(t-start)/(contact-start)
        flex=top*(1.-u**2.6)
    elif t<contact+hold:
        flex=0.
    elif second:
        flex=curve(t,[(contact+hold,0.),(contact+.16,.16),(contact+.28,.23),(contact+.52,0.)])
    elif t<heavy_start:
        reset=contact+.38
        load=heavy_start-(.09 if sign<0 else .065)
        flex=curve(t,[(contact+hold,0.),(contact+.17,.15),(reset,.72),(load,1.86),(heavy_start,1.90)])
    elif t<heavy_contact:
        u=(t-heavy_start)/(heavy_contact-heavy_start)
        flex=1.90*(1.-u**2.6)
    else:
        heavy_hold=data['finisher_hold_seconds']
        flex=curve(t,[(heavy_contact,0.),(heavy_contact+heavy_hold,0.),
                      (heavy_contact+.20,.18),(heavy_contact+.31,.28),
                      (data['duration']-(.035 if sign<0 else 0.),0.)])
    # Wrist articulation leads the last third of release, reaching a flat palm
    # before the arm arrests at the floor; it does not drag the shoulder roll.
    wrist=math.sin(min(math.pi*.5,flex))
    return ground,-.34*wrist,sign*.065*wrist,flex

def pose_flurry(t,duration):
    ready=curve(t,[(0,0),(.30,.68),(.52,1),(1.78,1),(2.16,.22),(duration,0)])
    drive=curve(t,[(0.,0.),(.42,.32),(.63,.80),(.85,.92),(1.08,1.),(1.31,.95),(1.71,.60),(1.905,1.20),(2.15,.28),(duration,0.)])
    impact=0.;sway=0.;twist=0.;anticipation=0.
    for i,(start,contact) in enumerate(zip(CONTRACT['flurry']['strike_starts'],CONTRACT['flurry']['contacts'])):
        pulse=curve(t,[(start,0),(contact,.46),(contact+.029,1),
                      (contact+.10,.46),(contact+.19,-.13),(contact+.25,0)])
        impact+=pulse*(1.40 if i==4 else 1.)
        anticipation+=curve(t,[(start-.18,0),(start-.025,1),(contact,0)])*(1.3 if i==4 else 1.)
        if i<4:
            sign=-1 if i%2==0 else 1
            sway+=sign*curve(t,[(start-.16,0),(start,-.32),(contact+.035,1),(contact+.18,-.14),(contact+.25,0)])
            twist+=sign*.055*curve(t,[(start-.16,0),(start,-.5),(contact+.03,1),(contact+.22,0)])
    translate('body',(.070*sway,-.19*drive-.055*impact+.025*anticipation,.058*ready-.078*impact))
    rotate('body',(1,0,0),-.050*anticipation+.105*impact)
    rotate('body',(0,1,0),.092*sway)
    rotate('body',(0,0,1),.45*twist)
    translate('body_front',(.014*sway,-.055*drive,-.018*impact))
    rotate('body_front',(0,0,1),twist)
    rotate('body_rear',(0,1,0),-.047*sway)
    rotate('body_rear',(1,0,0),-.025*impact)
    rotate('maw',(1,0,0),-.032*impact)
    rotate('jaw_L',(0,0,1),-.11*ready);rotate('jaw_R',(0,0,1),.09*ready)

def pose_bite(t,duration):
    data=CONTRACT['bite'];start=data['windup_end'];contact=data['contact']
    load=curve(t,[(0,0),(.32,.85),(.41,1),(start,1,'strike'),(contact,0),(duration,0)])
    drive=curve(t,[(0,0),(start,0,'strike'),(contact,1),(.65,1),(.79,.18),(.94,.38),(1.12,.05),(duration,0)])
    gape=curve(t,[(0,0),(.29,.8),(.42,1),(start,1,'strike'),(contact,-.16),(.66,-.16),(.86,.10),(1.08,0),(duration,0)])
    tear=curve(t,[(0,0),(.64,0),(.77,1),(.94,-.24),(1.14,.08),(1.36,0),(duration,0)])
    translate('body',(.035*tear,.085*load-.30*drive,-.045*load-.062*drive))
    rotate('body',(1,0,0),-.080*load+.110*drive)
    rotate('body',(0,1,0),.050*tear)
    translate('body_front',(0,-.10*drive,-.015*drive))
    rotate('body_front',(0,0,1),.070*tear)
    rotate('body_rear',(0,1,0),-.030*tear)
    translate('maw',(0,-.14*drive,.035*load))
    rotate('maw',(1,0,0),-.13*load+.085*drive)
    rotate('maw',(0,1,0),.080*tear)
    rotate('jaw_L',(0,0,1),-.52*gape);rotate('jaw_R',(0,0,1),.48*gape)

manifest=dict(revision='CombatV28',fps=CONTRACT['fps'],source_note=CONTRACT['source_note'],clips={},
              ground_plane_metres=floor_z,palm_ankle_height_metres=palm_heights,gameplay_tested=False,rendered=False)
for role,key in [('Flurry','flurry'),('Bite','bite')]:
    duration=CONTRACT[key]['duration'];name='A_BoundCongregate_'+role+'V28'
    action=bpy.data.actions.new(name);action.use_fake_user=True
    rig.animation_data_create();rig.animation_data.action=action
    scene.frame_start,scene.frame_end=1,round(duration*scene.render.fps)+1
    previous={};min_support_fraction=1.
    for frame in range(1,scene.frame_end+1):
        scene.frame_set(frame);t=(frame-1)/scene.render.fps
        for bone in rig.pose.bones:
            bone.rotation_mode='QUATERNION';bone.matrix_basis=Matrix.Identity(4)
        if role=='Flurry':pose_flurry(t,duration)
        else:pose_bite(t,duration)
        min_support_fraction=min(min_support_fraction,constrain_support(role,t))
        for leg in recipe['legs']:
            goal=support_goal(leg,role,t);pitch=roll=lift=0.
            if role=='Flurry' and leg['name'] in ('L1','R1','L2','R2'):
                goal,pitch,roll,lift=forelimb(t,leg['name'],goal)
            leg_pose(leg,goal,pitch,roll,lift)
        for bone in rig.pose.bones:
            # Matrix decomposition can alternate q/-q. Component interpolation
            # between those equivalent rotations creates a 180-degree flip.
            q=bone.rotation_quaternion.copy();q.normalize()
            if bone.name in previous and previous[bone.name].dot(q)<0:q.negate()
            bone.rotation_quaternion=q;previous[bone.name]=q.copy()
            for channel in ('location','rotation_quaternion','scale'):bone.keyframe_insert(channel,frame=frame,group=bone.name)
    for layer in action.layers:
        for strip in layer.strips:
            for bag in strip.channelbags:
                for fcurve in bag.fcurves:
                    for k in fcurve.keyframe_points:
                        k.interpolation='BEZIER'
                        k.handle_left_type=k.handle_right_type='AUTO_CLAMPED'
    scene.frame_set(1);bpy.context.view_layer.update()
    bpy.ops.object.select_all(action='DESELECT');rig.select_set(True);bpy.context.view_layer.objects.active=rig
    path=OUT/(name+'.fbx')
    bpy.ops.export_scene.fbx(filepath=str(path),use_selection=True,object_types={'ARMATURE'},axis_forward='-Y',axis_up='Z',
        apply_unit_scale=True,apply_scale_options='FBX_SCALE_UNITS',add_leaf_bones=False,use_armature_deform_only=False,
        bake_anim=True,bake_anim_use_all_actions=False,bake_anim_use_nla_strips=False,bake_anim_simplify_factor=0,
        bake_anim_force_startend_keying=True,path_mode='STRIP')
    manifest['clips'][role]=dict(name=name,file=str(path),duration=duration,loop=False,min_support_motion_fraction=min_support_fraction)
rig.animation_data.action=None
for bone in rig.pose.bones:bone.matrix_basis.identity()
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'BoundCongregate_CombatV28.blend'))
(OUT/'motion_manifest.json').write_text(json.dumps(manifest,indent=2))
timing=CONTRACT['flurry']
header='#pragma once\n\n// Generated by author_combat_v28.py from CombatV28/motion_contract.json.\nnamespace BoundCongregateMeleeTiming\n{\n'
for suffix,field in [('Duration','duration'),('Contact','contact'),('TurnEnd','turn_end'),('WindupEnd','windup_end')]:
    header+=f'inline constexpr float Bite{suffix}={CONTRACT["bite"][field]}f;\n'
header+='inline constexpr float Contacts[]={'+','.join(f'{x}f' for x in timing['contacts'])+'};\n'
header+='inline constexpr float StrikeStarts[]={'+','.join(f'{x}f' for x in timing['strike_starts'])+'};\n'
limb_index={name:i for i,name in enumerate(('L1','R1','L2','R2'))}
masks=[sum(1<<limb_index[n] for n in (limbs if isinstance(limbs,list) else [limbs])) for limbs in timing['limbs']]
header+='inline constexpr uint8 LimbMasks[]={'+','.join(str(mask) for mask in masks)+'};\n'
header+=f'inline constexpr float FinisherRadiusBonus={timing["finisher_radius_bonus_cm"]}f;\n'
header+=f'inline constexpr float GroundDamageHeight={timing["damage_height_cm"]}f;\n'
header+=f'inline constexpr int HitCount={len(timing["contacts"])};\ninline constexpr float Duration={timing["duration"]}f;\ninline constexpr float TurnEnd={timing["turn_end"]}f;\n}}\n'
(PROJECT/'Source/FPSGAME/Monsters/BoundCongregateMeleeTiming.h').write_text(header)
print('BOUND_CONGREGATE_COMBAT_V28_AUTHORED',flush=True)
