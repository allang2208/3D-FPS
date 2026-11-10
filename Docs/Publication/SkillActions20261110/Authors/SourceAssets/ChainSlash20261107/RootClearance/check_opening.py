"""Measure both skin openings, before/after, with the equipped-grip transforms."""
import json
import sys
from pathlib import Path

import numpy as np
from scipy.spatial.transform import Rotation

HERE=Path(__file__).resolve().parent
BASE=HERE.parent
sys.path.insert(0,str(BASE))
from fit_motion import world

FLIP=np.diag([1.,-1.,1.])
IDLE=json.loads((BASE/'grip_poses.json').read_text())
FIT_FILES=['highland-claymore','frost-sword','tang-dao','rune-sword','xuanchi-zhenyue','zhanmadao']

def configurations(grip):
    yield 'bare', {}
    for family in FIT_FILES:
        spec=json.loads((BASE.parents[1]/'Content/ColdSteelData'/(family+'-modules.json')).read_text(encoding='utf-8-sig'))
        base=spec.get('hand_fit',{})
        for name,part in spec.get('slots',{}).get('grip',{}).items():
            folder=part.get('animation_folder',spec.get('animation_folder',''))
            if folder.endswith('/LongGripAnimations') != (grip=='LongGrip'):continue
            fit={**base,**part.get('hand_fit',{})}
            for blade,blade_fit in {'default':{},**part.get('hand_fit_by_blade',{})}.items():
                for guard,guard_spec in spec.get('slots',{}).get('guard',{'default':{}}).items():
                    yield '/'.join((family,name,blade,guard)),{**fit,**blade_fit,**guard_spec.get('hand_fit',{})}

def visible_edges(q,edges,vertical,aspect):
    # Clip every boundary segment against all five halfspaces. Adjacent points
    # may both lie outside different sides of the viewport while the seam crosses it.
    tan=np.tan(np.deg2rad(vertical*.5))
    x,y,z=q.transpose(2,0,1)
    planes=[y-1.,tan*aspect*y+x,tan*aspect*y-x,tan*y+z,tan*y-z]
    interval_min=np.zeros((len(q),len(edges)))
    interval_max=np.ones_like(interval_min)
    for plane in planes:
        a,b=plane[:,edges[:,0]],plane[:,edges[:,1]]
        delta=b-a
        cross=np.divide(-a,delta,out=np.zeros_like(a),where=np.abs(delta)>1.e-10)
        interval_min=np.maximum(interval_min,np.where(delta>1.e-10,cross,0.))
        interval_max=np.minimum(interval_max,np.where(delta<-1.e-10,cross,1.))
        interval_max[(np.abs(delta)<=1.e-10)&(a<0)]=-1.
    return (interval_min<=interval_max).any(1)

def evaluate(folder,grip):
    rig=np.load(folder/(grip+'-rig.npz'))
    v=np.load(folder/(grip+'-verts.npy'),mmap_mode='r')
    tri=rig['tri'];names=rig['names'].tolist();m=rig['mats']
    edges=np.sort(np.concatenate([tri[:,:2],tri[:,1:],tri[:,::2]]),axis=1)
    unique,multiplicity=np.unique(edges,axis=0,return_counts=True)
    boundary=unique[multiplicity==1]
    idle=world(IDLE[grip]['idle']);w=idle['WPN_root']
    weap=m[:,names.index('WPN_root')]
    standard_rotation=weap[:,:3,:3]/np.linalg.norm(weap[:,:3,:3],axis=1,keepdims=True)
    delta=standard_rotation@standard_rotation[0].T
    rotation=delta@(w[:3,:3]/np.linalg.norm(w[:3,:3],axis=0))
    wp=weap[:,:3,3]*100+(delta@(w[:3,3]-weap[0,:3,3]*100))
    configs=list(configurations(grip))
    results={};worst={};nominal=np.zeros(len(v),bool)
    for side,label in (('r','right'),('l','left')):
        strong=rig['weights'][:,[names.index('upperarm_twist_01_'+side),names.index('clavicle_'+side)]].sum(1)>.65
        ring=boundary[strong[boundary].all(1)]
        ids,inverse=np.unique(ring,return_inverse=True)
        if len(ids)!=61:raise ValueError((side,'opening size',len(ids)))
        local_edges=inverse.reshape(-1,2)
        opening=v[:,ids,:]*100
        shoulder=m[:,names.index('upperarm_'+side),:3,3]*100
        shoulder_travel=float(np.linalg.norm(shoulder-shoulder[0],axis=1).max())
        wrist=idle['hand_'+side][:3,3];h=rotation[0].T@(wrist-w[:3,3])
        pivot=np.array([0.,0.,h[2]])
        loc=(opening-wp[:,None,:])@rotation
        side_worst={}
        seen={}
        for name,fit in configs:
            offset=FLIP@np.array(fit.get(label+'_offset_cm',[0,0,0]))
            roll=FLIP@Rotation.from_quat(fit.get(label+'_rotation',[0,0,0,1])).as_matrix()@FLIP
            key=tuple(np.r_[offset,roll.ravel()].round(7))
            if key in seen:continue
            seen[key]=name
            q=((loc-pivot)@roll.T+pivot+offset)@rotation.transpose(0,2,1)+wp[:,None,:]
            for label_view,fov,aspect in [('game',75.,16/9),('expanded',85.,21/9)]:
                contact=visible_edges(q,local_edges,fov,aspect)
                if name=='bare' and label_view=='game':nominal|=contact
                bottom=(-q[:,:,2]-np.tan(np.deg2rad(fov*.5))*q[:,:,1])*np.cos(np.deg2rad(fov*.5))
                group=side_worst.setdefault(label_view,dict(frames=set(),bottom_gap_cm=1.e6))
                group['frames'].update(np.flatnonzero(contact).tolist())
                group['bottom_gap_cm']=min(group['bottom_gap_cm'],float(bottom.min()))
            # The old tick froze its entry transform. The new tick eases it
            # toward neutral at the component's 9/s.
            decay=np.ones(len(q)) if folder.name=='Before' else (1-9/120.)**np.arange(len(q))
            for sign in (-1.,1.):
                ang=Rotation.from_rotvec(decay[:,None]*[[sign*np.deg2rad(22),0,0]]).as_matrix()
                sprint=q@ang.transpose(0,2,1)+decay[:,None,None]*np.array([0.,-4.,-9.])
                contact=visible_edges(sprint,local_edges,75.,16/9)
                side_worst.setdefault('sprint_entry',dict(frames=set()))['frames'].update(np.flatnonzero(contact).tolist())
        results[side]=dict(opening_vertices=len(ids),shoulder_excursion_cm=round(shoulder_travel,3),
            configurations=list(seen.values()),cases={k:{**group,'frames':sorted(group['frames']),'frame_count':len(group['frames'])} for k,group in side_worst.items()})
    fitted_frames={frame for side in results.values() for frame in side['cases']['game']['frames']}
    return dict(frames=len(v),bare_nominal_frames=int(nominal.sum()),
        any_fit_nominal_frames=len(fitted_frames),sides=results)

if __name__=='__main__':
    report={k:{g:evaluate(folder,g) for g in ('Standard','LongGrip')} for k,folder in [('before',HERE/'Before'),('after',BASE/'Review')]}
    (HERE/'opening-report.json').write_text(json.dumps(report,indent=2))
    for stage,grips in report.items():
        for grip,res in grips.items():
            print(stage,grip,'bare',res['bare_nominal_frames'],[(s,v['shoulder_excursion_cm'],[(k,x['frame_count'],round(x.get('bottom_gap_cm',0),1)) for k,x in v['cases'].items()]) for s,v in res['sides'].items()])
