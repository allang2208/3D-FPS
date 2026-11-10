"""Fit the four-cut reference path with fixed grips and anatomical arm lengths.

Image landmarks constrain the visible path. Depth and hidden elbows are authored
adaptations. This optimizer is the motion construction step, not a QA test.
"""
from pathlib import Path
import json
import numpy as np
from scipy.interpolate import PchipInterpolator
from scipy.optimize import least_squares
from scipy.spatial.transform import Rotation
from scipy.sparse import lil_matrix

P=Path(__file__).resolve().parent
KEYS=np.loadtxt(P/'landmarks.csv',delimiter=',')
FRAMES=np.arange(int(KEYS[0,0]),int(KEYS[-1,0])+1)
OBS=PchipInterpolator(KEYS[:,0],KEYS[:,1:],axis=0)(FRAMES)
N=len(FRAMES); F=135/np.tan(np.deg2rad(75/2))
FLIP=np.diag([1.,-1.,1.])
HIER=json.loads((P.parent/'SwordUppercut20261003/GripRecoveryV15/inputs.json').read_text())['parents']

def unit(v):return v/np.maximum(1e-8,np.linalg.norm(v,axis=-1,keepdims=True))
def project(v):
    d=np.maximum(v[:,1],3.)
    return np.column_stack((240+F*v[:,0]/d,135-F*v[:,2]/d))
def world(rows):
    out={}
    for n,k in rows.items():
        m=np.eye(4);m[:3,:3]=Rotation.from_quat(k['q'][1:]+k['q'][:1]).as_matrix()*k['s'];m[:3,3]=k['p']
        out[n]=out[HIER[n]]@m if HIER[n] in out else m
    result={}
    for n,m in out.items():
        v=m.copy();v[:3,3]=FLIP@m[:3,3];v[:3,:3]=FLIP@m[:3,:3]@FLIP;result[n]=v
    return result
def rotations(angles):
    yaw,pitch,roll=angles.T
    z=np.stack((np.sin(yaw)*np.cos(pitch),np.cos(yaw)*np.cos(pitch),np.sin(pitch)),axis=1)
    across=np.stack((-np.cos(yaw),np.sin(yaw),np.zeros(len(yaw))),axis=1)
    x=across*np.cos(roll)[:,None]+np.cross(z,across)*np.sin(roll)[:,None]
    return np.stack((x,np.cross(z,x),z),axis=-1)

def fit(grip):
    data=json.loads((P/'grip_poses.json').read_text())[grip];w=world(data['idle'])
    wp=w['WPN_root'][:3,3];wr=w['WPN_root'][:3,:3];wr=wr/np.linalg.norm(wr,axis=0)
    arms=[]
    for side in ('r','l'):
        s,e,h=[w[n+'_'+side][:3,3] for n in ('upperarm','lowerarm','hand')]
        arms.append((s,np.linalg.norm(e-s),np.linalg.norm(h-e),wr.T@(h-wp),wr.T@unit(h-e)))
    def unpack(raw):
        x=raw.reshape(N,12);p=x[:,:3];rot=rotations(x[:,3:6]);hands=[p+rot@a[3] for a in arms]
        return x,p,rot,hands
    root=OBS[:,:2];tip=OBS[:,2:4];visible=np.clip(OBS[:,5],0,1)[:,None]
    depth=np.full(N,37.);tpdepth=depth+OBS[:,4]
    start=np.column_stack(((root[:,0]-240)*depth/F,depth,(135-root[:,1])*depth/F))
    end=np.column_stack(((tip[:,0]-240)*tpdepth/F,tpdepth,(135-tip[:,1])*tpdepth/F))
    direction=unit(end-start)
    yaw=np.unwrap(np.arctan2(direction[:,0],direction[:,1]));pitch=np.arcsin(direction[:,2])
    desired=np.column_stack((yaw,pitch,np.deg2rad(OBS[:,6])))
    def loss(raw):
        x,p,rot,hands=unpack(raw);z=rot[:,:,2]
        screen_dir=unit(project(p+z*70)-project(p));ref_dir=unit(tip-root)
        r=[(project(p)-root)*(.18+.60*visible),(screen_dir-ref_dir)*22,
           (x[:,3:6]-desired)*np.array([5.,5.,.8]),
           ((p[:,1]-37)*.17)[:,None],np.maximum(18-p[:,1],0)[:,None]*6,
           np.maximum(12-(p[:,1]-27*z[:,1]),0)[:,None]*3]
        for j,(s,upper,lower,offset,forearm) in enumerate(arms):
            h=hands[j];e=x[:,6+3*j:9+3*j];lo=unit(h-e);up=unit(e-s);natural=rot@forearm
            bendcos=(lo*natural).sum(1)
            r += [((np.linalg.norm(h-e,axis=1)-lower)*12)[:,None],
                  ((np.linalg.norm(e-s,axis=1)-upper)*2.0)[:,None],
                  (lo-natural)*9,np.maximum(np.cos(np.deg2rad(22))-bendcos,0)[:,None]*130,
                  np.maximum((lo*up).sum(1)-.92,0)[:,None]*45,
                  np.maximum(10-h[:,1],0)[:,None]*5,
                  np.maximum(7-e[:,1],0)[:,None]*3,
                  np.maximum(e[:,2]-h[:,2]-14,0)[:,None]*.8]
        per=np.concatenate(r,axis=1)
        weights=np.array([.8,.9,.8,12,12,8,.7,.7,.7,.7,.7,.7])
        return np.r_[per.ravel(),(np.diff(x,axis=0)*weights*.3).ravel(),(np.diff(x,n=2,axis=0)*weights*2.).ravel()]
    x=np.zeros((N,12));x[:,:3]=start;x[:,3:6]=desired
    rot=rotations(desired)
    for j,a in enumerate(arms):x[:,6+3*j:9+3*j]=start+rot@a[3]-(rot@a[4])*a[2]
    total=len(loss(x));per=(total-12*(2*N-3))//N
    structure=lil_matrix((total,12*N),dtype=np.int8)
    for i in range(N):structure[i*per:(i+1)*per,i*12:(i+1)*12]=1
    at=per*N
    for order in (1,2):
        for i in range(N-order):
            for k in range(12):
                for j in range(order+1):structure[at+i*12+k,(i+j)*12+k]=1
        at+=12*(N-order)
    solve=least_squares(loss,x.ravel(),jac_sparsity=structure.tocsr(),x_scale='jac',max_nfev=240,ftol=3e-5)
    x,p,rot,hands=unpack(solve.x)
    rows=[dict(frame=int(f),p=p[i].tolist(),q=Rotation.from_matrix(rot[i]).as_quat().tolist(),elbows=x[i,6:].reshape(2,3).tolist()) for i,f in enumerate(FRAMES)]
    (P/(grip+'-fit.json')).write_text(json.dumps(rows,separators=(',',':')))
    print('AUTHORED_PATH',grip,'frames',N,'solver_steps',solve.nfev,flush=True)

if __name__=='__main__':
    for grip in ('Standard','LongGrip'):fit(grip)
