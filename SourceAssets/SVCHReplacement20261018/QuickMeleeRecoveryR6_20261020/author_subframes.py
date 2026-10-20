"""Rebake the existing right-arm recovery keys against compressed subframes.

No new motion: each original 120 Hz pose is retained. Only right-arm profile
keys in frames 54..90 are densified. Left arm, weapon and other clips are copied
byte-for-value from the current profile. Dense input reserves odd samples for
verification: 960/1920 Hz generally, 7680/15360 Hz only within frames 66..70.
"""
from diagnose_recovery import O,R5,s
import json,gzip,copy,numpy as np
from scipy.spatial.transform import Rotation as R

def lerp_transform(a,b,w):
    v=(1-w)*a+w*b;q0=a[:,3:7];q1=b[:,3:7].copy();q1[(q0*q1).sum(1)<0]*=-1
    q=(1-w)*q0+w*q1;v[:,3:7]=q/np.linalg.norm(q,axis=1)[:,None]
    return v

def main():
    raw=json.load(gzip.open(O/'compressed-1920.json.gz','rt'));order=[raw['names'].index(n) for n in s.names]
    base=np.array(raw['frames'])[:,order];rate=raw['rate'];step=rate//120
    selected=[j for j,n in enumerate(s.names) if n.endswith('_r') and n.startswith(('clavicle','upperarm','lowerarm','hand','thumb','index','middle','ring','pinky'))]
    fine=json.load(gzip.open(O/'compressed-window-15360.json.gz','rt'));finebase=np.array(fine['frames'])[:,order]
    def raw_at(t):
        return finebase[round(t*15360)-66*128] if 66/120-1e-9<=t<=70/120+1e-9 else base[round(t*rate)]
    original_times=np.arange(109)/120
    dense_times=np.r_[np.arange(54*8,90*8+1)/960,np.arange(66*64,70*64+1)/7680]
    keytimes=np.unique(np.r_[original_times,dense_times]);receipts={};desired={}
    for family in ['base','angled','vertical','canted','prism']:
        profile=json.loads((R5/'SavedReadback'/f'{family}.json').read_text());output=copy.deepcopy(profile)
        layer=next(c for c in profile['clips'] if c['base']==raw['path']);dest=next(c for c in output['clips'] if c['base']==raw['path'])
        local=np.array([s.apply(base[i*step],layer,t) for i,t in enumerate(original_times)])
        desired[family]=local
        replacement={s.names[j]:[] for j in selected}
        for t in keytimes:
            frame=t*120;i=min(int(np.floor(frame+1e-7)),107);w=np.clip(frame-i,0,1);target=lerp_transform(local[i],local[i+1],w)
            b=raw_at(t)
            for j in selected:
                q=(R.from_quat(target[j,3:7])*R.from_quat(b[j,3:7]).inv()).as_quat()
                v=np.r_[target[j,:3]-b[j,:3],q,target[j,7:]-b[j,7:]]
                values=replacement[s.names[j]]
                if values and np.dot(values[-1][3:7],v[3:7])<0:v[3:7]*=-1
                values.append(v)
        originals={t['bone']:t for t in layer['tracks']}
        for n,values in replacement.items():
            track={'bone':n,'times':keytimes.tolist(),'values':np.array(values).ravel().tolist()}
            # Outside the target recovery window the original sparse samples
            # and interpolation are retained exactly, including absent tracks.
            old=originals.get(n)
            if old:
                merged={round(float(t)*7680):(float(t),np.array(v)) for t,v in zip(old['times'],np.array(old['values']).reshape(-1,10))}
                for t,v in zip(keytimes,values):
                    if 54/120-1e-9<=t<=90/120+1e-9:merged[round(t*7680)]=(float(t),v)
                ticks=sorted(merged);ts=[merged[k][0] for k in ticks];vs=[merged[k][1].copy() for k in ticks]
                for k in range(1,len(vs)):
                    if vs[k-1][3:7]@vs[k][3:7]<0:vs[k][3:7]*=-1
                track={'bone':n,'times':ts,'values':np.array(vs).ravel().tolist()}
            dest['tracks']=[t for t in dest['tracks'] if t['bone']!=n]+[track]
        (O/'Profiles').mkdir(exist_ok=True);(O/'Profiles'/f'{family}.json').write_text(json.dumps(output,separators=(',',':')))
        unchanged=[t for t in layer['tracks'] if t['bone'] not in replacement]
        assert unchanged==[t for t in dest['tracks'] if t['bone'] not in replacement]
        assert [c for c in profile['clips'] if c['base']!=raw['path']]==[c for c in output['clips'] if c['base']!=raw['path']]
        receipts[family]={'right_tracks':len(selected),'keys_per_dense_track':len(keytimes),'left_weapon_tracks_unchanged':True,'other_clips_unchanged':True}
    np.savez_compressed(O/'desired-local-120.npz',**desired)
    (O/'authoring.json').write_text(json.dumps({'method':'Existing 120 Hz right-arm motion rebaked against actual compressed subframes',
        'source_rate':rate,'write_rate':960,'fine_source_rate':15360,'fine_write_rate':7680,
        'fine_window_frames':[66,70],'window_seconds':[.45,.75],'families':receipts},indent=2))
    print('SVCH_R6_SUBFRAME_PROFILES_AUTHORED',receipts,flush=True)

if __name__=='__main__':main()
