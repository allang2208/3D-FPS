"""Fit a changed/new shirt to the accepted gravity sling without changing its design."""
import copy
import numpy as np
from scipy.spatial.transform import Rotation
def update_hanging(recipe,translation,deform_native,surface,bones,native):
    result=copy.deepcopy(recipe)
    result['center']=(np.asarray(result['center'])+translation).tolist()
    result['probes']=(np.asarray(result['probes'])+translation).tolist()
    by_name={b['name']:b for b in bones}
    for tether in result['tethers']:
        point=np.asarray(tether['point']);before=np.zeros(3);after=np.zeros(3)
        for support in tether['support']:
            bone=by_name[support['bone']];matrix=Rotation.from_quat(bone['rotation']).as_matrix();position=np.asarray(bone['position'])
            p=np.asarray(support['local'])@matrix.T+position;moved=p+deform_native(p[None,:])[0]
            support['local']=((moved-position)@matrix).tolist();before+=p*support['weight'];after+=moved*support['weight']
        slack=max(0,tether['length']-np.linalg.norm(point-before));tether['point']=(point+translation).tolist()
        tether['length']=float(np.linalg.norm(point+translation-after)+slack)
    z=surface['polar_z'];angles=surface['angles'];r=surface['radius'];c=surface['centers']
    cloud=np.stack([c[:,0,None]+r*np.cos(angles),c[:,1,None]+r*np.sin(angles),np.broadcast_to(z[:,None],r.shape)],axis=-1).reshape(-1,3)
    cloud=native(cloud[np.all(np.isfinite(cloud),axis=1)])
    edges=np.linspace(by_name['pelvis']['position'][2],by_name['neck_01']['position'][2]+2,7)
    angles=np.arange(12)*np.pi/6;normals=np.c_[np.cos(angles),np.sin(angles),np.zeros(12)];hulls=[]
    for a,b in zip(edges[:-1],edges[1:]):
        a-=.5;b+=.5;s=cloud[(cloud[:,2]>=a)&(cloud[:,2]<=b)]
        if len(s)<4:raise RuntimeError('Incomplete native sling torso band')
        planes=np.vstack([np.c_[normals,-(s@normals.T).max(0)-.1],[0,0,-1,a],[0,0,1,-b]])
        name=min(('pelvis','spine_01','spine_02','spine_03','spine_04','spine_05'),key=lambda n:abs(by_name[n]['position'][2]-(a+b)*.5))
        bone=by_name[name];matrix=Rotation.from_quat(bone['rotation']).as_matrix();ns=planes[:,:3]@matrix;ds=planes[:,3]+planes[:,:3]@bone['position']
        hulls.append({'bone':name,'side_planes':12,'planes':(np.c_[ns,ds]/np.linalg.norm(ns,axis=1)[:,None]).tolist()})
    result['hulls']=hulls;return result
