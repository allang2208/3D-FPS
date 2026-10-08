"""Baked load/release/impact/recoil on the existing V14 rig, in metres.

Support constraints and quaternion hemisphere continuity are solved offline.
The same seconds contract generates animation and native hit-window timings.
"""
from pathlib import Path
import bpy, json, math
from mathutils import Matrix, Vector, Quaternion

PROJECT=Path('D:/FPS3D/FPSGAME')
ROOT=PROJECT/'SourceAssets/BoundCongregateMeshy20261006'
OUT=ROOT/'MeleeV17'
CONTRACT=json.loads((OUT/'motion_contract.json').read_text())
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'GarmentContinuityV14/BoundCongregate_GarmentContinuityV14.blend'))
rig=next(o for o in bpy.context.scene.objects if o.type=='ARMATURE')
scene=bpy.context.scene
scene.render.fps=CONTRACT['fps']
recipe=json.loads((ROOT/'Authoring/rig_recipe.json').read_text())
rest={b.name:b.matrix_local.copy() for b in rig.data.bones}
pose={}

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

def segment(name,head,tail,rest_normal=None,pose_normal=None):
    direction=rig.data.bones[name].tail_local-rig.data.bones[name].head_local
    if rest_normal is not None:
        # Map the complete hinge frame, including twist. A shortest-arc
        # direction-only rotation becomes unstable near opposite directions.
        y0,y1=direction.normalized(),(tail-head).normalized()
        x0,x1=rest_normal.normalized(),pose_normal.normalized()
        basis0=Matrix((x0,y0,x0.cross(y0))).transposed()
        basis1=Matrix((x1,y1,x1.cross(y1))).transposed()
        rotation=basis1@basis0.transposed()
    else:rotation=direction.rotation_difference(tail-head).to_matrix()
    matrix=rotation.to_4x4()@rest[name]
    matrix.translation=head
    assign(name,matrix)

def stance(leg):
    hip,_,ankle,_=[point(p) for p in leg['points']]
    return ankle+Vector((hip.x-ankle.x,hip.y-ankle.y,0))*.18

def constrain_support(role):
    """Limit torso excursion instead of dragging a planted sole after IK clamps."""
    channels={n:rig.pose.bones[n].matrix_basis.copy() for n in ('body','body_front')}
    def set_fraction(fraction):
        for n,matrix in channels.items():
            p,q,s=matrix.decompose()
            rig.pose.bones[n].matrix_basis=Matrix.LocRotScale(p*fraction,Quaternion().slerp(q,fraction),s)
        refresh()
    def reachable():
        for leg in recipe['legs']:
            if role=='Flurry' and leg['name'] in ('L1','R1'):continue
            upper='leg_'+leg['name']+'_upper'
            parent=rig.data.bones[upper].parent.name
            hip,knee,ankle,_=[point(p) for p in leg['points']]
            start=pose[parent]@rest[parent].inverted()@hip
            a,b=(knee-hip).length,(ankle-knee).length
            if not abs(a-b)+.003<=(stance(leg)-start).length<=(a+b)*.966:return False
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

def leg_pose(leg,goal,palm_pitch=0.,palm_roll=0.,lift=0.):
    upper,lower,foot=['leg_'+leg['name']+'_'+suffix for suffix in ('upper','lower','foot')]
    hip,knee,ankle,_=[point(p) for p in leg['points']]
    parent=rig.data.bones[upper].parent.name
    delta=pose[parent]@rest[parent].inverted()
    start,old_knee=delta@hip,delta@knee
    a,b=(knee-hip).length,(ankle-knee).length
    direction=(goal-start).normalized()
    distance=max(abs(a-b)+.002,min((goal-start).length,(a+b)*.97))
    pole=old_knee-start
    if lift>0:
        # Keep the lifting elbow outside the torso. Projecting only its rest
        # knee vector becomes singular when the raised wrist passes that ray.
        outward=Vector((-1 if leg['name'][0]=='L' else 1,0,.25)).normalized()
        pole=pole.normalized().lerp(delta.to_3x3()@outward,lift)
    pole-=direction*pole.dot(direction)
    if pole.length<.001:pole=Vector((0,0,1))-direction*direction.z
    along=(a*a-b*b+distance*distance)/(2*distance)
    joint=start+direction*along+pole.normalized()*math.sqrt(max(0,a*a-along*along))
    end=start+direction*distance
    rest_normal=(knee-hip).cross(ankle-knee).normalized()
    pose_normal=(joint-start).cross(end-joint).normalized()
    segment(upper,start,joint,rest_normal,pose_normal)
    segment(lower,joint,end,rest_normal,pose_normal)
    matrix=Quaternion((1,0,0),palm_pitch).to_matrix().to_4x4()@Quaternion((0,1,0),palm_roll).to_matrix().to_4x4()@rest[foot]
    matrix.translation=end;assign(foot,matrix)

def forelimb(t,side,base):
    sign=-1 if side=='L1' else 1
    ready=Vector((sign*.60,-1.13 if sign<0 else -.98,1.37))
    # Lift along an outward arc, not a straight line through the shoulder.
    # The short upper / long lower right donor otherwise folds almost 180 deg.
    clearance=Vector((sign*.72,-1.55 if sign<0 else -1.49,.66))
    lifted=Vector((sign*.74,-1.34 if sign<0 else -1.27,1.30))
    positions=[(0.,base),(.12,clearance),(.23,lifted),(.30,ready)]
    pitches=[(0.,0.),(.30,-.18)]
    data=CONTRACT['flurry']
    for i,(start,contact) in enumerate(zip(data['strike_starts'],data['contacts'])):
        if i<4 and (i%2==0)!=(sign<0):continue
        heavy=i==4
        top=ready+Vector((sign*.07,.06,.19 if heavy else .07))
        hit=Vector((sign*.20,-2.02 if sign<0 else -1.90,.57 if heavy else .70))
        low=hit+Vector((0,-.012,-.07 if heavy else -.045))
        # One continuous schedule; the recovering hand feeds its next load arc.
        prepared=start-(.055 if i<2 or heavy else .025)
        positions.extend([(prepared,top),(start,top,'strike'),(contact,hit),
            (contact+data['contact_hold_seconds'],hit),(contact+.075,low)])
        pitches.extend([(prepared,-.32),(start,-.32,'strike'),(contact,.17),
            (contact+data['contact_hold_seconds'],.17),(contact+.075,.23)])
        if heavy:
            # Finish toward support instead of snapping both arms back overhead.
            positions.extend([(contact+.26,clearance),(data['duration'],base)])
            pitches.extend([(contact+.26,.05),(data['duration'],0.)])
        else:
            positions.extend([(contact+.17,clearance),(contact+.25,lifted)])
            pitches.extend([(contact+.17,.10),(contact+.25,-.25)])
    active=curve(t,[(0,0),(.30,1),(1.86,1),(data['duration'],0)])
    return curve(t,positions),curve(t,pitches),sign*.055*active

manifest=dict(revision='MeleeV17',fps=CONTRACT['fps'],source_note=CONTRACT['source_note'],clips={})
for role,key in [('Bite','bite'),('Flurry','flurry')]:
    duration=CONTRACT[key]['duration'];name='A_BoundCongregate_'+role+'V17'
    action=bpy.data.actions.new(name);action.use_fake_user=True
    rig.animation_data_create();rig.animation_data.action=action
    scene.frame_start,scene.frame_end=1,round(duration*scene.render.fps)+1
    previous={};min_support_fraction=1.
    for frame in range(1,scene.frame_end+1):
        scene.frame_set(frame);t=(frame-1)/scene.render.fps
        for bone in rig.pose.bones:
            bone.rotation_mode='QUATERNION';bone.matrix_basis=Matrix.Identity(4)
        if role=='Bite':
            load=curve(t,[(0,0),(.39,1),(.48,1,'strike'),(.56,0),(duration,0)])
            drive=curve(t,[(0,0),(.48,0,'strike'),(.56,1),(.60,1),(.73,-.17),(.94,.16),(duration,0)])
            gape=curve(t,[(0,0),(.39,1),(.48,1,'strike'),(.56,-.26),(.64,-.26),(.95,0),(duration,0)])
            tear=curve(t,[(0,0),(.60,0),(.75,1),(.93,-.22),(1.18,0),(duration,0)])
            translate('body',(0,.055*load-.13*drive,-.024*load-.027*drive))
            rotate('body',(1,0,0),-.045*load+.055*drive)
            translate('body_front',(0,-.045*drive,0));rotate('body_front',(0,0,1),.038*tear)
            translate('maw',(0,-.045*drive,0));rotate('maw',(1,0,0),-.07*load+.045*drive)
            rotate('maw',(0,1,0),.045*tear)
            rotate('jaw_L',(0,0,1),-.32*gape);rotate('jaw_R',(0,0,1),.28*gape)
        else:
            ready=curve(t,[(0,0),(.34,1),(1.68,1),(duration,0)])
            impact=0.;roll=0.
            for i,(start,contact) in enumerate(zip(CONTRACT[key]['strike_starts'],CONTRACT[key]['contacts'])):
                pulse=curve(t,[(start,0,'strike'),(contact,1),(contact+.035,1),(contact+.15,-.2),(contact+.20,0)])
                impact+=pulse*(1.35 if i==4 else 1.)
                if i<4:roll+=pulse*(.032 if i%2==0 else -.032)
            translate('body',(0,-.05*ready-.10*impact,.035*ready-.045*impact))
            rotate('body',(1,0,0),-.035*ready+.067*impact);rotate('body',(0,1,0),roll)
            rotate('body_front',(0,0,1),-.5*roll)
            rotate('jaw_L',(0,0,1),-.07*ready);rotate('jaw_R',(0,0,1),.06*ready)
        min_support_fraction=min(min_support_fraction,constrain_support(role))
        for leg in recipe['legs']:
            goal=stance(leg);pitch=roll=lift=0.
            if role=='Flurry' and leg['name'] in ('L1','R1'):
                goal,pitch,roll=forelimb(t,leg['name'],goal)
                lift=curve(t,[(0,0),(.26,1),(1.86,1),(duration,0)])
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
                    for k in fcurve.keyframe_points:k.interpolation='LINEAR'
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
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'BoundCongregate_MeleeV17.blend'))
(OUT/'motion_manifest.json').write_text(json.dumps(manifest,indent=2))
timing=CONTRACT['flurry']
header='#pragma once\n\n// Generated by author_melee_v17.py from MeleeV17/motion_contract.json.\nnamespace BoundCongregateMeleeTiming\n{\n'
for suffix,field in [('Duration','duration'),('Contact','contact'),('TurnEnd','turn_end'),('WindupEnd','windup_end')]:
    header+=f'inline constexpr float Bite{suffix}={CONTRACT["bite"][field]}f;\n'
header+='inline constexpr float Contacts[]={'+','.join(f'{x}f' for x in timing['contacts'])+'};\n'
header+='inline constexpr float StrikeStarts[]={'+','.join(f'{x}f' for x in timing['strike_starts'])+'};\n'
header+=f'inline constexpr int HitCount={len(timing["contacts"])};\ninline constexpr float Duration={timing["duration"]}f;\ninline constexpr float TurnEnd={timing["turn_end"]}f;\n}}\n'
(PROJECT/'Source/FPSGAME/Monsters/BoundCongregateMeleeTiming.h').write_text(header)
print('BOUND_CONGREGATE_MELEE_V17_AUTHORED',flush=True)
