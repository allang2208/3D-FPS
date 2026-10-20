"""Locate short shoulder/elbow excursions in the saved real Gunplay output."""
from pathlib import Path
import sys,json,numpy as np,hashlib
O=Path(__file__).resolve().parent;R5=O.parent/'QuickMeleeElbowR5_20261020'
sys.path.insert(0,str(O.parent/'QuickMeleeHandR3_20261019'))
import check_surfaces as s
from action_framing import camera_for_frame
from scipy.spatial.transform import Rotation as R

def boundary(side):
    T=s.bare.T;edges=np.sort(np.vstack([T[:,[0,1]],T[:,[1,2]],T[:,[2,0]]]),axis=1)
    edges,count=np.unique(edges,axis=0,return_counts=True);v=s.bare.first[np.unique(edges[count==1])]
    bn=np.array([s.names[j] for j in s.bare.weights.argmax(1)])
    return np.array([j for j in v if bn[j].startswith(('upperarm','clavicle')) and bn[j].endswith('_'+side)])

if __name__=='__main__':
    receipt=json.loads((R5/'install_receipt.json').read_text())
    current={f:hashlib.sha256((Path('D:/FPS3D/FPSGAME/Content')/(v['path'].removeprefix('/Game/')+'.uasset')).read_bytes()).hexdigest()==v['sha256'] for f,v in receipt['assets'].items()}
    capture=json.loads((R5/'native-saved-glove.json').read_text());cuts={side:boundary(side) for side in ['l','r']}
    result={'R5_still_installed':current,'families':{}}
    for fam in capture['families']:
        order=[fam['names'].index(n) for n in s.names];rows=[];previous=None
        camera=s.matrices([fam['view_to_camera']])[0];tv=np.tan(np.radians(37.5));th=tv*2.65
        for row in fam['frames']:
            fi=row['frame'];p=s.matrices(np.array(row['bones'])[order]);view=camera_for_frame(camera,fi)
            if fi<55:previous=p;continue
            v=s.bare.evaluate(p,row['morphs']);v=v@view[:3,:3].T+view[:3,3]
            r={'frame':fi,'alpha':row['action_alpha'],'arms':{}}
            for side in ['l','r']:
                cut=v[cuts[side]];on=(cut[:,0]>1)&(abs(cut[:,1])<cut[:,0]*th)&(abs(cut[:,2])<cut[:,0]*tv)
                bones={}
                for part in ['clavicle','upperarm','lowerarm','hand','upperarm_twist_01','upperarm_twist_02','lowerarm_twist_01','lowerarm_twist_02']:
                    j=s.ids[part+'_'+side];par=s.parents[j]
                    local=s.relative(p[par],p[j]);ref=s.relative(s.ref[par],s.ref[j])
                    bones[part]={'step_cm':float(np.linalg.norm(p[j,:3,3]-previous[j,:3,3])),
                        'step_deg':float(np.degrees((R.from_matrix(s.rigid(p[j])[:3,:3])*R.from_matrix(s.rigid(previous[j])[:3,:3]).inv()).magnitude())),
                        'native_offset_error_cm':float(np.linalg.norm((local[:3,3]-ref[:3,3])*np.linalg.norm(p[par,:3,:3],axis=0)))}
                r['arms'][side]={'cut_in_view':int(on.sum()),'cut_eye_distance_cm':float(np.linalg.norm(cut,axis=1).min()),'bones':bones}
            rows.append(r);previous=p
        result['families'][fam['family']]=rows
    (O/'diagnosis-r5.json').write_text(json.dumps(result,indent=2))
    summary={'R5_still_installed':current,'families':{}}
    for family,rows in result['families'].items():
        summary['families'][family]={side:{'cut_frames':[(r['frame'],r['arms'][side]['cut_in_view']) for r in rows if r['arms'][side]['cut_in_view']],
            'largest_shoulder_steps':sorted([(r['frame'],r['arms'][side]['bones']['upperarm']['step_cm']) for r in rows],key=lambda x:-x[1])[:4],
            'largest_elbow_steps':sorted([(r['frame'],r['arms'][side]['bones']['lowerarm']['step_cm']) for r in rows],key=lambda x:-x[1])[:4],
            'max_joint_offset_cm':max(v['native_offset_error_cm'] for r in rows for n,v in r['arms'][side]['bones'].items() if n!='clavicle')}
            for side in ['l','r']}
    print(json.dumps(summary,indent=2),flush=True)
