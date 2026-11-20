"""Compare the installed shotgun glove and the repaired mesh on saved action samples."""
import gzip
import json
from pathlib import Path

import numpy as np
from scipy.spatial import cKDTree
from scipy.spatial.transform import Rotation

from native_glove_author import R, FINGERS, read, hand_zone
from native_glove_profile import GUNS, SOURCE_FILE

def matrices(transforms):
    ts = np.array(transforms)
    mat = np.broadcast_to(np.eye(4), (len(ts),4,4)).copy()
    mat[:,:3,:3] = Rotation.from_quat(ts[:,3:7]).as_matrix()*ts[:,None,7:10]
    mat[:,:3,3] = ts[:,:3]
    return mat

def component(local, parents):
    out = matrices(local)
    for i,p in enumerate(parents):
        if p>=0:
            out[i] = out[p]@out[i]
    return out

class Skin:
    def __init__(self, mesh, names, digits_only):
        bone_rows = mesh['bones']
        if isinstance(bone_rows,list):
            bone_rows = {b['name']:b for b in bone_rows}
        reference = {}
        for n,b in bone_rows.items():
            ref=np.eye(4)
            ref[:3,:3]=np.array(b['axes']).T
            ref[:3,3]=b['position']
            reference[n]=np.linalg.inv(ref)
        self.points=np.array(mesh['positions'])
        self.faces=np.array(mesh['triangles'])
        self.mats=np.array(mesh['triangle_materials'])
        self.all_weights=mesh['weights']
        if isinstance(self.all_weights[0],list):
            indexed={b['index']:n for n,b in bone_rows.items()}
            self.all_weights=[{indexed[i]:w for i,w in weights} for weights in self.all_weights]
        self.zones=np.array(['/'.join(hand_zone(w)) for w in self.all_weights])
        if digits_only:
            sections=np.unique(self.faces[self.mats<=2]) if mesh.get('equipment',False) else np.arange(len(self.points))
            self.ids=np.intersect1d(sections,np.flatnonzero([s.split('/')[1] in FINGERS for s in self.zones]))
            # Uniform by native point rather than duplicated UV/normal wedges.
            _,ids=np.unique(np.round(self.points[self.ids],5),axis=0,return_index=True)
            self.ids=self.ids[ids]
        else:
            self.ids=np.arange(len(self.points))
        self.groups=[]
        rig={n:i for i,n in enumerate(names)}
        indices={}
        for j,i in enumerate(self.ids):
            for n,w in self.all_weights[i].items():
                indices.setdefault(n,[]).append((j,w))
        for n,items in indices.items():
            ix=np.array([j for j,w in items])
            factors=np.array([w for j,w in items])
            p=np.column_stack((self.points[self.ids[ix]],np.ones(len(ix))))
            self.groups.append((rig[n],ix,(p@reference[n].T)*factors[:,None]))
        self.region={k:np.where(self.zones[self.ids]==k)[0] for k in np.unique(self.zones[self.ids])}

    def skin(self,component_pose):
        out=np.zeros((len(self.ids),3))
        for bi,idx,local in self.groups:
            out[idx]+=local@component_pose[bi,:3].T
        return out

def review():
    old=read(R/'Read/R4.json')
    saved=R/'Read/Installed.json'
    new=read(saved) if saved.exists() else read(SOURCE_FILE)
    if 'bones' not in new:
        new['bones']=old['bones']
    old['equipment']=new['equipment']=True
    results={}
    for gun in GUNS:
        native=read(R/'Read'/(gun+'_Jason.json'))
        pose=json.load(gzip.open(R/'Read'/(gun+'_poses.json.gz'),'rt'))
        names=pose['names']
        parents=[names.index(n) if n in names else -1 for n in pose['parents']]
        ns,os,cs=[Skin(mesh,names,True) for mesh in (native,old,new)]
        gun_result={}
        for clip,animation in pose['clips'].items():
            measures=[[],[]]
            for local in animation['local']:
                c=component(local,parents)
                skin=ns.skin(c)
                previous,current=os.skin(c),cs.skin(c)
                distance=[[],[]]
                for region,ni in ns.region.items():
                    tree=cKDTree(skin[ni])
                    for i,(v,s) in enumerate([(previous,os),(current,cs)]):
                        distance[i].append(tree.query(v[s.region[region]])[0])
                for history,dist in zip(measures,distance):
                    history.append(np.percentile(np.concatenate(dist),[50,95,99]))
            gun_result[clip]=dict(samples=len(animation['local']),old_peak_p95_cm=float(np.max(np.array(measures[0])[:,1])),
                                  new_peak_p95_cm=float(np.max(np.array(measures[1])[:,1])))
        results[gun]=gun_result
    (R/'posed-fit.json').write_text(json.dumps(results,indent=2),encoding='utf8')
    for gun,clips in results.items():
        print(gun,len(clips),sum(c['samples'] for c in clips.values()),'old worst p95',max(c['old_peak_p95_cm'] for c in clips.values()),'new worst p95',max(c['new_peak_p95_cm'] for c in clips.values()))

if __name__=='__main__':
    review()
