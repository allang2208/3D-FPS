"""Offline articulated-whip authoring, using minimum-jerk root primitives.

Reference: Moses C. Nah / MIT NEWMAN LAB, whip-project-targeting (BSD-3).
The monster model and controller below are independently authored for its
original centreline; no target position drives the distal chain during release.
"""
from pathlib import Path
import sys,json,math
ROOT=Path('D:/FPS3D/FPSGAME');OUT=ROOT/'SourceAssets/BoundCongregateMeshy20261006/TentacleWhipV4'
sys.path.insert(0,str(ROOT/'Saved/BoundCongregateWhipRuntime'))
import numpy as np,mujoco

data=np.load(OUT.parent/'TentacleRepairV2/partition.npz');curve=data['curve'].copy()
def smooth(x):
    x=np.clip(x,0,1);return x*x*x*(10+x*(-15+6*x))
def contact_fade(z):
    a=np.clip((z+.27)/.04,0,1);b=np.clip((-.04-z)/.04,0,1)
    return a*a*(3-2*a)*b*b*(3-2*b)
curve[:,1]-=.014*contact_fade(curve[:,2])
arc=np.r_[0.,np.cumsum(np.linalg.norm(np.diff(curve[:,:3],axis=0),axis=1))]
distance=np.linspace(0,arc[-1],58)
raw=np.column_stack([np.interp(distance,arc,curve[:,i]) for i in range(4)])
# Anatomical coordinates: forward, right, up, metres.
nodes=np.column_stack([-raw[:,1],raw[:,0],raw[:,2]+.532125])*2.25
radii=raw[:,3]*2.25
anchor=7;p=nodes[anchor:];N=len(p)-1
rest_nodes=p.copy()
lengths=np.linalg.norm(np.diff(p,axis=0),axis=1)
# Active preparation places the organ in one rearward loop. The following
# forward throw is passive dynamics, driven only at its thick proximal end.
theta=np.deg2rad(np.linspace(120,200,N))
p=np.vstack([rest_nodes[0],rest_nodes[0]+np.cumsum(np.column_stack([np.cos(theta),np.zeros(N),np.sin(theta)])*lengths[:,None],axis=0)])

def make_model(stiffness=5.,bend_damping=.8,handle=10,gravity=-9.81,body=True):
    lines=[f'<mujoco model="CongregateWhip"><compiler angle="radian"/><option timestep="0.0001" integrator="RK4" gravity="0 0 {gravity}"/><default><geom contype="1" conaffinity="0" friction=".15 .01 .001"/></default><worldbody><geom type="plane" size="20 20 .1" contype="0" conaffinity="1"/>',
           ('<geom name="body_clearance" type="ellipsoid" size="1.2 .95 .9" pos="0 0 1.05" contype="0" conaffinity="1"/>' if body else ''),
           '<body name="driver" pos="'+' '.join(map(str,p[0]))+'"><joint name="drive" type="hinge" axis="0 1 0" armature=".2"/>']
    for i in range(N):
        offset=np.zeros(3) if i==0 else p[i]-p[i-1];d=p[i+1]-p[i];L=np.linalg.norm(d)
        r=float(radii[anchor+i]);mass=max(.012,1000*math.pi*r*r*L)
        K=stiffness*max(.015,1e4*math.pi*r**4/4/L)
        damping=bend_damping*math.sqrt(K*mass*L*L)
        lines.append(f'<body name="link{i}" pos="'+ ' '.join(map(str,offset))+'">')
        if i>=handle:lines.append(f'<joint name="bend{i}" type="ball" stiffness="{K}" damping="{damping}" armature="0.0001"/>')
        lines.append(f'<geom type="capsule" size="{max(.004,r*.25)}" fromto="0 0 0 '+ ' '.join(map(str,d))+f'" mass="{mass}"/>')
    lines.append('<site name="tip" pos="'+' '.join(map(str,p[-1]-p[-2]))+'"/>')
    lines+=['</body>']*(N+1);lines+=['</worldbody></mujoco>']
    xml=''.join(lines);(OUT/'whip_model.xml').write_text(xml)
    m=mujoco.MjModel.from_xml_string(xml);return m

def simulate(front=1.4,windup=0.,release=.22,stiffness=5.,damping=200.,bend_damping=.8,handle=10,gravity=-9.81,body=True):
    m=make_model(stiffness,bend_damping,handle,gravity,body);d=mujoco.MjData(m);mujoco.mj_forward(m,d)
    ids=[mujoco.mj_name2id(m,mujoco.mjtObj.mjOBJ_BODY,f'link{i}') for i in range(N)]
    tip=mujoco.mj_name2id(m,mujoco.mjtObj.mjOBJ_SITE,'tip')
    frames=[];angles=[]
    for step in range(int((windup+1.4)/m.opt.timestep)+1):
        t=step*m.opt.timestep
        angle=front*float(smooth((t-windup)/release))
        u=np.clip((t-windup)/release,0.,1.)
        velocity=front/release*(30*u*u-60*u**3+30*u**4)
        d.qfrc_applied[0]=1200*(angle-d.qpos[0])+damping*(velocity-d.qvel[0])
        mujoco.mj_step(m,d)
        if step%80==0:
            frames.append(np.vstack([d.xpos[ids],d.site_xpos[tip]]).copy());angles.append(float(d.qpos[0]))
    for warning in [mujoco.mjtWarning.mjWARN_BADQPOS,mujoco.mjtWarning.mjWARN_BADQVEL,mujoco.mjtWarning.mjWARN_BADQACC]:
        if d.warning[warning].number:raise RuntimeError('Unstable whip simulation; do not bake')
    if not np.isfinite(frames).all():raise RuntimeError('Nonfinite physical pose')
    return np.array(frames),np.array(angles)

if __name__=='__main__':
    poses,angles=simulate()
    np.savez_compressed(OUT/'whip_simulation.npz',poses=poses,angles=angles,nodes=nodes,radii=radii,preload=p,dt=.008,windup=1.1,release=.22,anchor=anchor)
    print(json.dumps({'frames':len(poses),'tip_min':poses[:,-1].min(0).tolist(),'tip_max':poses[:,-1].max(0).tolist(),'tip_samples':{str(t):poses[min(len(poses)-1,round(t/.008)),-1].tolist() for t in [0,.2,.4,.6,.8,1.,1.2,1.4]}}),flush=True)
