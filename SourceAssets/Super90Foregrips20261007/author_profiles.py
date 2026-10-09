"""Retarget accepted common grasps into sparse native left-arm pose layers.

Super90 feeds shells with the RIGHT hand. The LEFT hand holds the grip during
all native clips, including the tilted continuous reload and its return tail.
"""
import bpy,json,math,sys
from pathlib import Path
from mathutils import Matrix,Vector,Quaternion
O=Path(__file__).parent;S=O.parent;X=O/'Profiles';X.mkdir(exist_ok=True)
sys.path.insert(0,str(S/'RSH12Grip20261003'))
from pose_geometry import matrix,set_pose
bpy.ops.wm.open_mainfile(filepath=str(S/'BenelliM4Super9020261006/Super90_Gameplay_Editable.blend'))
rig=bpy.data.objects['SK_Super90'];rig.animation_data_clear();rig.data.pose_position='POSE'
D=json.loads((O/'native.json').read_text());M=json.loads((O/'models.json').read_text())
donors=json.loads((S/'M16UniversalAttachments20260920/authoring.json').read_text())['donors']
rest={b.name:b.matrix_local.copy() for b in rig.data.bones};names=list(rest)
parents={b.name:b.parent.name if b.parent else None for b in rig.data.bones}
C=Matrix.Diagonal((100,-100,100,1));Ci=C.inverted()
# Keep each imported FBX bone's actual basis and inherited scale. Native arm
# axes differ from M4 and from the gun's physical forward/up directions.
K={n:(C@rest[n]).inverted()@matrix(D['rest'][n]) for n in names}
Ki={n:k.inverted() for n,k in K.items()}
mount=Matrix(M['mount_native']);root_rest_inv=rest['WPN_root'].inverted()
finger_names=[n for n in names if n.endswith('_l') and n.startswith(('thumb','index','middle','ring','pinky'))]
changed=['clavicle_l','upperarm_l','lowerarm_l','lowerarm_aux_l','lowerarm_twist_01_l','lowerarm_twist_02_l','hand_l']+finger_names
def frame(data,n):
    side=n[-1];p=data[n].translation
    if n=='hand_l':end=data['middle_01_l'].translation
    elif '_metacarpal_' in n:end=data[n.split('_')[0]+'_01_l'].translation
    elif '_03_' in n:end=p+(p-data[n.replace('_03_','_02_')].translation)
    else:end=data[n.replace('_02_','_03_') if '_02_' in n else n.replace('_01_','_02_')].translation
    x=(end-p).normalized();wide=data['index_01_l'].translation-data['pinky_01_l'].translation
    forward=data['middle_01_l'].translation-data['hand_l'].translation
    z=forward.cross(wide).normalized();y=z.cross(x).normalized();z=x.cross(y).normalized()
    m=Matrix((x,y,z)).transposed().to_4x4();m.translation=p;return m
anatomy={n:frame(rest,n) for n in ['hand_l']+finger_names}
def native(sample):
    world={}
    for n,v in sample['local'].items():world[n]=world.get(D['parents'][n],Matrix.Identity(4))@matrix(v)
    return {n:Ci@world[n]@Ki[n] for n in names},world
def carry(old,hand):
    p={n:m.copy() for n,m in old.items()};shoulder=old['upperarm_l'].translation.copy();elbow=old['lowerarm_l'].translation.copy();wrist=old['hand_l'].translation.copy()
    goal=hand.translation;v=goal-shoulder;length=v.length;axis=v.normalized();a=(elbow-shoulder).length;b=(wrist-elbow).length
    reach=(a+b)*.985
    if length>reach:
        shift=axis*(length-reach);shoulder+=shift;p['clavicle_l'].translation+=shift;length=reach
    length=max(abs(a-b)+1e-6,length);along=(a*a-b*b+length*length)/(2*length)
    pole=elbow-old['upperarm_l'].translation;pole-=axis*pole.dot(axis)
    knee=shoulder+axis*along+pole.normalized()*math.sqrt(max(0,a*a-along*along))
    qa=(elbow-old['upperarm_l'].translation).rotation_difference(knee-shoulder)
    qb=(wrist-elbow).rotation_difference(goal-knee)
    p['upperarm_l']=Matrix.LocRotScale(shoulder,qa@old['upperarm_l'].to_quaternion(),Vector((1,1,1)))
    p['lowerarm_l']=Matrix.LocRotScale(knee,qb@old['lowerarm_l'].to_quaternion(),Vector((1,1,1)))
    # Spread the changed wrist pronation over the three native forearm skin
    # stations. The proximal V7 weight is lowerarm_aux, not lowerarm_l.
    axis=(goal-knee).normalized();roll=hand.to_quaternion()@(qb@old['hand_l'].to_quaternion()).inverted()
    along=Vector((roll.x,roll.y,roll.z)).dot(axis);angle=2*math.atan2(along,roll.w)
    angle=(angle+math.pi)%(2*math.pi)-math.pi
    for n,w in (('lowerarm_aux_l',.20),('lowerarm_twist_02_l',.50),('lowerarm_twist_01_l',.80)):
        base=p['lowerarm_l']@old['lowerarm_l'].inverted()@old[n]
        p[n]=Matrix.LocRotScale(base.translation,Quaternion(axis,angle*w)@base.to_quaternion(),Vector((1,1,1)))
    p['hand_l']=hand;return p
report={'source_clips':list(D['clips']),'changed_bones':changed,'native_shell_feed':'right hand; left support retained','runtime_tested':False,'families':{}}
for family in ('vertical','canted','prism','angled'):
    donor=donors[family];dr={n:Matrix(v) for n,v in donor['rest'].items()};dp={n:Matrix(v) for n,v in donor['pose'].items()}
    da={n:frame(dr,n) for n in ['hand_l']+finger_names};posed={n:dp[n]@dr[n].inverted()@da[n] for n in da}
    hand=Matrix(M['parts'][family]['hand_in_mount'])@dr['hand_l'].inverted()@da['hand_l']@anatomy['hand_l'].inverted()@rest['hand_l']
    grasp={'hand_l':hand};finger_local={}
    for n in finger_names:
        par=parents[n]
        donor_bind=da[par].to_quaternion().inverted()@da[n].to_quaternion()
        donor_pose=posed[par].to_quaternion().inverted()@posed[n].to_quaternion()
        delta=donor_bind.inverted()@donor_pose
        target_bind=anatomy[par].to_quaternion().inverted()@anatomy[n].to_quaternion()
        parent_anatomy=grasp[par]@rest[par].inverted()@anatomy[par]
        q=parent_anatomy.to_quaternion()@target_bind@delta@anatomy[n].to_quaternion().inverted()@rest[n].to_quaternion()
        pos=grasp[par]@(rest[par].inverted()@rest[n]).translation
        grasp[n]=Matrix.LocRotScale(pos,q,Vector((1,1,1)));finger_local[n]=grasp[par].to_quaternion().inverted()@q
    # Move the complete grasp as one group to account for the native palm size;
    # no fingertip translations, joint length edits or independent finger fitting.
    anchors=('index_02_l','middle_02_l','ring_02_l','thumb_02_l')
    donor_mount_inv=Matrix(donor['mount']).inverted();lift=Vector((0,0,M['parts'][family]['body_lift']))
    shift=sum(((donor_mount_inv@dp[n]).translation+lift-grasp[n].translation for n in anchors),Vector())/len(anchors)
    hand.translation+=shift
    result={'family':family,'clips':[]}
    for kind,clip in D['clips'].items():
        tracks={n:[] for n in changed};times=[];first=None
        for sample in clip['samples']:
            old,world=native(sample);target=old['WPN_root']@root_rest_inv@mount@hand;p=carry(old,target)
            for n in finger_names:
                par=parents[n];lp=old[par].inverted()@old[n]
                p[n]=p[par]@Matrix.LocRotScale(lp.translation,finger_local[n],lp.to_scale())
            if first is None:first=p
            new_world={n:C@p[n]@K[n] for n in names}
            times.append(sample['time'])
            for n in changed:
                par=parents[n];local=new_world[par].inverted()@new_world[n];base=matrix(sample['local'][n]);q=local.to_quaternion()@base.to_quaternion().inverted()
                if tracks[n]:
                    previous=Quaternion((tracks[n][-1][6],*tracks[n][-1][3:6]))
                    if q.dot(previous)<0:q.negate()
                elif q.w<0:q.negate()
                # Native local translations and scales remain authoritative.
                delta=local.translation-base.translation if n=='clavicle_l' else Vector()
                tracks[n].append([*delta,q.x,q.y,q.z,q.w,0.,0.,0.])
        entry={'kind':kind,'base':clip['asset'],'duration':clip['duration'],'tracks':[]}
        for n,values in tracks.items():
            zero=[0,0,0,0,0,0,1,0,0,0]
            if all(max(abs(a-b) for a,b in zip(zero,v))<1e-6 for v in values):continue
            constant=all(max(abs(a-b) for a,b in zip(values[0],v))<1e-6 for v in values[1:])
            entry['tracks'].append({'bone':n,'times':[0.] if constant else times,'values':values[0] if constant else [x for v in values for x in v]})
        result['clips'].append(entry)
        if kind=='idle':idle=first
        print('SUPER90_GRIP_LAYER',family,kind,flush=True)
    (X/(family+'.json')).write_text(json.dumps(result,separators=(',',':')),encoding='utf-8')
    set_pose(rig,idle);bpy.context.preferences.filepaths.save_version=0
    with bpy.data.libraries.load(str(O/'Exports'/('SM_Super90_'+family+'_Editable.blend')),link=False) as (src,dst):dst.objects=['SM_Super90_'+family]
    grip=dst.objects[0];bpy.context.collection.objects.link(grip)
    grip.matrix_world=idle['WPN_root']@root_rest_inv@mount
    bpy.ops.wm.save_as_mainfile(filepath=str(X/('Super90_'+family+'_Editable.blend')))
    bpy.data.objects.remove(grip,do_unlink=True)
    report['families'][family]={'group_grasp_shift_m':list(shift),'clips':len(result['clips'])}
(O/'profile_authoring.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('SUPER90_GRIP_PROFILES_AUTHORED',flush=True)
