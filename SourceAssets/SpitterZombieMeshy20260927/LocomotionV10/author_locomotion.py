"""Author four contact-fitted locomotion clips from clean native source motion.

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
FPS=60;SIDES=['Left','Right'];ROLES=['Walk_A','Walk_B','Walk_C','Run_A']
SETTINGS={
    'Walk_A':dict(pelvis_yaw=3.8,pelvis_roll=2.4,shift=.012,elbow=5.0,lag=1.0),
    'Walk_B':dict(pelvis_yaw=3.2,pelvis_roll=2.8,shift=.014,elbow=4.0,lag=1.15),
    'Walk_C':dict(pelvis_yaw=4.5,pelvis_roll=2.2,shift=.011,elbow=5.5,lag=.85),
    'Run_A':dict(pelvis_yaw=2.2,pelvis_roll=1.4,shift=.008,elbow=3.0,lag=.65),
}

def smooth(x):
    x=max(0.,min(1.,x));return x*x*x*(x*(x*6-15)+10)

def quat_mean(qs):
    ref=qs[0];values=np.array([list(q if q.dot(ref)>=0 else -q) for q in qs])
    q=Quaternion(values.mean(axis=0));q.normalize();return q

def periodic_filter(values,radius):
    a=np.asarray(values,dtype=float);weights=np.array([radius+1-abs(i) for i in range(-radius,radius+1)],dtype=float)
    return sum(np.roll(a,i,axis=0)*w for i,w in zip(range(-radius,radius+1),weights))/weights.sum()

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

def contact_segments(mask):
    n=len(mask);segments=[]
    for i in range(n):
        if mask[i] and not mask[(i-1)%n]:
            indices=[];j=i
            while mask[j%n] and len(indices)<n:indices.append(j);j+=1
            if len(indices)>=5:segments.append(indices)
    return segments

def base_pose(role,t,seconds,drift,start,end):
    t=t%seconds;pose=sample(role,t)
    apply(pose);move_hips(Vector((-drift.x*t/seconds,-drift.y*t/seconds,0)))
    pose=ns['snapshot']()
    # Distribute the small seam correction over both sides of the boundary.
    # Secondary limb delays therefore read the same continuous periodic input.
    width=.10 if role=='Run_A' else .14
    if t<width:pose=mix(pose,mix(start,end,.5),1-smooth(t/width))
    elif t>seconds-width:pose=mix(pose,mix(start,end,.5),smooth((t-seconds+width)/width))
    apply(pose)

report=dict(revision='LocomotionV10-20260928',movement={},mesh_or_skin_modified=False,
    runtime_tested=False,preview_rendered=False,
    helper_source=str(helper),speed_policy='authored_stride_speed_selected_once_per_spawn',
    fitting='foot-only contacts and two-bone IK; constant body height offset; source vertical motion retained',
    gaze='clip-mean facing bias with 80 percent source head variation; no world-locked head')

for role in ROLES:
    cfg=SETTINGS[role];seconds=round(ns['metadata'][role]['seconds']*FPS)/FPS;n=round(seconds*FPS)
    rig.animation_data.action=None
    start=sample(role,0);end=sample(role,seconds)
    apply(start);p0=point('Hips').copy();apply(end);drift=point('Hips')-p0
    move_hips(Vector((-drift.x,-drift.y,0)));end=ns['snapshot']()
    raw=[];poses=[]
    for i in range(n):
        base_pose(role,i/FPS,seconds,drift,start,end)
        poses.append(ns['snapshot']())
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
        floor=float(np.percentile(sole,8));limit=.06 if role=='Run_A' else .045
        mask=(sole<floor+limit)&(vy>(.12 if role=='Run_A' else .06))
        segments=contact_segments(mask)
        if not segments:raise RuntimeError('No support intervals for '+role+' '+side)
        for indices in segments:
            ts=np.array(indices)/FPS;ys=y[np.array(indices)%n]
            slopes.append(float(np.polyfit(ts,ys,1)[0]))
        weights=np.zeros(n)
        for indices in segments:
            for j,index in enumerate(indices):weights[index%n]=min(smooth((j+1)/5),smooth((len(indices)-j)/5))
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
            a=point(side+'Arm');b=point(side+'ForeArm');c=point(side+'Hand')
            axis=(b-a).cross(c-b)
            if axis.length>1e-5:
                phase=float(gait[i])*(1 if side=='Left' else -1)
                bend=math.radians(cfg['elbow']*(.5+.5*phase))
                set_rotation(side+'ForeArm',Quaternion(axis.normalized(),bend)@wm(side+'ForeArm').to_quaternion())
        # Share a small mean correction at the neck; head variation stays 80%.
        neck=wm('neck').to_quaternion();set_rotation('neck',Quaternion().slerp(facing_bias,.12)@neck)
        desired=facing_bias@raw[i]['head'];set_rotation('Head',centered_head.slerp(desired,.80))
        for side in SIDES:
            pole=raw[i]['knees'][side]+Vector((0,0,height_offset))
            solve_leg(side,targets[side][i],pole,raw[i]['foot_q'][side])
        fitted.append(ns['snapshot']())

    name='A_Spitter_LocomotionV10_'+role;action=ns['new_action'](name,FPS,seconds);previous={}
    for frame in range(n+1):
        scene.frame_set(frame);apply(fitted[frame%n]);ns['key_pose'](frame,previous)
    entry=ns['export'](name,action,FPS,True,ns['metadata'][role]['source']+'; original Meshy skin; LocomotionV10 contact and body fitting')
    entry.update(reference_speed_cm_s=round(speed*100,3),actor_walk_speed_cm_s=round(speed*100,3),
        body_height_offset_cm=round(height_offset*100,3),settings=cfg,
        support_intervals={s:[[round(indices[0]/FPS,4),round((indices[-1]+1)/FPS,4)] for indices in contacts[s]['segments']] for s in SIDES})
    report['movement'][role]=entry
    print('SPITTER_LOCOMOTION_V10_AUTHORED',role,json.dumps(entry),flush=True)

ns['active'](bpy.data.actions['A_Spitter_LocomotionV10_Walk_A']);scene.frame_start=0
scene.frame_end=round(report['movement']['Walk_A']['seconds']*FPS);scene.frame_set(0)
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'SpitterZombie_LocomotionV10.blend'))
(ROOT/'authoring.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print('SPITTER_LOCOMOTION_V10_COMPLETE',flush=True)
