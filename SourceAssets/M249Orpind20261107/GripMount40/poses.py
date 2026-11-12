"""Move the approved held hand with the grip, solving rotations on the original arm."""
from pathlib import Path
import sys
import gzip
import json
import numpy as np
from scipy.spatial.transform import Rotation as R

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/'Wrist36'))
import rig as G

cl,upper,elbow,hand,arm,_=G.indices('l')
gun=G.ix['WPN_root']
owned=[cl,*arm,hand]


def between(a,b):
    a,b=G.unit(a),G.unit(b)
    return R.from_quat(np.r_[np.cross(a,b),1.+a@b]).as_matrix()


def follow(w,delta):
    # Keep the donor forearm and wrist together. Solve the shoulder on the
    # circle defined by the original clavicle and upper-arm lengths.
    c,a,e,h=w[[cl,upper,elbow,hand],:3,3]
    end=e+delta
    axis=G.unit(end-c)
    distance=np.linalg.norm(end-c)
    lc,lu=np.linalg.norm(a-c),np.linalg.norm(e-a)
    along=(lc*lc-lu*lu+distance*distance)/(2*distance)
    wrist=h+delta
    if abs(along)>lc:
        # When the clavicle reaches tangency, take the nearest feasible
        # elbow on the two-bone circle. Both branches meet at the same pose.
        start=c+axis*np.sign(along)*lc
        fore_length=np.linalg.norm(h-e)
        reach=np.linalg.norm(wrist-start)
        if reach>lu+fore_length:
            start=c+lc*G.unit(wrist-c)
            reach=np.linalg.norm(wrist-start)
        axis=G.unit(wrist-start)
        along=(lu*lu-fore_length*fore_length+reach*reach)/(2*reach)
        pole=end-start
        end=start+along*axis+np.sqrt(max(0,lu*lu-along*along))*G.unit(pole-axis*(axis@pole))
    else:
        pole=a+delta-c
        pole=G.unit(pole-axis*(pole@axis))
        start=c+along*axis+np.sqrt(max(0,lc*lc-along*along))*pole
    new=w.copy()
    new[cl,:3,:3]=between(a-c,start-c)@w[cl,:3,:3]
    upturn=between(e-a,end-start)
    downturn=between(h-e,wrist-end)
    for b in arm:
        if G.names[b].startswith('upperarm'):
            new[b,:3,:3]=upturn@w[b,:3,:3]
            new[b,:3,3]=start+upturn@(w[b,:3,3]-a)
        else:
            new[b,:3,:3]=downturn@w[b,:3,:3]
            new[b,:3,3]=end+downturn@(w[b,:3,3]-e)
    new[hand,:3,3]+=delta
    return new


def author(family,delta):
    profile=json.load(gzip.open(HERE.parent/'Wrist39'/(family+'.json.gz'),'rt'))
    idle=next(c for c in profile['clips'] if c['base'].endswith('_idle'))
    def source(row):
        path=row['base'];src=G.d['clips'][path];times=np.array(src['times'])
        local=G.layer(np.array(src['frames']),path,profile,G.names,times)
        return times,local,G.compose(local,G.parents)
    rest=source(idle)[2][0]
    ref=(np.linalg.inv(rest[gun])@rest[hand])[:3,3]*100
    for row in profile['clips']:
        t,local,w=source(row)
        grip_space=(np.linalg.inv(w[:,gun])@w[:,hand])[:,:3,3]*100
        amount=1-G.ease((np.linalg.norm(grip_space-ref,axis=1)-1.7)/7.)
        if row['base'].endswith(('.A_M249_reload','.A_M249_reload_empty')):
            end=1.20 if row['base'].endswith('_empty') else 2.10
            amount*=1-G.ease((t-.09)/.20)*(1-G.ease((t-max(end,1.28))/.48))
        effective=np.flatnonzero(amount>1e-7)
        if not len(effective):continue
        after=w.copy()
        for i in effective:after[i]=follow(w[i],G.rot(w[i,gun])@delta*amount[i])
        solved=G.encode(after,G.parents)
        # Insert boundaries around a held interval, keeping untouched authored
        # key values along the open-cover and magazine handling tracks.
        active=amount>1e-7
        used=active|np.r_[False,active[:-1]]|np.r_[active[1:],False]
        for b in owned:
            rot=R.from_quat(solved[:,b,3:7])*R.from_quat(local[:,b,3:7]).inv()
            if rot.magnitude().max()<1e-7:continue
            orig=next((tr for tr in row['tracks'] if tr['bone']==G.names[b]),None)
            tt=np.unique(np.r_[orig['times'] if orig else [t[0],t[-1]],t[used]])
            val=G.sample(orig['values'],orig['times'],tt) if orig else np.tile([0.,0,0,0,0,0,1,0,0,0],(len(tt),1))
            if orig:val[np.searchsorted(tt,orig['times'])]=np.asarray(orig['values']).reshape(-1,10)
            mask=np.interp(tt,t,amount)>1e-7
            q=np.zeros((len(t),10));q[:,3:7]=rot.as_quat()
            val[mask,3:7]=(R.from_quat(G.sample(q.ravel(),t,tt[mask])[:,3:7])*R.from_quat(val[mask,3:7])).as_quat()
            tr=dict(bone=G.names[b],times=tt.tolist(),values=val.ravel().tolist())
            if orig:orig.update(tr)
            else:row['tracks'].append(tr)
    with gzip.open(HERE/(family+'.json.gz'),'wt') as out:json.dump(profile,out,separators=(',',':'))
    print('Authored',family,flush=True)


if __name__=='__main__':
    shifts=json.loads((HERE/'fit.json').read_text())['front_deltas_root_cm']
    for family in ('base','vertical','canted','angled','prism'):author(family,np.array(shifts[family]))
