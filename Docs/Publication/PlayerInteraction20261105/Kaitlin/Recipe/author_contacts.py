"""Preserve male weapon-local contacts on native female arm lengths.

Only native two-hand libraries are baked. Procedural weapon families already
use target-body palm registration and retain their existing runtime solvers.
"""
import gzip,json,math
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation as R
from weapon_contact_math import bodies,palm_mount,compose,inverse,rotate,mul,unit,fk,read

W=Path(__file__).resolve().parent
male,female=bodies()
mounts={s:palm_mount(male,female,s) for s in ('l','r')}
selected=read(W/'selected.json')


def compact(skel,names):
    names=sorted(names,key=lambda n:skel['index'][n])
    ix={n:i for i,n in enumerate(names)}
    parents=[]
    for n in names:
        p=skel['parents'][skel['index'][n]]
        parents.append(-1 if p<0 else ix[skel['names'][p]])
    return dict(names=names,index=ix,parents=parents)


def between(a,b):
    a,b=unit(a),unit(b)
    dot=float(np.clip(np.dot(a,b),-1,1))
    if dot<-.99999:
        axis=np.cross(a,[1.,0.,0.])
        if np.linalg.norm(axis)<.01:axis=np.cross(a,[0.,1.,0.])
        return np.r_[unit(axis),0.]
    return unit(np.r_[np.cross(a,b),1.+dot])


def write_rotation(local,world,skel,index,q):
    parent=skel['parents'][index]
    local[index,3:7]=mul(R.from_quat(world[parent,3:7]).inv().as_quat(),q) if parent>=0 else q


def fit_arm(local,skel,side,goal,previous_twist):
    ix=skel['index'];a,b,c=[ix[n+'_'+side] for n in ('upperarm','lowerarm','hand')]
    world=fk(local,skel);shoulder=world[a,:3]
    l1=np.linalg.norm(world[b,:3]-shoulder);l2=np.linalg.norm(world[c,:3]-world[b,:3])
    ray=unit(goal[:3]-shoulder);reach=np.linalg.norm(goal[:3]-shoulder)
    if reach>=l1+l2-.0001 or reach<=abs(l1-l2)+.0001:
        raise RuntimeError('Paired contact outside native arm reach')
    bend=unit((world[b,:3]-shoulder)-ray*np.dot(world[b,:3]-shoulder,ray))
    along=(l1*l1-l2*l2+reach*reach)/(2*reach)
    elbow=shoulder+ray*along+bend*math.sqrt(max(0.,l1*l1-along*along))
    write_rotation(local,world,skel,a,mul(between(world[b,:3]-shoulder,elbow-shoulder),world[a,3:7]))
    world=fk(local,skel)
    write_rotation(local,world,skel,b,mul(between(world[c,:3]-world[b,:3],goal[:3]-world[b,:3]),world[b,3:7]))
    world=fk(local,skel);axis=unit(goal[:3]-world[b,:3])
    difference=mul(goal[3:7],R.from_quat(world[c,3:7]).inv().as_quat())
    angle=(2*math.atan2(np.dot(difference[:3],axis),difference[3])+math.pi)%(2*math.pi)-math.pi
    if side in previous_twist:angle+=2*math.pi*round((previous_twist[side]-angle)/(2*math.pi))
    previous_twist[side]=angle
    twist=angle*.70
    write_rotation(local,world,skel,b,mul(R.from_rotvec(axis*twist).as_quat(),world[b,3:7]))
    after=fk(local,skel)
    write_rotation(local,after,skel,c,goal[3:7])
    for name in ('lowerarm_twist_01_'+side,'lowerarm_twist_02_'+side):
        j=ix[name]
        # The helper's axial station determines the fraction of the added roll.
        station=float(np.clip(np.linalg.norm(world[j,:3]-world[b,:3])/l2,0,1))
        desired=mul(R.from_rotvec(axis*twist*station).as_quat(),world[j,3:7])
        write_rotation(local,fk(local,skel),skel,j,desired)


reports={}
for key,spec in selected.items():
    output=W/'Authored'/(key+'.json.gz')
    if output.exists():
        reports[key]=read(W/'Authored'/(key+'-report.json'));continue
    with gzip.open(W/'Tracks'/(key+'.json.gz'),'rt',encoding='utf-8') as stream:data=json.load(stream)
    result=dict(spec,rate=data['rate'],keys=data['keys'])
    report=dict(roles=spec['roles'],source=spec['source'],previous=spec['target'],kind=spec['kind'])
    if spec['kind']=='bow':
        curves=data['curves'];changed={}
        for prefix,side,size in [('SparrowBowGrip','l',7),('SparrowBowRight','r',7),('SparrowBowNock','r',3)]:
            labels=['X','Y','Z','QX','QY','QZ','QW'][:size]
            if prefix+labels[0] not in curves:continue
            times=curves[prefix+labels[0]][0]
            values=np.array([np.interp(times,*curves[prefix+n]) for n in labels]).T
            mapped=np.array([compose(mounts[side],v) if size==7 else mounts[side][:3]+rotate(mounts[side][3:7],v) for v in values])
            if size==7:
                for i in range(1,len(mapped)):
                    if np.dot(mapped[i-1,3:7],mapped[i,3:7])<0:mapped[i,3:7]*=-1
            for j,n in enumerate(labels):changed[prefix+n]=[times,mapped[:,j].tolist()]
        result['curves']=changed;report['curve_count']=len(changed)
    else:
        skel=compact(female,data['names']);source_skel=compact(male,data['names'])
        order=[data['names'].index(n) for n in skel['names']]
        source_order=[data['names'].index(n) for n in source_skel['names']]
        targets=np.array(data['target_frames'])[:,order];sources=np.array(data['source_frames'])[:,source_order]
        ix=skel['index'];mi=source_skel['index'];changed=[];previous_twist={}
        residuals=[];shifts=[];before=[];rotation_residuals=[]
        for local,source in zip(targets,sources):
            source_world=fk(source,source_skel);world=fk(local,skel)
            relation=compose(inverse(source_world[mi['hand_r'],:7]),source_world[mi['hand_l'],:7])
            relation=compose(compose(mounts['r'],relation),inverse(mounts['l']))
            goals={'r':world[ix['hand_r'],:7].copy()}
            goals['l']=compose(goals['r'],relation)
            before.append(np.linalg.norm(goals['l'][:3]-world[ix['hand_l'],:3]))
            shoulders={s:world[ix['upperarm_'+s],:3] for s in ('r','l')}
            limits={s:(np.linalg.norm(world[ix['lowerarm_'+s],:3]-shoulders[s])+np.linalg.norm(world[ix['hand_'+s],:3]-world[ix['lowerarm_'+s],:3]))*.995 for s in ('r','l')}
            shift=np.zeros(3)
            for _ in range(40):
                moved=False
                for s in ('r','l'):
                    v=goals[s][:3]+shift-shoulders[s];length=np.linalg.norm(v)
                    if length>limits[s]:shift-=v*(1-limits[s]/length);moved=True
                if not moved:break
            for s in ('r','l'):goals[s][:3]+=shift
            if np.linalg.norm(shift)>1e-7:fit_arm(local,skel,'r',goals['r'],previous_twist)
            fit_arm(local,skel,'l',goals['l'],previous_twist)
            fitted=fk(local,skel)
            actual=compose(inverse(fitted[ix['hand_r'],:7]),fitted[ix['hand_l'],:7])
            residuals.append(float(np.linalg.norm(actual[:3]-relation[:3])))
            rotation_residuals.append(float(np.degrees((R.from_quat(actual[3:7]).inv()*R.from_quat(relation[3:7])).magnitude())))
            shifts.append(float(np.linalg.norm(shift)))
            changed.append(local)
        frames=np.array(changed)
        for i in range(1,len(frames)):
            flip=np.sum(frames[i-1,:,3:7]*frames[i,:,3:7],axis=1)<0;frames[i,flip,3:7]*=-1
        owned=[n for n in skel['names'] if n.startswith(('upperarm_','lowerarm_','hand_'))]
        result['names']=owned;result['frames']=frames[:,[ix[n] for n in owned]].tolist()
        report.update(frames=len(frames),before_max_cm=float(max(before)),after_max_cm=max(residuals),
                      after_max_degrees=max(rotation_residuals),group_shift_max_cm=max(shifts),
                      bone_translations_changed=False,weapon_scale_changed=False)
    output.parent.mkdir(exist_ok=True)
    with gzip.open(output,'wt',encoding='utf-8') as stream:json.dump(result,stream,separators=(',',':'))
    (W/'Authored'/(key+'-report.json')).write_text(json.dumps(report,indent=2),encoding='utf-8')
    reports[key]=report
    print('AUTHORED',spec['roles'][0],report.get('before_max_cm'),report.get('after_max_cm'),flush=True)
(W/'authoring_report.json').write_text(json.dumps(reports,indent=2),encoding='utf-8')
