"""Fit the shared sword path and both shoulder chains in the first-person camera frame."""
import json
import sys
from pathlib import Path

import numpy as np
from scipy.ndimage import gaussian_filter1d
from scipy.interpolate import BSpline
from scipy.spatial.transform import Rotation, Slerp
import torch

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parent
sys.path.insert(0,str(PROJECT))
from fit_motion import world
from reviewed_path import obs

torch.set_default_dtype(torch.float64)
torch.set_num_threads(1)
tensor = torch.as_tensor
relu = torch.relu

def normalized(v):
    return v / torch.linalg.vector_norm(v,dim=-1,keepdim=True).clamp_min(1.e-9)

def skew(v):
    x,y,z = v.unbind(-1)
    zero = torch.zeros_like(x)
    return torch.stack((zero,-z,y,z,zero,-x,-y,x,zero),-1).reshape(*v.shape[:-1],3,3)

def rotate(v):
    length = torch.linalg.vector_norm(v,dim=-1)[...,None,None]
    k = skew(v)
    return torch.eye(3) + torch.sinc(length/np.pi)*k + .5*torch.sinc(length/(2*np.pi))**2*(k@k)

def mv(m,v):
    return (m@v.unsqueeze(-1)).squeeze(-1)

def swing(a,b):
    k=skew(torch.linalg.cross(a,b))
    return torch.eye(3)+k+(k@k)/(1+(a*b).sum(-1)).clamp_min(.002)[...,None,None]

def smooth(x):
    t = np.clip(x,0,1)
    return t*t*(3-2*t)

def rotation(m):
    return m[:3,:3]/np.linalg.norm(m[:3,:3],axis=0)

def soft_limit(v,start,span):
    return np.sign(v)*(np.minimum(np.abs(v),start)+span*np.tanh(np.maximum(0,np.abs(v)-start)/span))

def choose_roll(base,p,r0,wp,arms):
    """Pick a single continuous grasp orientation, even while both hands are offscreen."""
    angles=np.deg2rad(np.arange(-180,180,6))
    spins=Rotation.from_rotvec(angles[:,None]*[[0,0,1]]).as_matrix()
    rots=base[:,None]@spins
    carry=rots@r0.T
    costs=np.zeros(rots.shape[:2])
    for _,side,s,e,h in arms:
        hand=p[:,None]+carry@(h-wp)
        elbow=hand-carry@(h-e)
        up=elbow-s
        sh=elbow-up/np.maximum(np.linalg.norm(up,axis=-1,keepdims=True),.001)*np.linalg.norm(e-s)
        costs+=np.sum(((sh-s)*[1.7,1.4,1.6])**2,-1)
        costs+=(np.maximum(0,sh[:,:,2]+.94*sh[:,:,1]+18)*6)**2
        costs+=(np.maximum(0,elbow[:,:,2]-hand[:,:,2]+4)*1.7)**2
        costs+=(np.maximum(0,20-elbow[:,:,1])*3)**2
        costs+=(np.maximum(0,(hand[:,:,0]-elbow[:,:,0])*(1 if side=='r' else -1)+3)*1.8)**2
    quats=Rotation.from_matrix(rots.reshape(-1,3,3)).as_quat().reshape(len(p),len(spins),4)
    costs[0,angles!=0]=costs[-1,angles!=0]=1.e12
    prev=costs[0];parents=[]
    for i in range(1,len(p)):
        delta=2*np.arccos(np.clip(abs(quats[i-1]@quats[i].T),0,1))
        pair=prev[:,None]+(delta*260)**2+(np.maximum(0,delta-.12)*2500)**2
        parents.append(pair.argmin(0));prev=pair.min(0)+costs[i]
    indexes=[prev.argmin()]
    for parent in parents[::-1]:indexes.append(parent[indexes[-1]])
    spin=gaussian_filter1d(np.unwrap(angles[indexes[::-1]]),4.5,mode='nearest')
    spin-=np.interp(np.arange(len(spin)),[0,len(spin)-1],[spin[0],spin[-1]-2*np.pi*round(spin[-1]/(2*np.pi))])
    return base@Rotation.from_rotvec(spin[:,None]*[[0,0,1]]).as_matrix()

class ArmFit:
    def __init__(self):
        inputs=json.loads((PROJECT/'grip_poses.json').read_text())
        self.arms=[]
        for grip,data in inputs.items():
            if grip not in ('Standard','LongGrip'):continue
            matrices=world(data['idle'])
            weapon=matrices['WPN_root']
            self.idle_p=weapon[:3,3]
            self.idle_r=rotation(weapon)
            for side in ('r','l'):
                s,e,h=[matrices[b+'_'+side][:3,3] for b in ('upperarm','lowerarm','hand')]
                self.arms.append((grip,side,s,e,h))
        self.shoulder,self.elbow,self.hand=[tensor(np.stack([a[i] for a in self.arms])) for i in (2,3,4)]
        self.side=tensor([1. if a[1]=='r' else -1. for a in self.arms])
        reflection=np.diag([1.,-1.,1.])
        rune=json.loads((PROJECT.parents[1]/'Content/ColdSteelData/rune-sword-modules.json').read_text(encoding='utf-8-sig'))['hand_fit']
        keys=['right' if a[1]=='r' else 'left' for a in self.arms]
        self.fit_roll=tensor(np.stack([reflection@Rotation.from_quat(rune.get(k+'_rotation',[0,0,0,1])).as_matrix()@reflection for k in keys]))
        self.fit_offset=tensor(np.stack([reflection@rune[k+'_offset_cm'] for k in keys]))
        self.up_len=(self.elbow-self.shoulder).norm(dim=-1,keepdim=True)
        self.fore=self.hand-self.elbow
        source=json.loads((PROJECT/'Standard-fit.json').read_text())
        p=np.array([row['p'] for row in source]);q=np.array([row['q'] for row in source])
        for i in range(1,len(q)):
            if q[i-1]@q[i]<0:q[i]*=-1
        t=np.arange(325)/120
        blend=smooth(t/.18)*(1-smooth((t-2.30)/.40))
        self.weight=tensor(blend)[:,None]
        self.idle=tensor(self.idle_p)
        self.r0=tensor(self.idle_r)
        self.pivot=mv(self.r0.T,self.hand-self.idle)*tensor([0.,0.,1.])
        # Keep the blade's on-screen direction. Beyond the picture the traverse
        # approaches a comfortable reach instead of carrying the torso after it.
        uv=p[:,[0,2]]/p[:,1,None]
        uv[:,0]=soft_limit(uv[:,0],.72,.84)
        uv[:,1]=soft_limit(uv[:,1],.53,.65)
        depth=35.5+np.clip((p[:,1]-45.)*.16,-3.,3.)
        depth-=4*np.clip(np.abs(uv[:,0])-.7,0,1)
        p=np.stack((depth*uv[:,0],depth,depth*uv[:,1]),axis=1)
        p=gaussian_filter1d(p,1.2,axis=0,mode='nearest')
        p=np.stack([np.interp(t,np.arange(len(p))/60,c) for c in p.T],axis=1)
        self.goal=tensor(self.idle_p+(p-self.idle_p)*blend[:,None])
        q=gaussian_filter1d(q,1.7,axis=0,mode='nearest')
        basis=Slerp(np.arange(len(q))/60,Rotation.from_quat(q))(t)
        r0=Rotation.from_matrix(self.idle_r)
        twist=(r0.inv()*basis).as_rotvec()
        # Slerp only at the entry and recovery. In the body the factor is 1.
        raw=(r0*Rotation.from_rotvec(twist*blend[:,None])).as_matrix()
        self.base=tensor(choose_roll(raw,self.goal.numpy(),self.idle_r,self.idle_p,self.arms))
        screen=np.stack([np.interp(t,np.arange(len(obs))/60,c) for c in obs[:,:4].T],axis=1).reshape(len(t),2,2)
        self.rays=tensor((screen-[240,135])/[176.,-176.])
        self.visible=tensor(((screen[:,:,0]>-32)&(screen[:,:,0]<512)&(screen[:,:,1]>-18)&(screen[:,:,1]<288)).astype(float))*self.weight
        self.contact=tensor(np.exp(-.5*((t[:,None]-[.30,.85,1.35,1.70])/.029)**2).max(1))[:,None,None]
        self.outside=tensor(np.stack((screen[:,:,0].min(1)>488,screen[:,:,0].max(1)<-8,screen[:,:,1].min(1)>278),axis=1).astype(float))*self.weight
        frames=np.arange(len(t))
        knots=np.r_[[0]*3,frames[::4],[frames[-1]]*3]
        self.spline=tensor(BSpline.design_matrix(frames,knots,3).toarray())
        self.controls=torch.zeros((self.spline.shape[1],6+3*len(self.arms)),requires_grad=True)

    def pose(self):
        x=(self.spline@self.controls)*self.weight
        p=self.goal+x[:,:3]*8
        r=self.base@rotate(x[:,3:6])
        carry=r@self.r0.T
        h=p[:,None]+mv(carry[:,None],self.hand-self.idle)
        v=x[:,6:].reshape(len(x),len(self.arms),3)
        self.bend=v/torch.sqrt(1+(v*v).sum(-1,keepdim=True)/np.deg2rad(18.5)**2)
        tilt=rotate(self.bend)
        f=mv(carry[:,None]@tilt,self.fore)
        e=h-f
        anchor=self.shoulder[None]+torch.stack((2.*torch.tanh(p[:,0]/22),torch.zeros_like(p[:,0]),-3.*self.weight[:,0]),1)[:,None]*self.weight[:,None]
        u=normalized(e-anchor)
        s=e-u*self.up_len
        return p,r,h,e,s,u

    def loss(self):
        p,r,h,e,s,u=self.pose()
        def sq(v):return (v*v).mean()
        def diff(v,n=1):return torch.diff(v,n=n,dim=0)
        cost=sq((p-self.goal)*tensor([1.,.60,1.]))
        tips=torch.stack((p,p+92*r[:,:,2]),dim=1)
        screen_error=tips[:,:,[0,2]]-self.rays*tips[:,:,1,None]
        cost+=sq(screen_error*self.visible[:,:,None]*tensor([.65,.70])[None,:,None])
        cost+=sq(screen_error*self.contact*1.)
        depth=tips[:,:,1]
        exits=torch.stack((relu(1.42*depth-tips[:,:,0]),relu(1.42*depth+tips[:,:,0]),relu(.82*depth+tips[:,:,2])),dim=2)
        cost+=sq(exits*self.outside[:,None]*.42)
        cost+=sq((r[:,:,2]-self.base[:,:,2])*36)+sq((r-self.base)*8)
        cost+=sq((s-self.shoulder)*tensor([1.5,1.35,1.40]))
        # Entire measured shoulder cap (8.9 cm radius) remains below the
        # expanded lower image plane with room for the held-grip adjustment.
        cost+=sq(relu(s[:,:,2]+.94*s[:,:,1]+18.)*12)
        local=mv(r.transpose(1,2)[:,None],s-p[:,None])
        fitted=p[:,None]+mv(r[:,None],self.pivot+mv(self.fit_roll,local-self.pivot)+self.fit_offset)
        cost+=sq(relu(fitted[:,:,2]+.94*fitted[:,:,1]+19.)*13)
        cost+=sq(relu(s[:,:,1]-10)*3)+sq(relu(-s[:,:,0]*self.side+7)*3)
        cost+=sq(relu(-s[:,:,1]-12)*2)
        # The first third of the arm should enter naturally from below.
        prox=s+.35*(e-s)
        cost+=sq(relu(prox[:,:,2]+.82*prox[:,:,1]+5)*2.3)
        cost+=sq(relu(20-e[:,:,1])*3.4)+sq(relu((e[:,:,2]-h[:,:,2]+2))*1.65)
        cost+=sq(relu((h[:,:,0]-e[:,:,0])*self.side+2)*1.6)
        cost+=sq(self.bend*16.)
        fore=normalized(h-e)
        elbow_cos=(u*fore).sum(-1)
        cost+=sq(relu(elbow_cos-.90)*60)+sq(relu(-elbow_cos-.45)*75)
        carry=(r@self.r0.T)[:,None]
        distal=swing(mv(carry,normalized(self.fore)),fore)@carry
        supported=mv(distal,normalized(self.elbow-self.shoulder))
        humerus=swing(supported,u)@distal
        cost+=sq(relu(.34-(supported*u).sum(-1))*125)
        cost+=sq(diff(humerus)*80)+sq(diff(humerus,2)*260)
        # Penalize spatial derivatives of the actual joints, including frames
        # well outside the crop, where screen observations cannot constrain speed.
        cost+=sq(diff(p,2)*13)+sq(diff(r,2)*280)+sq(diff(r)*55)
        cost+=sq(diff(e,2)*10)+sq(diff(s,2)*14)+sq(diff(s)*2.4)
        return cost

    def solve(self):
        opt=torch.optim.Adam([self.controls],lr=.035)
        for _ in range(520):
            opt.zero_grad();self.loss().backward();opt.step()
        opt=torch.optim.LBFGS([self.controls],max_iter=220,history_size=20,line_search_fn='strong_wolfe')
        def closure():
            opt.zero_grad();loss=self.loss();loss.backward();return loss
        opt.step(closure)
        p,r,h,e,s,u=[v.detach().numpy() for v in self.pose()]
        rows={grip:[] for grip in ('Standard','LongGrip')}
        for j in range(len(p)):
            for grip,out in rows.items():
                joints={side:dict(shoulder=s[j,k].tolist(),elbow=e[j,k].tolist()) for k,(g,side,*_) in enumerate(self.arms) if g==grip}
                out.append(dict(p=p[j].tolist(),q=Rotation.from_matrix(r[j]).as_quat().tolist(),arms=joints))
        (HERE/'arm-path.json').write_text(json.dumps(rows,separators=(',',':')))
        print('Fitted',len(p),'keys, final loss',float(self.loss().detach()),flush=True)

if __name__=='__main__':ArmFit().solve()
