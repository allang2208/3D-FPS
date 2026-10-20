"""Probe untouched compressed samples between authored keys, plus 120 Hz anchors."""
from author_subframes import O,R5,s,lerp_transform
import json,gzip,numpy as np
from scipy.spatial.transform import Rotation as R

def compiled_layer(layer):
    return [(s.ids[t['bone']],np.array(t['times'],dtype=np.float32).astype(float),np.array(t['values'],dtype=np.float32).astype(float).reshape(-1,10)) for t in layer['tracks']]
def apply(base,tracks,t):
    out=base.copy()
    for j,ts,vs in tracks:
        k=int(np.clip(np.searchsorted(ts,t)-1,0,len(ts)-2)) if len(ts)>1 else 0
        if len(ts)==1:v=vs[0].copy()
        else:
            w=float(np.clip((t-ts[k])/(ts[k+1]-ts[k]),0,1));v=(1-w)*vs[k]+w*vs[k+1]
            # Exact slerp used by FWeaponGripTrack::Sample.
            qa,qb=vs[k,3:7],vs[k+1,3:7];qa=qa/np.linalg.norm(qa);qb=qb/np.linalg.norm(qb);dot=qa@qb
            if dot<0:qb=-qb;dot=-dot
            theta=np.arccos(np.clip(dot,-1,1))
            if theta>1e-7:v[3:7]=(np.sin((1-w)*theta)*qa+np.sin(w*theta)*qb)/np.sin(theta)
        out[j,:3]+=v[:3];out[j,7:]+=v[7:];out[j,3:7]=(R.from_quat(v[3:7])*R.from_quat(out[j,3:7])).as_quat()
    return out

if __name__=='__main__':
    raw=json.load(gzip.open(O/'compressed-1920.json.gz','rt'));rate=raw['rate'];order=[raw['names'].index(n) for n in s.names];base=np.array(raw['frames'])[:,order]
    fine=json.load(gzip.open(O/'compressed-window-15360.json.gz','rt'));finebase=np.array(fine['frames'])[:,order]
    querytimes=np.unique(np.r_[np.arange(round(.45*rate),round(.75*rate)+1)/rate,np.array(fine['times'])])
    target=np.load(O/'desired-local-120.npz');report={'rate':rate,'families':{}};saved={};denseframes=[]
    fixed=[j for j,n in enumerate(s.names) if n.endswith('_l') or n.startswith('WPN_')]
    right=[j for j,n in enumerate(s.names) if n.endswith('_r') and n.startswith(('upperarm','lowerarm','hand','thumb','index','middle','ring','pinky'))]
    for family in target.files:
        old=json.loads((R5/'SavedReadback'/f'{family}.json').read_text());folder=O/'SavedReadback' if (O/'SavedReadback'/f'{family}.json').exists() else O/'Profiles';new=json.loads((folder/f'{family}.json').read_text())
        old_layer=compiled_layer(next(c for c in old['clips'] if c['base']==raw['path']));new_layer=compiled_layer(next(c for c in new['clips'] if c['base']==raw['path']))
        rows=[];captured={'before':[],'after':[]}
        for t in querytimes:
            frame=t*120;i=min(int(np.floor(frame+1e-7)),107);w=np.clip(frame-i,0,1)
            finer=66/120-1e-9<=t<=70/120+1e-9;k=round(t*(15360 if finer else rate))
            b=finebase[k-66*128] if finer else base[k]
            wanted=s.comp(s.matrices(lerp_transform(target[family][i],target[family][i+1],w)))
            before=s.comp(s.matrices(apply(b,old_layer,t)));after=s.comp(s.matrices(apply(b,new_layer,t)))
            diff=np.linalg.norm(after[:,:3,3]-wanted[:,:3,3],axis=1);old_diff=np.linalg.norm(before[:,:3,3]-wanted[:,:3,3],axis=1)
            rows.append({'frame':frame,'time':t,'is_held_out':bool(k%2),'hand_before_cm':float(old_diff[s.ids['hand_r']]),'hand_after_cm':float(diff[s.ids['hand_r']]),
                'right_chain_after_cm':float(diff[right].max()),'fixed_matrix_error':float(abs(after[fixed]-before[fixed]).max())})
            if family=='base':
                captured['before'].append(before);captured['after'].append(after);denseframes.append(frame)
        held=[r for r in rows if r['is_held_out']];anchors=[r for r in rows if abs(r['frame']-round(r['frame']))<1e-6]
        report['families'][family]={'max_hand_before_cm':max(r['hand_before_cm'] for r in rows),'max_hand_after_cm':max(r['hand_after_cm'] for r in rows),
            'held_out_right_chain_max_cm':max(r['right_chain_after_cm'] for r in held),'original_anchor_error_cm':max(r['right_chain_after_cm'] for r in anchors),
            'left_weapon_matrix_error':max(r['fixed_matrix_error'] for r in rows),'rows':rows}
        if family=='base':saved=captured
    np.savez_compressed(O/'dense-review.npz',frames=np.array(denseframes),**{k:np.array(v) for k,v in saved.items()})
    report['passed']=all(f['held_out_right_chain_max_cm']<.05 and f['original_anchor_error_cm']<.003 and f['left_weapon_matrix_error']==0 for f in report['families'].values())
    (O/'dense-check.json').write_text(json.dumps(report,indent=2));print(json.dumps({'passed':report['passed'],'families':{f:{k:v for k,v in x.items() if k!='rows'} for f,x in report['families'].items()}},indent=2),flush=True)
    if not report['passed']:raise SystemExit(1)
