"""Compare old/current sleeve avoidance over the requested firearm inventory.

No game or asset mutation. Reports sampled risks and explicit coverage gaps,
not a global collision/visual pass. Geometry checks use one highest-displacement
sample per clip and omit finger-weighted cuff vertices not in the pose export.
"""
import importlib.util
import sys
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation
import diagnose_chainmail_camera as current
from garment_motion import matrix,prepare,posed
from garment_pipeline import read,write,digest,asset_file

P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/FirearmChainmailReview20260930'
spec=importlib.util.spec_from_file_location('previous_clearance',P/'SourceAssets/SVDReloadElbow20260930/Before/diagnose_chainmail_camera.py')
previous=importlib.util.module_from_spec(spec);spec.loader.exec_module(previous)
HIPS={'M4':[0,7,-7],'AKM':[6,7,-7],'QBZ191':[0,7,-7],'ASH12':[8,7,-7],
    'M16':[5,7,-7],'M1911':[-2,3,-6.5],'DW715':[1,3.2,-7],
    'A762':[6,7,-7],'SVD':[6,7,-7],'PKM':[9,9,-11],'LMG201':[9,9,-11]}
EYES={'M4':12,'AKM':18,'QBZ191':12,'ASH12':18,'M16':18,'M1911':38,'DW715':38,'A762':18,'SVD':7,'PKM':20,'LMG201':20}


def flex(b,side):
    a,e,h=[b[n+'_'+side][:3,3] for n in ['upperarm','lowerarm','hand']]
    x,y=e-a,h-e
    return float(np.degrees(np.arccos(np.clip(x@y/np.linalg.norm(x)/np.linalg.norm(y),-1.,1.))))


def frame(rig,reference,kind):
    base=rig.split('_')[0];pistol=base in ('M1911','DW715')
    f=np.eye(4);f[:3,:3]=Rotation.from_euler('z',-90 if pistol else 90,degrees=True).as_matrix()
    hip=np.zeros(3) if '_' in rig else np.array(HIPS[base],dtype=float)
    f[:3,3]=hip
    if kind.startswith('action'):
        alpha=float(kind.split(':')[1]);f[:3,3]=hip*(1-alpha)+np.array([10,0,-5])*alpha
    if kind=='ads':
        rear=reference['WPN_RearSight'][:3,3];front=reference['WPN_FrontSight'][:3,3]
        if base=='AKM':
            rear=(reference['WPN_root']@np.array([.0007595263,.1704100072,.1019900516,1]))[:3]
            front=(reference['WPN_root']@np.array([.0008,.5575537682,.0968115032,1]))[:3]
        axis=front-rear;axis/=np.linalg.norm(axis)
        if pistol or base=='SVD':
            up=reference['WPN_root'][:3,2];right=np.cross(up,axis);right/=np.linalg.norm(right)
            f[:3,:3]=np.array([axis,right,np.cross(axis,right)])
        else:f[:3,:3]=current.swing(f[:3,:3]@axis,np.array([1.,0,0]))@f[:3,:3]
        f[:3,3]=np.array([EYES[base],0,0])-f[:3,:3]@rear
    return f


def geometry_inputs(rig,names):
    result=[]
    for lod in range(3):
        mesh=read(P/f'SourceAssets/ChainmailCameraClearance20260929/{rig}/LOD{lod}.json')
        assert digest(asset_file(mesh['source']))==mesh['asset_sha256']
        valid=np.array([set(w)<=names for w in mesh['weights']])
        # Unknown finger channels are excluded, never replaced by guessed poses.
        mesh['weights']=[w if ok else {} for w,ok in zip(mesh['weights'],valid)]
        triangles=np.array(mesh['triangles']);triangles=triangles[np.all(valid[triangles],axis=1)]
        edges=np.unique(np.sort(np.concatenate([triangles[:,[0,1]],triangles[:,[1,2]],triangles[:,[2,0]]]),axis=1),axis=0)
        positions=np.array(mesh['positions'])
        lengths=np.linalg.norm(positions[edges[:,0]]-positions[edges[:,1]],axis=1)
        upper=np.array([i for i,w in enumerate(mesh['weights']) if sum(v for n,v in w.items() if n.startswith(('clavicle','upperarm')))>.65])
        result.append((prepare(mesh),edges,lengths,upper))
    return result


def measure_geometry(inputs,bones,f):
    result=[]
    for data,edges,rest,upper in inputs:
        points=posed(data,bones);length=np.linalg.norm(points[edges[:,0]]-points[edges[:,1]],axis=1)
        result.append(dict(max_edge_cm=float(length.max()),max_stretch=float((length[rest>.1]/rest[rest>.1]).max()),
            upper_cone_vertices=current.intrusion(points,f,upper)))
    return result


def main(only=None):
    inventory=read(R/'inventory.json');reports=read(R/'summary.json') if only else {}
    for rig,entry in inventory.items():
        if only and rig not in only:continue
        source=read(entry['path']);assert digest(asset_file(source['native']))==source['native_sha256']
        assert digest(asset_file(source['shirt']))==source['shirt_sha256']
        names=set(source['clips'][0]['samples'][0]['bones'])
        meshes=geometry_inputs(rig,names)
        sides=[rig[-1]] if rig.endswith(('_l','_r')) else ['l','r']
        results=[];details=[]
        for clip in source['clips']:
            assert digest(asset_file(clip['asset']))==clip['sha256']
            refs={n:matrix(t) for n,t in clip['samples'][0]['bones'].items()}
            frames=['ads'] if clip['group']=='ads' and '_' not in rig else ['hip']
            if clip['group'] in ('reload','inspect','melee') and (rig in ('M4','QBZ191','ASH12','M16','SVD','PKM') or
                rig=='LMG201' and 'ClothFeed' in clip['asset']):frames+=['action:0.5','action:1']
            row=dict(asset=clip['asset'],group=clip['group'],cases=0,previous_locked=0,current_locked=0,
                current_extension_max_deg=0.,max_elbow_shift_cm=0.,immutable_error=0.,max_length_error=0.,nonfinite=0)
            chosen=None;score=-1
            for sample in clip['samples']:
                b={n:matrix(t) for n,t in sample['bones'].items()}
                for framing in frames:
                    f=frame(rig,refs,framing)
                    old,_=previous.correct(b,f);new,corrections=current.correct(b,f)
                    row['cases']+=1
                    if not all(np.isfinite(m).all() for m in new.values()):row['nonfinite']+=1;continue
                    immutable=[n for n in b if n.startswith(('hand_','WPN_'))]
                    row['immutable_error']=max(row['immutable_error'],max(float(np.abs(new[n]-b[n]).max()) for n in immutable))
                    row['max_length_error']=max(row['max_length_error'],max((max(c['upper_length_error'],c['lower_length_error']) for c in corrections),default=0))
                    shift=0
                    for side in sides:
                        initial,before,after=flex(b,side),flex(old,side),flex(new,side)
                        row['previous_locked']+=int(initial>10 and before<3)
                        row['current_locked']+=int(initial>10 and after<3)
                        row['current_extension_max_deg']=max(row['current_extension_max_deg'],initial-after)
                        distance=float(np.linalg.norm(new['lowerarm_'+side][:3,3]-b['lowerarm_'+side][:3,3]))
                        shift=max(shift,distance)
                    row['max_elbow_shift_cm']=max(row['max_elbow_shift_cm'],shift)
                    if shift>score:
                        score=shift;chosen=(sample['time'],framing,b,old,new,f)
            if chosen:
                time,framing,b,old,new,f=chosen
                row['geometry_sample']=dict(time=time,framing=framing,
                    source=measure_geometry(meshes,b,f),previous=measure_geometry(meshes,old,f),current=measure_geometry(meshes,new,f))
            results.append(row)
        summary=dict(clips=len(results),samples=entry['samples'],cases=sum(x['cases'] for x in results),groups=entry['groups'],
            previous_locked=sum(x['previous_locked'] for x in results),current_locked=sum(x['current_locked'] for x in results),
            nonfinite=sum(x['nonfinite'] for x in results),max_extension_deg=max(x['current_extension_max_deg'] for x in results),
            immutable_error=max(x['immutable_error'] for x in results),max_length_error=max(x['max_length_error'] for x in results))
        write(R/'results'/f'{rig}.json',dict(summary=summary,clips=results))
        reports[rig]=summary;write(R/'summary.json',reports)
        print('CLEARANCE_REVIEW',rig,summary,flush=True)


if __name__=='__main__':main(sys.argv[1:] or None)
