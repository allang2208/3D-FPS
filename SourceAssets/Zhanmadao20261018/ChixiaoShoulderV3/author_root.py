"""Keep accepted hands and blade; reshape right shoulder support to exclude its opening."""
import json, math
from pathlib import Path
import bpy
import numpy as np
from mathutils import Matrix, Quaternion, Vector

P=Path(__file__).resolve().parent;V2=P.parent/'ChixiaoGripV2';V1=P.parent/'ChixiaoDoubleHeavyV1'
env={'__file__':str(V1/'author_motion.py')}
exec(compile((V1/'author_motion.py').read_text('utf-8').split('receipt=')[0].replace("data=json.loads((P/'motion_sources.json').read_text('utf-8'))",'data={}'),str(V1/'author_motion.py'),'exec'),env)
A=env['A'];serialize=env['serialize']
RIGHT_ROOT=['clavicle_r','upperarm_r','upperarm_twist_01_r','upperarm_twist_02_r']
RIGHT_FOREARM=['lowerarm_r','lowerarm_twist_01_r','lowerarm_twist_02_r']
normal=np.array([0.,math.tan(math.radians(75)/2),1.]);normal/=np.linalg.norm(normal)
margin=.01
report={'revision':'ChixiaoShoulderV3','clips':{},'preserved':'hands, fingers, left arm, weapon, bone lengths and timing'}

def boundary_skin(obj,reference):
    counts={}
    for face in obj.data.polygons:
        for edge in face.edge_keys:counts[edge]=counts.get(edge,0)+1
    ids=set(i for edge,count in counts.items() if count==1 for i in edge)
    groups={g.index:g.name for g in obj.vertex_groups}
    points=[]
    for i in sorted(ids):
        vertex=obj.data.vertices[i]
        weights={groups[g.group]:g.weight for g in vertex.groups}
        if sum(weights.get(n,0.) for n in RIGHT_ROOT)<.9:continue
        pos=obj.matrix_world@vertex.co
        points.append([(n,w,reference[n].inverted()@pos) for n,w in weights.items() if w>0])
    return points

def skin_points(pose,bindings):
    return np.array([list(sum((pose[n]@local*w for n,w,local in row),Vector())) for row in bindings])

def rotated(points,elbow,axis,angle):
    v=points-elbow;c,s=math.cos(angle),math.sin(angle)
    return elbow+v*c+np.cross(axis,v)*s+np.outer(v@axis,axis)*(1-c)

for variant in ('Standard','LongGrip'):
    original=json.loads((V2/variant/'editable_keys.json').read_text('utf-8'))
    poses=[A.pose_from_rows(sample['bones']) for sample in original['samples']]
    bpy.ops.wm.open_mainfile(filepath=str(V2/variant/'Chixiao_GripV2_Editable.blend'))
    bpy.context.preferences.filepaths.save_version=0
    scene=bpy.context.scene;rig=next(o for o in scene.objects if o.type=='ARMATURE')
    reference={n:A.canonical(A.native(row)) for n,row in A.DATA['reference'].items()}
    bindings=[]
    for obj in scene.objects:
        if obj.type=='MESH' and obj.vertex_groups:bindings+=boundary_skin(obj,reference)
    roots=[skin_points(pose,bindings) for pose in poses]
    elbows=[np.array(pose['lowerarm_r'].translation) for pose in poses]
    exposed=[i for i,points in enumerate(roots) if .12<original['samples'][i]['seconds']<.95 and (points@normal).max()>-margin]
    peak=max(exposed,key=lambda i:(roots[i]@normal).max())
    seed=roots[peak].mean(axis=0)-elbows[peak]
    axis=np.cross(seed,-normal);axis/=np.linalg.norm(axis)
    root_axes=[];lower_axes=[]
    for pose,points,elbow in zip(poses,roots,elbows):
        root_axis=np.cross(points.mean(axis=0)-elbow,-normal);root_axis/=np.linalg.norm(root_axis)
        lower_axis=np.cross(points.mean(axis=0)-np.array(pose['hand_r'].translation),-normal);lower_axis/=np.linalg.norm(lower_axis)
        root_axes.append(root_axis);lower_axes.append(lower_axis)
    required=[];forearm_required=[]
    idle=poses[-1]
    for i,(sample,points,elbow) in enumerate(zip(original['samples'],roots,elbows)):
        t=sample['seconds'];hand=np.array(poses[i]['hand_r'].translation)
        root_axis=root_axes[i];lower_axis=lower_axes[i]
        if not .12<t<.98 or (points@normal).max()<=-margin:
            required.append(0.);forearm_required.append(0.);continue
        best=None
        for lower_deg in np.linspace(0,32,65):
            lower_angle=math.radians(float(lower_deg))
            moved=rotated(points,hand,lower_axis,lower_angle)
            moved_elbow=rotated(elbow[None,:],hand,lower_axis,lower_angle)[0]
            hq=poses[i]['hand_r'].to_quaternion()@idle['hand_r'].to_quaternion().inverted()
            wrist_axis=hq@(idle['hand_r'].translation-idle['lowerarm_r'].translation).normalized()
            bend=math.degrees(wrist_axis.angle(Vector(hand-moved_elbow)))
            if bend>48.:continue
            feasible=None
            for degrees in np.linspace(0,80,41):
                angle=math.radians(float(degrees))
                if (rotated(moved,moved_elbow,root_axis,angle)@normal).max()<=-margin:
                    feasible=angle;break
            if feasible is None:continue
            lo=max(0.,feasible-math.radians(2));hi=feasible
            for _ in range(14):
                mid=(lo+hi)*.5
                if (rotated(moved,moved_elbow,root_axis,mid)@normal).max()<=-margin:hi=mid
                else:lo=mid
            cost=hi*hi+9*lower_angle*lower_angle
            if best is None or cost<best[0]:best=(cost,hi,lower_angle)
        if best is None:raise RuntimeError(f'No supported shoulder clearance: {variant} {t}')
        required.append(best[1]);forearm_required.append(best[2])
    # Smooth the entire correction signal; begin before the opening enters view.
    radius=16
    kernel=np.exp(-.5*(np.arange(-radius,radius+1)/6.)**2);kernel/=kernel.sum()
    def envelope_angles(values):
        envelope=np.array([max(values[max(0,i-radius):min(len(values),i+radius+1)]) for i in range(len(values))])
        result=np.convolve(envelope,kernel,mode='same')
        for i,sample in enumerate(original['samples']):
            t=sample['seconds'];result[i]*=A.smooth((t-.12)/.07)*(1-A.smooth((t-.86)/.12))
        return result
    angles=envelope_angles(required);forearm_angles=envelope_angles(forearm_required)
    rest={b.name:b.matrix_local.copy() for b in rig.data.bones}
    local_rest={n:rest[A.PARENTS[n]].inverted()@m if A.PARENTS[n] in rest else m for n,m in rest.items()}
    correction={n:reference[n].inverted()@rest[n] for n in rest}
    rig.animation_data_clear();rig.animation_data_create()
    action=bpy.data.actions.new('Chixiao_ShoulderV3_'+variant);action.use_fake_user=True;rig.animation_data.action=action
    samples=[];previous={};blend_previous={};rows=[]
    for i,(sample,source,angle) in enumerate(zip(original['samples'],poses,angles)):
        pose={n:m.copy() for n,m in source.items()}
        lower_angle=float(forearm_angles[i]);hand=source['hand_r'].translation
        lower_delta=Matrix.Translation(hand)@Quaternion(Vector(lower_axes[i]),lower_angle).to_matrix().to_4x4()@Matrix.Translation(-hand)
        for n in RIGHT_FOREARM:pose[n]=lower_delta@source[n]
        if angle>1.e-10 or abs(lower_angle)>1.e-10:
            e=pose['lowerarm_r'].translation
            delta=Matrix.Translation(e)@Quaternion(Vector(root_axes[i]),float(angle)).to_matrix().to_4x4()@Matrix.Translation(-e)
            for n in RIGHT_ROOT:pose[n]=delta@lower_delta@source[n]
        keys=sample['bones'] if angle<=1.e-10 and abs(lower_angle)<=1.e-10 else serialize(pose,previous)
        samples.append({'seconds':sample['seconds'],'bones':keys})
        points=skin_points(pose,bindings)
        upper=pose['lowerarm_r'].translation-pose['upperarm_r'].translation
        lower=pose['hand_r'].translation-pose['lowerarm_r'].translation
        rows.append({'t':sample['seconds'],'root_rotation_deg':math.degrees(float(angle)),'forearm_rotation_deg':math.degrees(lower_angle),
                     'wrist_bend_deg':math.degrees(((pose['hand_r'].to_quaternion()@idle['hand_r'].to_quaternion().inverted())@(idle['hand_r'].translation-idle['lowerarm_r'].translation).normalized()).angle(lower)),
                     'root_bottom_clearance_cm':-(points@normal).max()*100,
                     'elbow_bend_deg':math.degrees(upper.angle(lower)),
                     'shoulder_shift_cm':(pose['upperarm_r'].translation-source['upperarm_r'].translation).length*100})
        scene.frame_set(i);world={n:pose[n]@correction[n] for n in rest}
        for b in rig.pose.bones:
            parent=world[b.parent.name] if b.parent else Matrix.Identity(4)
            b.matrix_basis=local_rest[b.name].inverted()@parent.inverted()@world[b.name]
            b.rotation_mode='QUATERNION';q=b.rotation_quaternion.copy()
            if b.name in blend_previous and q.dot(blend_previous[b.name])<0:q=-q
            b.rotation_quaternion=q;blend_previous[b.name]=q.copy()
            for channel in ('location','rotation_quaternion','scale'):b.keyframe_insert(channel,frame=i,group=b.name)
    for layer in action.layers:
        for strip in layer.strips:
            for bag in strip.channelbags:
                for curve in bag.fcurves:
                    for key in curve.keyframe_points:key.interpolation='LINEAR'
    scene.render.fps=original['fps'];scene.render.fps_base=1;scene.frame_start=0;scene.frame_end=len(samples)-1;scene.frame_set(0)
    out=P/variant;out.mkdir(exist_ok=True)
    (out/'editable_keys.json').write_text(json.dumps(dict(original,samples=samples),separators=(',',':')),encoding='utf-8')
    bpy.ops.wm.save_as_mainfile(filepath=str(out/'Chixiao_ShoulderV3_Editable.blend'))
    focus=[r for r in rows if .20<=r['t']<=.75]
    report['clips'][variant]={'axis':axis.tolist(),'root_vertices':len(bindings),
        'peak_forearm_rotation_deg':max(abs(r['forearm_rotation_deg']) for r in rows),
        'peak_wrist_bend_deg':max(r['wrist_bend_deg'] for r in rows),
        'peak_rotation_deg':max(r['root_rotation_deg'] for r in rows),
        'peak_shoulder_shift_cm':max(r['shoulder_shift_cm'] for r in rows),
        'minimum_root_clearance_cm':min(r['root_bottom_clearance_cm'] for r in focus),
        'max_rotation_step_deg':max(abs(b['root_rotation_deg']-a['root_rotation_deg']) for a,b in zip(rows,rows[1:])),
        'elbow_bend_range':[min(r['elbow_bend_deg'] for r in focus),max(r['elbow_bend_deg'] for r in focus)],'frames':rows}
    print('SHOULDER_AUTHORED',variant,json.dumps({k:v for k,v in report['clips'][variant].items() if k!='frames'}),flush=True)
(P/'authoring.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
