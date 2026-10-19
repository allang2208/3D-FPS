"""Shared physical waist fit for the capri repair and the ST6 trousers."""
from pathlib import Path
import numpy as np
FIELD=Path('D:/FPS3D/FPSGAME/SourceAssets/ST6LowerSet20261018/waist_fit.npz')
F=None
REVISION='NativeWaistFit20261018'
def table():
    global F
    if F is None:F=np.load(FIELD)
    return F
def sample(z,t):
    f=table();z=np.asarray(z);t=np.asarray(t);zi=np.clip((z-80)/.5,0,len(f['levels'])-1.000001)
    a=np.floor(zi).astype(int);b=a+1;za=zi-a
    ti=np.mod(t,2*np.pi)/(2*np.pi)*192;i=np.floor(ti).astype(int)%192;j=(i+1)%192;ta=ti-np.floor(ti)
    ra=f['radii'][a,i]*(1-ta)+f['radii'][a,j]*ta;rb=f['radii'][b,i]*(1-ta)+f['radii'][b,j]*ta
    cy=f['centers'][a,1]*(1-za)+f['centers'][b,1]*za
    return ra*(1-za)+rb*za,cy
def fitted_torso(z,t,offset=0):
    rx=np.interp(z,[80,85,90,95,100.2],[18.3,18.7,18.3,17.7,17.1]);ry=np.interp(z,[80,85,90,95,100.2],[13.8,14.4,14.2,13.7,12.7])
    old=np.array([rx*np.sin(t),.8+ry*np.cos(t),z]);polar=np.arctan2(old[0],old[1]-.8)
    radius,cy=sample(z,polar);radius+=.55
    target=np.array([radius*np.sin(polar),cy+radius*np.cos(polar),z])
    blend=np.clip((z-85)/11,0,1);blend=blend*blend*(3-2*blend)
    result=old*(1-blend)+target*blend
    return result+offset*np.array([np.sin(polar),np.cos(polar),0])
def deform(points):
    q=np.array(points,float);out=q.copy();z=q[:,2];t=np.arctan2(q[:,0],q[:,1]-.8)
    rx=np.interp(z,[80,85,90,95,100.2],[18.3,18.7,18.3,17.7,17.1]);ry=np.interp(z,[80,85,90,95,100.2],[13.8,14.4,14.2,13.7,12.7])
    old_radius=1/np.sqrt((np.sin(t)/rx)**2+(np.cos(t)/ry)**2)
    radius,cy=sample(z,t);delta=radius+.55-old_radius
    blend=np.clip((z-85)/11,0,1);blend=blend*blend*(3-2*blend)
    out[:,0]+=delta*np.sin(t)*blend;out[:,1]+=(delta*np.cos(t)+cy-.8)*blend
    return out
def repair(data):
    if REVISION in data.get('contract',''):return data
    q=np.array(data['positions']);data['positions']=deform(q).tolist()
    eps=.002;jac=np.empty((len(q),3,3))
    for axis in range(3):
        delta=np.zeros(3);delta[axis]=eps;jac[:,:,axis]=(deform(q+delta)-deform(q-delta))/(2*eps)
    nmat=np.transpose(np.linalg.inv(jac),(0,2,1));f=np.array(data['triangles']);n=np.einsum('fcij,fcj->fci',nmat[f],np.array(data['normals']));n/=np.maximum(np.linalg.norm(n,axis=2,keepdims=True),1e-12)
    data['normals']=n.tolist();data['contract']+='; '+REVISION+': native asymmetric waist section + 5.5mm cloth clearance; shared trim deformation'
    return data
