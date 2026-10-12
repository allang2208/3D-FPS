"""Transfer absolute accepted grasp frames; preserve current 30-clip ownership."""
import bpy,json,gzip,math,sys,copy
from pathlib import Path
from mathutils import Matrix,Vector,Quaternion
O=Path(__file__).parent;sys.path.insert(0,str(O))
from grip_math import load,matrix,pose,pack
native=load('SK_Super90_V7');donor=load('SK_M4_FoldingSights_HK416');donor_poses=load('M4_donors')
profiles=load('profiles_before');poses=load('poses')
C=Matrix.Diagonal((.01,-.01,.01,1));Ci=C.inverted()
nr={n:C@matrix(v)@Ci for n,v in native['rest'].items()};dr={n:C@matrix(v)@Ci for n,v in donor['rest'].items()}
parents=native['parents'];digits=[n for n in nr if n.endswith('_l') and n.startswith(('thumb','index','middle','ring','pinky'))]
changed=['clavicle_l','upperarm_l','lowerarm_l','lowerarm_aux_l','lowerarm_twist_02_l','lowerarm_twist_01_l','hand_l']+digits
mount=Matrix(((0,-1,0,0),(1,0,0,.16),(0,0,1,-.8015),(0,0,0,1)))
models=json.loads((O.parent/'Super90Foregrips20261007/models.json').read_text())
auth=json.loads((O.parent/'ASH12UniversalAttachments20260919/authoring_inputs.json').read_text())
def semantic(rest,n):
    p=rest[n].translation
    if n=='hand_l':end=rest['middle_01_l'].translation
    elif '_metacarpal_' in n:end=rest[n.split('_')[0]+'_01_l'].translation
    elif '_03_' in n:end=p+(p-rest[n.replace('_03_','_02_')].translation)
    else:end=rest[n.replace('_02_','_03_') if '_02_' in n else n.replace('_01_','_02_')].translation
    x=(end-p).normalized();wide=rest['index_01_l'].translation-rest['pinky_01_l'].translation
    y=(wide-x*wide.dot(x)).normalized();z=x.cross(y).normalized()
    out=Matrix((x,y,z)).transposed().to_4x4();out.translation=p;return out
ns={n:semantic(nr,n) for n in ['hand_l']+digits};ds={n:semantic(dr,n) for n in ns}
def carry(old,hand):
    p={n:m.copy() for n,m in old.items()};s=old['upperarm_l'].translation.copy();e=old['lowerarm_l'].translation.copy();w=old['hand_l'].translation.copy();goal=hand.translation
    axis=(goal-s).normalized();a=(e-s).length;b=(w-e).length;length=(goal-s).length
    if length>(a+b)*.985:
        shift=axis*(length-(a+b)*.985);s+=shift;p['clavicle_l'].translation+=shift;length=(a+b)*.985
    length=max(abs(a-b)+1e-6,length);along=(a*a-b*b+length*length)/(2*length)
    pole=e-old['upperarm_l'].translation;pole-=axis*pole.dot(axis)
    knee=s+axis*along+pole.normalized()*math.sqrt(max(0,a*a-along*along))
    qa=(e-old['upperarm_l'].translation).rotation_difference(knee-s);qb=(w-e).rotation_difference(goal-knee)
    p['upperarm_l']=Matrix.LocRotScale(s,qa@old['upperarm_l'].to_quaternion(),old['upperarm_l'].to_scale())
    p['lowerarm_l']=Matrix.LocRotScale(knee,qb@old['lowerarm_l'].to_quaternion(),old['lowerarm_l'].to_scale())
    fore=p['lowerarm_l']@old['lowerarm_l'].inverted()
    for n in ('lowerarm_aux_l','lowerarm_twist_02_l','lowerarm_twist_01_l'):p[n]=fore@old[n]
    p['hand_l']=hand;return p
def smooth(a,b,v):
    t=max(0.,min(1.,(v-a)/(b-a)));return t*t*(3-2*t)
report={'method':'absolute posed anatomical frames; original native lengths, local translations and weights','families':{}}
grasp_out={};unfitted_out={}
for family,profile in profiles.items():
    dw,_=pose(donor,donor_poses[family]);dw={n:C@m@Ci for n,m in dw.items()}
    normal=dr['WPN_root']@dw['WPN_root'].inverted();dw={n:normal@m for n,m in dw.items()}
    registration=mount@Matrix.Translation((0,0,models['parts'][family]['body_lift']))@Matrix(auth['donors'][family]['mount']).inverted()
    desired={n:registration@dw[n]@dr[n].inverted()@ds[n] for n in ns}
    grasp={}
    for n in ['hand_l']+digits:
        frame=desired[n]@ns[n].inverted()@nr[n]
        if n!='hand_l':frame.translation=grasp[parents[n]]@(nr[parents[n]].inverted()@nr[n]).translation
        grasp[n]=frame
    anchors=('index_02_l','middle_02_l','ring_02_l','thumb_02_l')
    shift=sum((desired[n].translation-grasp[n].translation for n in anchors),Vector())/len(anchors)
    for m in grasp.values():m.translation+=shift
    unfitted_out[family]={n:pack(Ci@m@C) for n,m in grasp.items()}
    # Retain the accepted grouped grasp, with bounded adjustments only where
    # the native Super90 finger proportions cross the angled grip's lower rim.
    if family=='angled':
        fit=json.loads((O/'angled_digit_fit.json').read_text())
        corrections={n:Vector(v) for item in fit.values() for n,v in item['joint_rotation_vectors'].items()}
        locals_before={n:grasp[parents[n]].inverted()@grasp[n] for n in digits}
        for n in digits:
            local=locals_before[n]
            if n in corrections and corrections[n].length>1e-8:
                v=corrections[n];q=Quaternion(v.normalized(),v.length)@local.to_quaternion()
                local=Matrix.LocRotScale(local.translation,q,local.to_scale())
            grasp[n]=grasp[parents[n]]@local
    local_fingers={n:(grasp[parents[n]].inverted()@grasp[n]).to_quaternion() for n in digits}
    idle=next(c for c in profile['clips'] if c['base'].split('/')[-1].startswith('A_Super90_idle.'))
    iw,_=pose(native,poses[idle['base']]['samples'][0],idle);iw={n:C@m@Ci for n,m in iw.items()}
    old_idle=nr['WPN_root']@iw['WPN_root'].inverted()@iw['hand_l'];offset=old_idle.inverted()@grasp['hand_l']
    family_report={'wrist_shift_mm':(grasp['hand_l'].translation-old_idle.translation).length*1000,
        'wrist_angle_deg':math.degrees(old_idle.to_quaternion().rotation_difference(grasp['hand_l'].to_quaternion()).angle),'clips':{}}
    for clip in profile['clips']:
        original=copy.deepcopy(clip);source=poses[clip['base']];tracks={n:[] for n in changed};times=[];weights=[]
        for row in source['samples']:
            uw,ul=pose(native,row,original);old={n:C@m@Ci for n,m in uw.items()}
            relative=nr['WPN_root']@old['WPN_root'].inverted()@old['hand_l']
            distance=(relative.translation-old_idle.translation).length
            angle=old_idle.to_quaternion().rotation_difference(relative.to_quaternion()).angle
            angle=min(angle,2*math.pi-angle)
            weight=(1-smooth(.020,.065,distance))*(1-smooth(math.radians(20),math.radians(55),angle));weights.append(weight)
            target=old['hand_l']@offset
            hand=Matrix.LocRotScale(old['hand_l'].translation.lerp(target.translation,weight),old['hand_l'].to_quaternion().slerp(target.to_quaternion(),weight),old['hand_l'].to_scale())
            p=carry(old,hand) if weight>1e-6 else old
            # Rebuild from preserved local translations/scales so native bone
            # lengths cannot drift while fingers take the approved local frames.
            final={}
            for n in nr:
                par=parents[n];local=C@matrix(ul[n])@Ci
                if n in changed and weight>1e-6:
                    if n in digits:local=Matrix.LocRotScale(local.translation,local.to_quaternion().slerp(local_fingers[n],weight),local.to_scale())
                    else:
                        target_local=p[par].inverted()@p[n] if par else p[n]
                        local=Matrix.LocRotScale(target_local.translation if n=='clavicle_l' else local.translation,target_local.to_quaternion(),local.to_scale())
                final[n]=final[par]@local if par else local
                if n in changed:
                    result=Ci@local@C;base=matrix(row['local'][n]);q=result.to_quaternion()@base.to_quaternion().inverted()
                    if tracks[n] and q.dot(Quaternion((tracks[n][-1][6],*tracks[n][-1][3:6])))<0:q.negate()
                    elif not tracks[n] and q.w<0:q.negate()
                    delta=result.translation-base.translation;scale=result.to_scale()-base.to_scale()
                    tracks[n].append([*delta,q.x,q.y,q.z,q.w,*scale])
            times.append(row['time'])
        clip['duration']=source['duration'];clip['tracks']=[t for t in original['tracks'] if t['bone'] not in changed]
        for n,values in tracks.items():
            clip['tracks'].append({'bone':n,'times':times,'values':[x for v in values for x in v]})
        family_report['clips'][clip['base'].split('/')[-1].split('.')[0]]={'samples':len(times),'full_contact':sum(w>.999 for w in weights),'released_unchanged':sum(w<1e-6 for w in weights)}
    report['families'][family]=family_report;grasp_out[family]={n:pack(Ci@m@C) for n,m in grasp.items()}
    print('GRASP_FAMILY_AUTHORED '+family,flush=True)
with gzip.open(O/'profiles_after.json.gz','wt',encoding='utf-8') as f:json.dump(profiles,f,separators=(',',':'))
(O/'grasp_targets.json').write_text(json.dumps(grasp_out,separators=(',',':')))
(O/'grasp_unfitted.json').write_text(json.dumps(unfitted_out,separators=(',',':')))
(O/'profiles_authored.json').write_text(json.dumps(report,indent=2))
