"""Redistribute the existing return path; never alter mechanical/contact clocks."""
from pathlib import Path
import pickle, json, importlib.util
import numpy as np
from scipy.spatial.transform import Rotation as R, Slerp
from scipy.ndimage import gaussian_filter1d
r=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('contact_motion',r/'motion.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)

def interpolate(ts, values, at):
    out=np.empty((len(at),values.shape[1],10))
    for i in range(values.shape[1]):
        for j in [0,1,2,7,8,9]:out[:,i,j]=np.interp(at,ts,values[:,i,j])
        out[:,i,3:7]=Slerp(ts,R.from_quat(values[:,i,3:7]))(np.clip(at,ts[0],ts[-1])).as_quat()
    return out

def progress(q):
    a=.12;u=np.minimum(q,1-q)/a
    edge=a*(u**3-.5*u**4)/(1-a)
    return np.where(q<a,edge,np.where(q>1-a,1-edge,(q-a/2)/(1-a)))

def match_arm_lengths(w, reference):
    """Restore the source-frame lengths after re-timing, keeping palms fixed."""
    result=w.copy()
    for k in range(len(w)):
        a,e,h=[w[k,m.ix[n],:3,3] for n in ['upperarm_l','lowerarm_l','hand_l']]
        ra,re,rh=[reference[k,m.ix[n],:3,3] for n in ['upperarm_l','lowerarm_l','hand_l']]
        u,l=np.linalg.norm(re-ra),np.linalg.norm(rh-re)
        length=np.linalg.norm(h-a);axis=m.unit(h-a)
        if length>=u+l:raise RuntimeError('Re-timed shoulder exceeds original reach')
        pole=m.unit(e-a-axis*np.dot(e-a,axis));along=(u*u-l*l+length*length)/(2*length)
        elbow=a+axis*along+pole*np.sqrt(max(0,u*u-along*along))
        for bones,origin,neworigin,oldvec,newvec in [
            (['upperarm_l','upperarm_twist_01_l','upperarm_twist_02_l'],a,a,e-a,elbow-a),
            (['lowerarm_l','lowerarm_twist_02_l','lowerarm_twist_01_l'],e,elbow,h-e,h-elbow)]:
            turn=m.hinge.swing(oldvec,newvec)
            for n in bones:
                i=m.ix[n];offset=w[k,i,:3,3]-origin;fraction=np.dot(offset,oldvec)/np.dot(oldvec,oldvec)
                result[k,i,:3,3]=neworigin+fraction*newvec+turn@(offset-fraction*oldvec)
                result[k,i,:3,:3]=turn@w[k,i,:3,:3]
    return result

if __name__=='__main__':
    baseline=r/'candidate_before_settle.pkl'
    if not baseline.exists():baseline.write_bytes((r/'candidate_world.pkl').read_bytes())
    data=pickle.load(open(baseline,'rb'));old=pickle.load(open(r/'corrected.pkl','rb'));post={};stats={}
    for (path,family),row in data.items():
        t=row['times'];w=row['world'];side='/SideMagazine' in path
        if not side:
            if 'quick_melee' not in path and '/Bipod/' not in path:continue
            original=old[(family,path)];weights=gaussian_filter1d(original['weights'],4.,mode='nearest')
            xidle=pickle.load(open(r/'idle_fit.pkl','rb'))[family]['parameters']
            smooth=np.array([m.correct(fr,xidle*v) for fr,v in zip(original['old'],weights)])
            # Endpoint grip must remain identical to the newly authored idle.
            for k in range(len(t)):
                boundary=min(k,len(t)-1-k);a=float(m.ease(boundary/5.))
                if a<1:smooth[k]=m.correct(original['old'][k],xidle*((1-a)*original['weights'][k]+a*weights[k]))
            post[(family,path)]=dict(times=t,world=smooth)
            continue
        end=3.14 if '_empty' in path else 3.50;start=2.76
        # Dense local interpolation preserves joint lengths and the already
        # solved elbow plane, including helper bones and bounded finger curls.
        sample=np.unique(np.r_[start,np.arange(np.ceil(start*480),np.floor(end*480)+1)/480.,end])
        local=m.encode(w);sample_w=m.world(interpolate(t,local,sample))
        relative=np.array([np.linalg.inv(m.rigid(fr[m.ix['WPN_root']]))@fr for fr in sample_w])
        hand=relative[:,m.ix['hand_l']];angle=(R.from_matrix(hand[:-1,:3,:3]/np.linalg.norm(hand[:-1,:3,:3],axis=1)[:,None,:]).inv()*R.from_matrix(hand[1:,:3,:3]/np.linalg.norm(hand[1:,:3,:3],axis=1)[:,None,:])).magnitude()
        length=np.linalg.norm(np.diff(hand[:,:3,3],axis=0),axis=1)+6.*angle
        arc=np.r_[0,np.cumsum(length)];arc/=arc[-1]
        # Only the free return is re-timed: release, insert, seat, charging,
        # camera impulses and gameplay durations remain on their existing clock.
        times=np.unique(np.r_[t,start,np.arange(np.ceil(start*240),np.floor(end*240)+1)/240.,end])
        out=m.world(interpolate(t,local,times));mask=(times>start)&(times<end)
        mapped=np.interp(progress((times[mask]-start)/(end-start)),arc,sample)
        moved=m.world(interpolate(t,local,mapped))
        for k,fr in zip(np.flatnonzero(mask),moved):
            xf=m.rigid(out[k,m.ix['WPN_root']])@np.linalg.inv(m.rigid(fr[m.ix['WPN_root']]))
            out[k,m.left_ids]=xf@fr[m.left_ids]
        post[(family,path)]=dict(times=times,world=out)
        stats[family+'/'+path.split('/')[-1]]=dict(start=start,end=end,path_preserved=True,source_map=np.c_[times[mask],mapped].tolist())
    pickle.dump(post,open(r/'post_world.pkl','wb'))
    (r/'settling.json').write_text(json.dumps(stats,indent=2))
    print('CONTACT25_RETURN_SETTLED',len(post),'clips',flush=True)
