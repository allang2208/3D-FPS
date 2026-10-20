"""Contrast separate base+delta interpolation with authored local interpolation."""
from diagnose_recovery import O,R5,s
import json,numpy as np,gzip
from scipy.spatial.transform import Rotation as R,Slerp

def interp_keys(a,b,w):
    v=(1-w)*a+w*b;q0=a[:,3:7];q1=b[:,3:7].copy();q1[(q0*q1).sum(1)<0]*=-1
    # UE/ACL compressed track interpolation uses normalized quaternion lerp.
    q=(1-w)*q0+w*q1;v[:,3:7]=q/np.linalg.norm(q,axis=1)[:,None]
    return v
if __name__=='__main__':
    profile=json.loads((R5/'SavedReadback/base.json').read_text());motion=s.motion['clips']['quick_melee']
    raw=np.array(motion['frames']);layer=next(c for c in profile['clips'] if c['base']==motion['path'])
    poses=np.load(R5/'poses.npz')['base'];rows=[];dense=[]
    compressed=json.load(gzip.open(O/'compressed-480.json.gz','rt')) if (O/'compressed-480.json.gz').exists() else None
    order=[compressed['names'].index(n) for n in s.names] if compressed else None
    for k in range(4*54,4*108+1):
        i=min(k//4,107);w=k/4-i;t=k/480
        base=interp_keys(raw[i],raw[i+1],w)
        if compressed:base=np.array(compressed['frames'][k])[order]
        p=s.comp(s.matrices(s.apply(base,layer,t)));dense.append(p)
        # The intended support trajectory between these nearby keys is short.
        reference=(1-w)*poses[i,:,:3,3]+w*poses[i+1,:,:3,3]
        errors=np.linalg.norm(p[:,:3,3]-reference,axis=1);j=int(errors.argmax())
        rows.append({'time':t,'source_frame':k/4,'worst_bone':s.names[j],'max_excursion_cm':float(errors[j]),
            'elbow_excursion_cm':float(errors[s.ids['lowerarm_r']]),'hand_excursion_cm':float(errors[s.ids['hand_r']])})
    (O/'subframe-diagnosis.json').write_text(json.dumps(rows,indent=2));np.savez_compressed(O/'subframe-before.npz',poses=np.array(dense),frames=np.arange(4*54,4*108+1)/4)
    print(json.dumps(sorted(rows,key=lambda r:-r['max_excursion_cm'])[:12],indent=2),flush=True)
