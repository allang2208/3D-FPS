"""Keep Rampage's coupled body motion; fit original legs to explicit planted feet."""
import bpy,json,math,numpy as np
from pathlib import Path
from mathutils import Matrix,Vector,Quaternion
BASE=Path(__file__).resolve().parents[1];P=BASE/'V18CoupledLocomotion'
for f in ['Records','Motion','Authoring']:(P/f).mkdir(parents=True,exist_ok=True)
data=json.loads((BASE/'RecoveryInputs/RampageBiped/Motion/native_walk.json').read_text())
src=json.loads((BASE/'RecoveryInputs/RampageBiped/Source/rampage_biped_source.json').read_text())
def mat(v):return Matrix.LocRotScale(Vector(v['p']),Quaternion((v['q'][3],*v['q'][:3])),Vector(v['s']))
ref={n:mat(v) for n,v in data['reference'].items()};inv={n:m.inverted() for n,m in ref.items()}
parents={n:p if p in ref else None for n,p in data['parents'].items()}
def depth(n):return 1+depth(parents[n]) if parents[n] else 0
order=sorted(ref,key=depth);root=order[0]
def is_child(n,a):return n==a or (parents[n] is not None and is_child(parents[n],a))
children={n:[b for b in order if is_child(b,n)] for n in order}
local_ref={n:mat(v) for n,v in data['reference_local'].items()}
native=[]
for r in data['frames']:
    p={n:mat(v) for n,v in r.items()};align=ref[root]@p[root].inverted()
    native.append({n:align@m for n,m in p.items()})
local=[{n:p[parents[n]].inverted()@p[n] if parents[n] else ref[n] for n in order} for p in native]
def sample(phase):
    f=(phase%1)*(len(local)-1);a=int(f);b=min(a+1,len(local)-1);t=f-a;pose={}
    for n in order:
        x,y=local[a][n],local[b][n]
        m=Matrix.LocRotScale(x.translation.lerp(y.translation,t),x.to_quaternion().slerp(y.to_quaternion(),t),local_ref[n].to_scale())
        pose[n]=pose[parents[n]]@m if parents[n] else ref[n].copy()
    return pose
def rotate(pose,bone,q):
    pivot=pose[bone].translation;D=Matrix.Translation(pivot)@q.to_matrix().to_4x4()@Matrix.Translation(-pivot)
    for n in children[bone]:pose[n]=D@pose[n]
def move(pose,bone,offset):
    for n in children[bone]:pose[n].translation+=offset
def set_rotation(pose,bone,q):rotate(pose,bone,q@pose[bone].to_quaternion().inverted())
def smooth(x):
    x=max(0.,min(1.,x));return x*x*x*(10.-15.*x+6.*x*x)
bpy.ops.wm.open_mainfile(filepath=str(BASE/'V14BareBodyHand/Authoring/NightWarden_BareBody_HandRepair_V14.blend'))
bpy.context.preferences.filepaths.save_version=0
body=bpy.data.objects['NW14_CompleteBody_HandRepair'];rig=next(o for o in bpy.context.scene.objects if o.type=='ARMATURE')
C=Matrix(((0,-100,0,0),(-100,0,0,0),(0,0,100,0),(0,0,0,1)));invC=C.inverted()
groups={g.index:g.name for g in body.vertex_groups};soles={};points={};inputs={}
for side,foot in [('L','Bone_008'),('R','Bone_013')]:
    family=set(children[foot]);rows=[]
    for v in body.data.vertices:
        w={groups[g.group]:g.weight for g in v.groups if groups[g.group] in ref and g.weight>1e-6}
        if sum(w.get(n,0.) for n in family)>.6:rows.append((C@(body.matrix_world@v.co),w))
    cut=np.percentile([p.z for p,w in rows],10)+.8;rows=[(p,w) for p,w in rows if p.z<=cut]
    soles[side]=rows;points[side]=np.array([p for p,w in rows])
    inputs[side]={}
    for n in order:
        w=np.array([weights.get(n,0.)/sum(weights.values()) for p,weights in rows])
        if np.any(w):inputs[side][n]=(np.c_[points[side],np.ones(len(rows))]@np.array(inv[n]).T)*w[:,None]
def skin(pose,side):return sum(v@np.array(pose[n]).T for n,v in inputs[side].items())[:,:3]
legs={'L':('Bone_010','Bone_009','Bone_008','Bone_007'),'R':('Bone_015','Bone_014','Bone_013','Bone_012')}
lengths={s:((ref[k].translation-ref[h].translation).length,(ref[f].translation-ref[k].translation).length) for s,(h,k,f,t) in legs.items()}
duration=1.4;fps=60;count=85;stance=.56;starts={'L':.78,'R':.28}
stride=float(np.mean([sum(v) for v in lengths.values()]))*1.60;speed=stride/duration
# Lateral pelvis motion is fitted by hip width, not by the donor's height alone.
source_width=(Vector(src['reference']['thigh_l']['p'])-Vector(src['reference']['thigh_r']['p'])).length
target_width=(ref['Bone_010'].translation-ref['Bone_015'].translation).length
lateral_scale=target_width/source_width
hip_mean=sum((p['Bone_001'].translation for p in native[:-1]),Vector())/(len(native)-1)
# One chest-space neck correction preserves all cyclic neck/torso rotations.
chest='Bone_002';neck='Bone_018';head='Bone_016'
v=sum(((p[chest].to_quaternion().inverted()@(p[head].translation-p[neck].translation)).normalized() for p in native[:-1]),Vector()).normalized()
target=(ref[chest].to_quaternion().inverted()@(ref[head].translation-ref[neck].translation)).normalized()
neck_correction=v.rotation_difference(target)
swing_profiles={}
for side,origin in [('L',.10),('R',.62)]:
    values=np.array([float(skin(sample(origin+s*.80),side)[:,2].min()) for s in np.linspace(0.,1.,101)])
    values-=np.linspace(values[0],values[-1],101)
    swing_profiles[side]=np.maximum(values,0.)/max(1.,float(values.max()))
poses=[];goals=[];weights={'L':[],'R':[]};phases={'L':[],'R':[]};contacts=[]
for i in range(count):
    phase=i/(count-1);pose=sample(phase)
    old=pose['Bone_001'].translation.copy();new=old.copy()
    new.x+=ref['Bone_001'].translation.x-hip_mean.x
    new.y=ref['Bone_001'].translation.y+(old.y-hip_mean.y)*lateral_scale
    new.z=hip_mean.z+(old.z-hip_mean.z)*.55
    move(pose,'Bone_000',new-old)
    q=pose[chest].to_quaternion();rotate(pose,neck,q@neck_correction@q.inverted())
    goal={};contact={}
    for side,(h,k,f,toe) in legs.items():
        u=(phase-starts[side])%1.;phases[side].append(u)
        in_stance=u<stance;flat=ref[f].to_quaternion()
        if in_stance:
            x=stride*(stance*.5-u);lift=0.;rotation=flat;blend=0.
        else:
            s=(u-stance)/(1-stance)
            x=-stride*stance*.5-stride*(1-stance)*s+stride*smooth(s)
            # Preserve the source swing's uneven vertical arc, with walking clearance.
            origin=.10 if side=='L' else .62
            swing=sample(origin+s*.80)
            lift=18.*float(np.interp(s,np.linspace(0.,1.,101),swing_profiles[side]))*smooth(s/.12)*smooth((1-s)/.12)
            lift=max(lift,10.*math.sin(math.pi*s)**2)
            blend=smooth(s/.18)*smooth((1-s)/.18)
            rotation=flat.slerp(swing[f].to_quaternion(),blend*.70)
        for n in children[f]:
            if n!=f:
                q0=local_ref[n].to_quaternion();qn=(pose[parents[n]].inverted()@pose[n]).to_quaternion()
                set_rotation(pose,n,pose[parents[n]].to_quaternion()@q0.slerp(qn,blend))
        desired=ref[f].translation.copy();desired.x+=x
        desired.z+=.30-float(points[side][:,2].min())+lift
        goal[side]=(desired,rotation)
        contact[side]=(Vector((float(points[side][:,0].mean())+x,float(points[side][:,1].mean()),0.)),.30+lift)
        # Curves are also used by the runtime contact layer during turning/blending.
        weights[side].append(smooth(u/.045)*smooth((stance-u)/.045) if in_stance else 0.)
    goals.append(goal);poses.append(pose);contacts.append(contact)
# Lower only when the original bone lengths need room; never stretch a limb.
caps=[];wanted=[]
for pose,goal in zip(poses,goals):
    cap=10000.
    for side,(h,k,f,t) in legs.items():
        dest=goal[side][0];origin=pose[h].translation;reach=sum(lengths[side])*.975
        horizontal=(dest-origin).to_2d().length
        cap=min(cap,dest.z+math.sqrt(max(1.,reach*reach-horizontal*horizontal))-(origin.z-pose['Bone_001'].translation.z))
    caps.append(cap);wanted.append(min(pose['Bone_001'].translation.z,cap))
z=np.array(wanted[:-1]);filtered=sum(np.roll(z,i)*w for i,w in [(-2,1/9),(-1,2/9),(0,3/9),(1,2/9),(2,1/9)])
filtered=np.minimum(filtered,np.array(caps[:-1]));filtered=np.r_[filtered,filtered[0]]
def solve_leg(pose,side,dest,rotation):
    h,k,f,toe=legs[side];p0=pose[h].translation.copy();p1=pose[k].translation.copy();p2=pose[f].translation.copy()
    l1,l2=lengths[side];direction=dest-p0;distance=direction.length
    if distance>l1+l2-.01:raise RuntimeError('Unreachable foot target '+side+' '+str(distance))
    direction.normalize();pole=p1-p0;pole-=direction*pole.dot(direction)
    if pole.length<.1:pole=Vector((1,0,0));pole-=direction*pole.dot(direction)
    pole.normalize();along=(l1*l1-l2*l2+distance*distance)/(2*distance)
    knee=p0+direction*along+pole*math.sqrt(max(0.,l1*l1-along*along))
    rotate(pose,h,(p1-p0).rotation_difference(knee-p0))
    rotate(pose,k,(pose[f].translation-pose[k].translation).rotation_difference(dest-pose[k].translation))
    set_rotation(pose,f,rotation)
for i,(pose,goal) in enumerate(zip(poses,goals)):
    move(pose,'Bone_000',Vector((0,0,float(filtered[i])-pose['Bone_001'].translation.z)))
    for side in legs:
        dest,q=goal[side];dest=dest.copy();target_center,target_height=contacts[i][side]
        # Solve for the actual skinned sole, including small calf weights and
        # toe roll, rather than assuming the ankle is the ground contact.
        for correction in range(4):
            solve_leg(pose,side,dest,q);surface=skin(pose,side)
            delta=Vector((target_center.x-float(surface[:,0].mean()),target_center.y-float(surface[:,1].mean()),target_height-float(surface[:,2].min())))
            if delta.length<.002:break
            dest+=delta
poses[-1]={n:m.copy() for n,m in poses[0].items()}
for side in weights:weights[side][-1]=weights[side][0]
keys={n:[] for n in order};previous={}
for pose in poses:
    for n in order:
        m=pose[parents[n]].inverted()@pose[n] if parents[n] else ref[n];p,q,s=m.decompose()
        if n in previous and q.dot(previous[n])<0:q.negate()
        previous[n]=q.copy();keys[n].append({'p':list(p),'q':[q.x,q.y,q.z,q.w],'s':list(local_ref[n].to_scale())})
(P/'Motion/coupled_keys.json').write_text(json.dumps({'fps':fps,'frames':count,'duration':duration,'keys':keys,'plant_curves':weights}),encoding='utf-8')
rig.animation_data_clear();rig.animation_data_create();rig.data.pose_position='POSE'
action=bpy.data.actions.new('A_NightWarden_CoupledStride_V18');rig.animation_data.action=action;action.use_fake_user=True
rest_bl={b.name:rig.matrix_world@b.matrix_local for b in rig.data.bones};previous={}
for i,pose in enumerate(poses,1):
    desired={n:invC@pose[n]@inv[n]@C@rest_bl[n] for n in rest_bl}
    for pb in sorted(rig.pose.bones,key=lambda b:len(b.bone.parent_recursive)):
        n=pb.name;par=pb.parent
        m=pb.bone.convert_local_to_pose(desired[n],pb.bone.matrix_local,parent_matrix=desired[par.name] if par else Matrix.Identity(4),parent_matrix_local=par.bone.matrix_local if par else Matrix.Identity(4),invert=True)
        p,q,s=m.decompose()
        if n in previous and q.dot(previous[n])<0:q.negate()
        previous[n]=q.copy();pb.rotation_mode='QUATERNION';pb.location=p;pb.rotation_quaternion=q;pb.scale=s
        for channel in ['location','rotation_quaternion','scale']:pb.keyframe_insert(channel,frame=i,group=n)
bpy.context.scene.render.fps=fps;bpy.context.scene.frame_start=1;bpy.context.scene.frame_end=count;bpy.context.scene.frame_set(1)
bpy.ops.wm.save_as_mainfile(filepath=str(P/'Authoring/NightWarden_CoupledStride_V18.blend'))
report={'stage':'coupled_body_and_contact_stride_authored','source_asset':src['asset'],'duration_s':duration,'fps':fps,'frames':count,'nominal_speed_cm_s':speed,
    'stride_length_cm':stride,'stance_fraction':stance,'stance_starts':starts,'lateral_pelvis_scale':lateral_scale,
    'upper_body':'Original native shoulder/spine/arm timing and rotations; single constant chest-space neck alignment',
    'leg_method':'Original bone lengths and animated knee plane; stationary world-space sole during stance; source-shaped swing',
    'independent_arm_delay':False,'per_spine_bone_mean_replacement':False,'body_or_weights_changed':False,'game_tested':False}
(P/'Records/motion_manifest.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('NW18_COUPLED_AUTHORED '+json.dumps(report),flush=True)
