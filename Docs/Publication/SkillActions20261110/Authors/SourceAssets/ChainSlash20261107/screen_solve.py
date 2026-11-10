"""Choose a continuous sword roll and camera depth across all four cuts."""
import json
import numpy as np
from scipy.ndimage import gaussian_filter1d
from scipy.spatial.transform import Rotation
from reviewed_path import P,FRAMES,N,obs,world,unit,blade,initial_axis,basis
from fit_motion import project

def solve(crossed=False):
    # Use one sword roll sequence for both grip lengths. Score both native hands.
    data=json.loads((P/'grip_poses.json').read_text())
    idle=world(data['Standard']['idle'])
    wp=idle['WPN_root'][:3,3];wr=idle['WPN_root'][:3,:3];wr=wr/np.linalg.norm(wr,axis=0)
    arms=[]
    for s in 'rl':
        sh,el,ha=[idle[n+'_'+s][:3,3] for n in ('upperarm','lowerarm','hand')]
        arms.append((sh,wr.T@(ha-wp),wr.T@unit(ha-el),wr.T@unit(el-sh),np.linalg.norm(ha-el),np.linalg.norm(el-sh)))
    depths=np.arange(34.,65.,4.) if crossed else np.arange(26.,53.,3.)
    depth,angle=np.meshgrid(depths,np.arange(0.,360.,6.)*np.pi/180,indexing='ij')
    depth=depth.ravel();angle=angle.ravel();M=len(depth)
    bases=np.stack([blade(np.repeat(d,N))[0] for d in depth],axis=1)
    axes=np.stack([blade(np.repeat(d,N))[1] for d in depth],axis=1)
    def evaluate(i,p,z,spin):
        across=unit(basis[i]-z*(z*basis[i]).sum(-1,keepdims=True))
        across=across*np.cos(spin[:,None])+np.cross(z,across)*np.sin(spin[:,None])
        r=np.stack([across,np.cross(z,across),z],axis=-1)
        cost=((p[:,1]-45)*.6)**2;elbows=[]
        for j,(shoulder,grip,fore,up,length,upper_length) in enumerate(arms):
            h=p+r@grip;natural=r@fore;uv=obs[i,4+2*j:6+2*j]
            ray=unit(np.array([(uv[0]-240)/176,1,(135-uv[1])/176]))
            t=h@ray
            root=np.sqrt(np.maximum(0.,length**2-((h*h).sum(-1)-t*t)))
            e0=h-natural*length
            da=t+root;db=t-root
            value=np.where(np.abs(da-e0@ray)<np.abs(db-e0@ray),da,db)
            target=unit(h-ray*np.maximum(13.,value[:,None]))
            dot=np.clip((natural*target).sum(-1),-1.,1.)
            tangent=unit(target-natural*dot[:,None])
            a=np.minimum(np.arccos(dot),np.deg2rad(16))
            fd=unit(natural*np.cos(a[:,None])+tangent*np.sin(a[:,None]));e=h-fd*length
            # Screen accuracy, a camera-safe arm diameter, and shoulder travel.
            # Prefer an elbow farther forward if the reference leaves both possible.
            err=project(e)-uv
            vis=0<uv[0]<480 and 0<uv[1]<270
            lateral=(e[:,0]-h[:,0])*(1 if j==0 else -1)
            shoulder_travel=np.linalg.norm(e-shoulder,axis=1)-upper_length
            # The reference crosses the arms in the third and fourth cut.
            # Fade the left/right order prior out before that crossing.
            order=np.clip((2307-FRAMES[i])/12,0,1)
            if crossed:
                cost+=((err**2).sum(1)*(.45 if vis else .27)**2+
                       ((np.linalg.norm(e-shoulder,axis=1)-upper_length)*.8)**2+
                       (np.maximum(25-e[:,1],0)*8)**2+(np.maximum(23-h[:,1],0)*6)**2+
                       (np.maximum(e[:,2]-h[:,2]-1,0)*8.)**2+
                       (np.maximum(np.minimum(uv[1],300)-project(e)[:,1]-20,0)*.8)**2)
                elbows.append(e)
                continue
            cost+=((err**2).sum(1)*(.90 if vis else .60)**2+
                   (np.maximum(shoulder_travel-12,0)*8)**2+
                   (np.maximum(7-lateral,0)*7*order)**2+
                   (np.maximum(e[:,1]-53,0)*8)**2+
                   ((np.linalg.norm(e-shoulder,axis=1)-upper_length)*.8)**2+
                   (np.maximum(25-e[:,1],0)*8)**2+
                   (np.maximum(23-h[:,1],0)*6)**2+
                   (np.maximum(e[:,2]-h[:,2]-3,0)*(4.5+10*(1-order)))**2+
                   (np.maximum(np.minimum(uv[1],300)-project(e)[:,1]-20,0)*.7)**2)
            elbows.append(e)
        return cost,r,np.stack(elbows,axis=1)
    scores=[];quats=[]
    for i in range(N):
        cost,r,_=evaluate(i,bases[i],axes[i],angle)
        q=Rotation.from_matrix(r).as_quat();scores.append(cost);quats.append(q)
    prev=scores[0];back=[]
    for i in range(1,N):
        dots=np.abs(quats[i-1]@quats[i].T)
        turns=2*np.arccos(np.clip(dots,0,1))
        steps=(depth[:,None]-depth[None,:])**2*3+(turns*100)**2+(np.maximum(turns-.38,0)*1800)**2
        pair=prev[:,None]+steps
        back.append(np.argmin(pair,axis=0));prev=pair.min(0)+scores[i]
    ids=[np.argmin(prev)]
    for b in reversed(back):ids.append(b[ids[-1]])
    ids=np.array(ids[::-1]);dep=gaussian_filter1d(depth[ids],2.,mode='nearest')
    spin=gaussian_filter1d(np.unwrap(angle[ids]),1.5,mode='nearest');p,z=blade(dep)
    rows=[]
    for i in range(N):
        _,r,e=evaluate(i,p[i:i+1],z[i:i+1],spin[i:i+1])
        rows.append(dict(frame=int(FRAMES[i]),p=p[i].tolist(),q=Rotation.from_matrix(r[0]).as_quat().tolist(),elbows=e[0].tolist()))
    return rows
if __name__=='__main__':
    wide=solve();crossed=solve(True)
    for a,b in zip(wide,crossed):
        f=a['frame']
        # Enter the crossed grip path while the weapon is below the image.
        weight=np.clip((f-2297)/9,0,1)
        weight=weight*weight*(3-2*weight)
        r=Rotation.from_quat(a['q']);delta=r.inv()*Rotation.from_quat(b['q'])
        a['q']=(r*Rotation.from_rotvec(delta.as_rotvec()*weight)).as_quat().tolist()
        for k in ('p','elbows'):a[k]=((1-weight)*np.array(a[k])+weight*np.array(b[k])).tolist()
    for grip in ('Standard','LongGrip'):
        (P/(grip+'-fit.json')).write_text(json.dumps(wide,separators=(',',':')))
