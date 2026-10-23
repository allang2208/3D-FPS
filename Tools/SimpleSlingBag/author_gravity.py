"""Fit the retained pouch to a torso contact proxy and author its two sewn tethers."""
import hashlib
import importlib.util
import json
from pathlib import Path
import numpy as np
from scipy.spatial import cKDTree
from scipy.spatial.transform import Rotation

P=Path('D:/FPS3D/FPSGAME');BASE=P/'SourceAssets/SimpleSlingBag20261022';R=BASE/'GravityFitR3'
DEST='/Game/Characters/SimpleSlingBag20261022/GravityFitR3'
spec=importlib.util.spec_from_file_location('sling_author',P/'Tools/SimpleSlingBag/author.py')
a=importlib.util.module_from_spec(spec);spec.loader.exec_module(a);b=a.b
a.R=R;a.DEST=DEST;a.REV='SlingGravityFitR3_20261022'
body=b.read(R/'BodyInputs/body.json');refs=body['reference'];names={x['index']:x['name'] for x in body['bones']}
raw=np.load(BASE/'Authored/pouch_support.npz')['positions']
# The original cut's centroid is not the load-bearing edge of the pouch.
# Keep the seam on the retained top cap, inset from its torso-facing boundary.
top=raw[np.abs(raw[:,2]-raw[:,2].max())<.002]
strip=top[np.abs(top[:,0]-a.pouch['anchors_cm']['top'][0])<1.8]
a.pouch['anchors_cm']['top'][1]=float(strip[:,1].max()-.22)


def surface(vertices,cell=.7):
    keys=np.floor(vertices[:,[0,2]]/cell).astype(int)
    order=np.lexsort((-vertices[:,1],keys[:,1],keys[:,0]));keys=keys[order]
    return vertices[order[np.r_[True,np.any(keys[1:]!=keys[:-1],axis=1)]]]


def point_local(point,bone):
    r=refs[bone]
    return Rotation.from_quat(r[3:7]).inv().apply(point-np.array(r[:3]))/r[7:10]


def hulls(garment):
    points=[]
    for data in [body]+([garment] if garment else []):
        mesh=b.visible_mesh(data);ids=np.unique(mesh.faces);v=np.asarray(data['positions'])[ids]
        torso={x['index'] for x in data['bones'] if x['name']=='pelvis' or x['name'].startswith(('spine_','clavicle'))}
        weight=np.array([sum(w for bi,w in data['weights'][i] if bi in torso) for i in ids])
        selected=(np.abs(v[:,0])<21)&(v[:,2]>98)&(v[:,2]<151.5)&(weight>np.where(v[:,2]>132,.25,.8))
        points.append(v[selected])
    cloud=np.vstack(points);result=[];reference=[]
    angles=np.arange(12)*2*np.pi/12;normals=np.c_[np.cos(angles),np.sin(angles),np.zeros(12)]
    for low,high in [(92,112),(111,120),(119,128),(127,136),(135,144),(143,151.5)]:
        local=cloud[(cloud[:,2]>=low)&(cloud[:,2]<=high)]
        if len(local)<4:raise RuntimeError('Missing torso proxy section')
        side=np.c_[normals,-(local@normals.T).max(axis=0)-.1]
        planes=np.vstack([side,[0,0,-1,low],[0,0,1,-high]])
        bone=min(['pelvis','spine_01','spine_02','spine_03','spine_04','spine_05'],key=lambda name:abs(refs[name][2]-(low+high)/2))
        ref=refs[bone];normal_local=Rotation.from_quat(ref[3:7]).inv().apply(planes[:,:3])*ref[7:10]
        length=np.linalg.norm(normal_local,axis=1)
        local_planes=np.c_[normal_local,(planes[:,:3]@ref[:3])+planes[:,3]]/length[:,None]
        result.append(dict(bone=bone,side_planes=12,planes=local_planes.tolist()))
        reference.append(planes)
    return result,{'cells':reference}


def fit(rotation,equations):
    vertices=raw@rotation.T;support=surface(vertices)
    location=np.array([0.,-8.,123.]);direction=np.tile([0.,-1.,0.],(len(support),1))
    location[1]-=float(b.lift_required(support+location,direction,equations,.3).max())+.03
    points=support+location
    central=(np.abs(points[:,0])<11)&(points[:,2]>110)&(points[:,2]<138)
    offset=b.contact_offset(points[central],direction[central],equations,.2)
    gap=-offset[np.isfinite(offset)]
    return location,float(np.median(gap)+.3*np.percentile(gap,80)),vertices


def main():
    (R/'Authored').mkdir(parents=True,exist_ok=True)
    _,bare_hulls=hulls(None);candidates=[]
    for pitch in [-24,-18,-12,-6,0]:
        rot=Rotation.from_euler('yx',[-20,pitch],degrees=True)
        loc,score,_=fit(rot.as_matrix(),bare_hulls)
        candidates.append(dict(pitch=pitch,location=loc.tolist(),score=score+.015*abs(pitch)))
    chosen=min(candidates,key=lambda row:row['score']);rotation=Rotation.from_euler('yx',[-20,chosen['pitch']],degrees=True)
    a.rotation=rotation.as_matrix();a.quaternion=rotation.as_quat().tolist()
    a.vertices=raw@a.rotation.T;a.support=surface(a.vertices,.25)
    rows=[]
    for profile,(shirt,_,_) in b.PROFILES.items():
        garment=b.read(R/'BodyInputs'/(shirt+'.json')) if shirt else None
        collision,reference=hulls(garment);location,_,_=fit(a.rotation,reference)
        row=a.build(profile,initial_location=location,extra_clearance=.05,free_lengths=(7.,9.),soft_contact=True)
        data=b.read(Path(row['source']));part=data['parts'][0];path=np.asarray(part['path']);mask=np.asarray(data['motion_mask'])
        for material in data['materials']:
            material['asset']=material['asset'].replace('/GravityFitR3','')
        b.write(Path(row['source']),data)
        # The free spans end where their skinning is fully pinned to the body.
        stationary=[i for i,ring in enumerate(part['rows']) if max(mask[ring])<1e-6]
        tethers=[]
        for end,station in [(0,stationary[0]),(-1,stationary[-1])]:
            point=path[end];anchor=path[station];vertex=part['rows'][station][0]
            binding=[dict(bone=names[bi],local=point_local(anchor,names[bi]).tolist(),weight=w) for bi,w in data['weights'][vertex]]
            # A near-taut rest length; a small amount of slack is taken up by gravity.
            tethers.append(dict(point=point.tolist(),support=binding,length=float(np.linalg.norm(point-anchor))+.15))
        location=np.array(row['rigid_location']);support=surface(a.vertices)+location
        tree=cKDTree(support[:,[0,2]]);lo=support.min(axis=0);hi=support.max(axis=0)
        targets=np.array([[x,z] for x in np.linspace(lo[0]+1,hi[0]-1,4) for z in np.linspace(lo[2]+1,hi[2]-1,4)])
        _,indices=tree.query(targets)
        # Include the four foremost silhouette corners as well as the contact patch.
        corners=[np.argmax(support@np.array([x,1,z])) for x in [-.6,.6] for z in [-.6,.6]]
        probes=support[np.unique(np.r_[indices,corners])]
        row['hanging_pack']=dict(center=location.tolist(),tethers=tethers,hulls=collision,probes=probes.tolist())
        row['sha256']=hashlib.sha256(Path(row['source']).read_bytes()).hexdigest()
        rows.append(row)
        print('SLING_GRAVITY_FIT',profile,'location',location.tolist(),'tethers',[round(t['length'],2) for t in tethers],'probes',len(probes),flush=True)
    plan=dict(revision=a.REV,variants=rows,rotation_quat=a.quaternion,
        retained_pouch='/Game/Characters/SimpleSlingBag20261022/SM_SimpleSlingPouch.SM_SimpleSlingPouch',
        pose_candidates=candidates,selected_pitch=chosen['pitch'],runtime_tested=False,
        method='gravity-driven rigid proxy, two unilateral strap tethers, six garment-fitted torso hulls; shared pouch and strap motion field')
    b.write(R/'manifest.json',plan)


if __name__=='__main__':main()
