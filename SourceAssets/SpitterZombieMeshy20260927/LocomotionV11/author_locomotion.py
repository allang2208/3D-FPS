"""Refine Walk_B, Walk_C and Run_A using their separate measured issues.

Keeps the Meshy skin and source style. No UE execution, test, or render.
The retained V7 prefix supplies only native sampling / original bind-length
conversion / FBX export helpers; none of its production loops are executed.
"""
import bpy,json,math,statistics
import numpy as np
from pathlib import Path
from mathutils import Matrix,Vector,Quaternion

ROOT=Path(__file__).resolve().parent;BASE=ROOT.parent;OUT=ROOT/'Final';OUT.mkdir(parents=True,exist_ok=True)
helper=BASE/'LibraryMotionV7/author_library_motion.py'
prefix=helper.read_text(encoding='utf-8').split("report={'movement':{}")[0]
ns={'__file__':str(helper),'__name__':'locomotion_source_helpers'}
exec(compile(prefix,str(helper),'exec'),ns)
rig=ns['rig'];meshes=ns['meshes'];scene=ns['scene'];bones=ns['bones']
rig.animation_data_clear();rig.animation_data_create()
ns['ROOT']=ROOT;ns['OUT']=OUT
apply=ns['apply'];sample=ns['sample'];wm=ns['wm'];point=ns['point']
move_hips=ns['move_hips'];set_rotation=ns['set_rotation'];aim=ns['aim'];mix=ns['mix']
FPS=60;SIDES=['Left','Right'];ROLES=['Walk_B','Walk_C','Run_A']
SETTINGS={
    'Walk_B':dict(pelvis_yaw=3.2,pelvis_roll=2.2,shift=.012,elbow=4.0,lag=1.15,head_weight=.80,head_filter=3,body_filter=2,contact_ramp=8),
    'Walk_C':dict(pelvis_yaw=4.0,pelvis_roll=2.0,shift=.012,elbow=5.0,lag=.90,head_weight=.70,head_filter=4,body_filter=2,contact_ramp=8),
    'Run_A':dict(pelvis_yaw=2.2,pelvis_roll=1.2,shift=.008,elbow=3.0,lag=.50,head_weight=.55,head_filter=5,body_filter=3,contact_ramp=6),
}

def smooth(x):
    x=max(0.,min(1.,x));return x*x*x*(x*(x*6-15)+10)

def quat_mean(qs):
    ref=qs[0];values=np.array([list(q if q.dot(ref)>=0 else -q) for q in qs])
    q=Quaternion(values.mean(axis=0));q.normalize();return q

def periodic_filter(values,radius):
    a=np.asarray(values,dtype=float);weights=np.array([radius+1-abs(i) for i in range(-radius,radius+1)],dtype=float)
    return sum(np.roll(a,i,axis=0)*w for i,w in zip(range(-radius,radius+1),weights))/weights.sum()

def filtered_quat(qs,i,radius):
    ref=qs[i];value=Vector((0.,0.,0.,0.))
    for step in range(-radius,radius+1):
        q=qs[(i+step)%len(qs)];weight=radius+1-abs(step)
        value+=Vector(q)*(weight if q.dot(ref)>=0 else -weight)
    return Quaternion(value).normalized()

# Restrict contact geometry to the foot/toe skin; clothing or fingertips must
# never move the whole body just because they are the lowest mesh vertex.
foot_vertices={}
for o in meshes:
    names={g.index:g.name for g in o.vertex_groups}
    foot_vertices[o.name]={side:[v.index for v in o.data.vertices
        if sum(g.weight for g in v.groups if names[g.group] in [side+'Foot',side+'ToeBase'])>.60] for side in SIDES}

def sole_heights():
    result={s:float('inf') for s in SIDES};deps=bpy.context.evaluated_depsgraph_get()
    for mesh in meshes:
        obj=mesh.evaluated_get(deps);skin=obj.to_mesh()
        try:
            for side in SIDES:
                result[side]=min(result[side],min((obj.matrix_world@skin.vertices[i].co).z for i in foot_vertices[mesh.name][side]))
        finally:obj.to_mesh_clear()
    return result

def solve_leg(side,target,pole,rotation):
    upper=side+'UpLeg';lower=side+'Leg';tip=side+'Foot'
    a=point(upper);b=point(lower);c=point(tip);l1=(b-a).length;l2=(c-b).length
    axis=(target-a).normalized();distance=max(abs(l1-l2)+.001,min((target-a).length,(l1+l2)*.995))
    across=pole-a-axis*(pole-a).dot(axis)
    if across.length<1e-5:across=Vector((0,-1,0))-axis*axis.dot(Vector((0,-1,0)))
    across.normalize();along=(l1*l1-l2*l2+distance*distance)/(2*distance)
    joint=a+axis*along+across*math.sqrt(max(0,l1*l1-along*along))
    aim(upper,b-a,joint-a);aim(lower,point(tip)-point(lower),a+axis*distance-point(lower));set_rotation(tip,rotation)

def contact_segments(mask,min_frames=5):
    n=len(mask);segments=[]
    for i in range(n):
        if mask[i] and not mask[(i-1)%n]:
            indices=[];j=i
            while mask[j%n] and len(indices)<n:indices.append(j);j+=1
            if len(indices)>=min_frames:segments.append(indices)
    return segments

def base_pose(role,t,seconds,drift,start,end):
    t=t%seconds;pose=sample(role,t)
    apply(pose);move_hips(Vector((-drift.x*t/seconds,-drift.y*t/seconds,0)))
    pose=ns['snapshot']()
    # Distribute endpoint mismatch over the whole cycle. V10's short fade to a
    # frozen midpoint stopped the head at the seam, then made it rush away.
    phase=t/seconds
    for name,m in pose.items():
        correction=start[name].to_quaternion()@end[name].to_quaternion().inverted()
        q=Quaternion().slerp(correction,phase)@m.to_quaternion()
        pos=m.translation+(start[name].translation-end[name].translation)*phase
        pose[name]=Matrix.LocRotScale(pos,q,m.to_scale())
    apply(pose)

report=dict(revision='LocomotionV11-20260929',movement={},mesh_or_skin_modified=False,
    runtime_tested=False,preview_rendered=False,
    helper_source=str(helper),speed_policy='authored_stride_speed_selected_once_per_spawn',
    fitting='foot-only contacts and two-bone IK; constant body height offset; source vertical motion retained',
    gaze='style-specific periodic head filtering and retained variation; no world-locked head')

for role in ROLES:
    cfg=SETTINGS[role];seconds=round(ns['metadata'][role]['seconds']*FPS)/FPS;n=round(seconds*FPS)
    rig.animation_data.action=None
    start=sample(role,0);end=sample(role,seconds)
    apply(start);p0=point('Hips').copy();apply(end);drift=point('Hips')-p0
    move_hips(Vector((-drift.x,-drift.y,0)));end=ns['snapshot']()
    raw=[];unfiltered=[]
    for i in range(n):
        base_pose(role,i/FPS,seconds,drift,start,end)
        unfiltered.append(ns['snapshot']())
    poses=[{} for i in range(n)]
    for name in unfiltered[0]:
        qs=[p[name].to_quaternion() for p in unfiltered]
        positions=periodic_filter([list(p[name].translation) for p in unfiltered],cfg['body_filter'])
        for i in range(n):
            poses[i][name]=Matrix.LocRotScale(Vector(positions[i]),filtered_quat(qs,i,cfg['body_filter']),unfiltered[i][name].to_scale())
    elbow_axes={side:[] for side in SIDES}
    for i in range(n):
        apply(poses[i])
        for side in SIDES:
            a=point(side+'Arm');b=point(side+'ForeArm');c=point(side+'Hand')
            axis=(b-a).cross(c-b)
            elbow_axes[side].append((axis.length,wm(side+'ForeArm').to_quaternion().inverted()@axis.normalized()))
        raw.append(dict(head=wm('Head').to_quaternion(),hip=point('Hips').copy(),sole=sole_heights(),
            feet={s:point(s+'Foot').copy() for s in SIDES},
            knees={s:point(s+'Leg').copy() for s in SIDES},
            foot_q={s:wm(s+'Foot').to_quaternion() for s in SIDES}))

    # Infer support windows from sole height and rearward travel, not ankle
    # height. Fit one clip speed from complete support intervals, then use that
    # speed for both planted trajectories and the actor's movement setting.
    contacts={};slopes=[]
    for side in SIDES:
        sole=np.array([r['sole'][side] for r in raw]);y=np.array([r['feet'][side].y for r in raw])
        vy=(np.roll(y,-1)-np.roll(y,1))*FPS*.5
        floor=float(np.percentile(sole,8));limit=.07 if role=='Run_A' else .085
        mask=(sole<floor+limit)&(vy>(.12 if role=='Run_A' else .06))
        if role=='Run_A':
            # A rearward-travelling airborne foot must not become a second
            # planted contact just because its rotating toe drops briefly.
            ankle=np.array([r['feet'][side].z for r in raw])
            mask &= ankle < float(np.percentile(ankle,8))+.065
        # Fill only sub-50ms detection chatter, not the real swing phase.
        for gap in contact_segments(~mask,1):
            if len(gap)<=3:
                for j in gap:mask[j%n]=True
        segments=contact_segments(mask)
        if not segments:raise RuntimeError('No support intervals for '+role+' '+side)
        for indices in segments:
            ts=np.array(indices)/FPS;ys=y[np.array(indices)%n]
            slopes.append(float(np.polyfit(ts,ys,1)[0]))
        weights=np.zeros(n)
        for indices in segments:
            for j,index in enumerate(indices):weights[index%n]=min(smooth((j+1)/cfg['contact_ramp']),smooth((len(indices)-j)/cfg['contact_ramp']))
        contacts[side]=dict(segments=segments,weights=weights,floor=floor)
    speed=statistics.median(slopes)
    if speed<=0:raise RuntimeError('Support fitting produced non-forward speed')
    # A single vertical fit keeps source hip bob and run flight. Foot IK handles
    # contact changes, rather than lifting the pelvis with each lowest vertex.
    height_offset=.003-statistics.mean(c['floor'] for c in contacts.values())-.008
    targets={s:[raw[i]['feet'][s]+Vector((0,0,height_offset)) for i in range(n)] for s in SIDES}
    for side in SIDES:
        for indices in contacts[side]['segments']:
            center=statistics.mean(indices);center_y=statistics.mean(raw[i%n]['feet'][side].y for i in indices)
            center_x=statistics.mean(raw[i%n]['feet'][side].x for i in indices)
            for index in indices:
                i=index%n;w=contacts[side]['weights'][i]
                targets[side][i].x=targets[side][i].x*(1-w)+center_x*w
                targets[side][i].y=targets[side][i].y*(1-w)+(center_y+speed*(index-center)/FPS)*w
        for i in range(n):
            w=contacts[side]['weights'][i];bottom=raw[i]['sole'][side]+height_offset
            desired=max(.003,bottom)*(1-w)+.003*w
            targets[side][i].z+=desired-bottom

    # Bias the mean face toward the target while retaining source nod/roll.
    head_mean=quat_mean([r['head'] for r in raw]);mean_hip=sum((r['hip'] for r in raw),Vector())/n
    head_curve=[filtered_quat([r['head'] for r in raw],i,cfg['head_filter']) for i in range(n)]
    # Choose the bend plane in local bone space from the most clearly flexed
    # source pose. Recomputing a cross product near a straight elbow flips it.
    bend_axes={side:max(elbow_axes[side],key=lambda p:p[0])[1] for side in SIDES}
    face=head_mean@(ns['head_rest'].to_quaternion().inverted()@ns['rest_front'])
    target_direction=Vector((0,-4,.10)).normalized()
    facing_bias=face.rotation_difference(target_direction)
    centered_head=facing_bias@head_mean
    separation=np.array([r['feet']['Right'].y-r['feet']['Left'].y for r in raw])
    gait=periodic_filter(separation/max(.001,float(np.max(np.abs(separation)))),4)
    support=periodic_filter(contacts['Left']['weights']-contacts['Right']['weights'],6)
    fitted=[]
    for i in range(n):
        apply(poses[i]);move_hips(Vector((float(support[i])*cfg['shift'],0,height_offset)))
        yaw=math.radians(cfg['pelvis_yaw']*float(gait[i]));roll=math.radians(cfg['pelvis_roll']*float(support[i]))
        set_rotation('Hips',Quaternion((0,0,1),yaw)@Quaternion((0,-1,0),roll)@wm('Hips').to_quaternion())
        set_rotation('Spine',Quaternion((0,0,1),-yaw*.55)@wm('Spine').to_quaternion())
        # Local rotations keep the shoulder's body-driven movement; increasing
        # delay down the arm supplies follow-through without pushing hands out.
        for side in SIDES:
            for part,delay,amount in [('Arm',.025,.30),('ForeArm',.055,.60),('Hand',.085,.65)]:
                b=rig.pose.bones[side+part];lag=delay*cfg['lag']*FPS
                frame=(i-lag)%n;lo=int(frame);hi=(lo+1)%n
                delayed=poses[lo][b.name].to_quaternion().slerp(poses[hi][b.name].to_quaternion(),frame-lo)
                q=b.matrix_basis.to_quaternion().slerp(delayed,amount)
                b.matrix_basis=Matrix.LocRotScale(b.matrix_basis.translation,q,b.matrix_basis.to_scale())
            ns['update']()
            q=wm(side+'ForeArm').to_quaternion();axis=q@bend_axes[side]
            phase=float(gait[i])*(1 if side=='Left' else -1)
            bend=math.radians(cfg['elbow']*(.5+.5*phase))
            set_rotation(side+'ForeArm',Quaternion(axis,bend)@q)
        # Run has its own head damping instead of inheriting the walk value.
        neck=wm('neck').to_quaternion();set_rotation('neck',Quaternion().slerp(facing_bias,.12)@neck)
        desired=facing_bias@head_curve[i];set_rotation('Head',centered_head.slerp(desired,cfg['head_weight']))
        for side in SIDES:
            pole=raw[i]['knees'][side]+Vector((0,0,height_offset))
            solve_leg(side,targets[side][i],pole,raw[i]['foot_q'][side])
        fitted.append(ns['snapshot']())

    name='A_Spitter_LocomotionV11_'+role;action=ns['new_action'](name,FPS,seconds);previous={}
    for frame in range(n+1):
        scene.frame_set(frame);apply(fitted[frame%n]);ns['key_pose'](frame,previous)
    entry=ns['export'](name,action,FPS,True,ns['metadata'][role]['source']+'; original Meshy skin; LocomotionV11 per-style contact, bend-plane and cycle fitting')
    entry.update(reference_speed_cm_s=round(speed*100,3),actor_walk_speed_cm_s=round(speed*100,3),
        body_height_offset_cm=round(height_offset*100,3),settings=cfg,
        support_intervals={s:[[round(indices[0]/FPS,4),round((indices[-1]+1)/FPS,4)] for indices in contacts[s]['segments']] for s in SIDES})
    report['movement'][role]=entry
    print('SPITTER_LOCOMOTION_V11_AUTHORED',role,json.dumps(entry),flush=True)

ns['active'](bpy.data.actions['A_Spitter_LocomotionV11_Walk_B']);scene.frame_start=0
scene.frame_end=round(report['movement']['Walk_B']['seconds']*FPS);scene.frame_set(0)
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'SpitterZombie_LocomotionV11.blend'))
(ROOT/'authoring.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print('SPITTER_LOCOMOTION_V11_COMPLETE',flush=True)
