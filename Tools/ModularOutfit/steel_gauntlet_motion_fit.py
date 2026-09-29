"""Build per-phalanx motion envelopes without ray hits on another phalanx."""
from pathlib import Path
import numpy as np
from mathutils.bvhtree import BVHTree
from original_leather_gloves import PROJECT as P,read
R=P/'SourceAssets/MetalGauntlet20260927/SteelGauntletV1'
CACHE=None
def matrix(b):
    m=np.eye(4);m[:3,:3]=np.asarray(b['axes']).T;m[:3,3]=b['position'];return m
def inputs():
    global CACHE
    if CACHE is None:
        CACHE=[]
        for profile in ('M4','M1911','DW715'):
            d=read(R/'Sources'/f'{profile}.json');motion=read(R/'ArticulationSolve20260928'/f'{profile}_motion.json')
            samples=[sample for clip in motion['clips'] for sample in clip['samples']]
            names=set(b for w in d['weights'] for b in w)
            transforms={n:np.asarray([matrix(sample['bones'][n]) for sample in samples]) for n in names}
            CACHE.append((profile,d,transforms))
    return CACHE

def section_trees(master,bone):
    trees=[]
    for profile,d,transforms in inputs():
        weight=np.array([w.get(bone,0.) for w in d['weights']])
        all_faces=np.asarray(d['triangles'])
        # The entire old digit included folded neighbouring phalanges. This
        # owner restriction prevents a ray from treating them as its own skin.
        faces=all_faces[weight[all_faces].mean(1)>.62]
        ids=np.unique(faces);remap=np.full(len(weight),-1);remap[ids]=np.arange(len(ids));faces=remap[faces]
        ps=np.asarray(d['positions'])[ids];ws=[d['weights'][i] for i in ids]
        pose_to_master=matrix(master['bones'][bone])[None,:,:]@np.linalg.inv(transforms[bone])
        clouds=np.zeros((len(pose_to_master),len(ids),3))
        for name in set(b for w in ws for b in w):
            weights=np.array([w.get(name,0.) for w in ws])
            tr=pose_to_master@transforms[name]@np.linalg.inv(matrix(d['bones'][name]))
            clouds+=(np.einsum('fij,vj->fvi',tr[:,:3,:3],ps)+tr[:,:3,3,None].transpose(0,2,1))*weights[None,:,None]
        # Select geometrically distinct constraints from every 24 Hz input.
        # Selection is per phalanx, so a moving little finger cannot be masked
        # by an otherwise nearly static wrist or by the weapon root motion.
        descriptor=clouds[:,::max(1,len(ids)//30),:].reshape((len(clouds),-1))
        chosen=[0];distance=np.full(len(clouds),np.inf)
        for _ in range(23):
            distance=np.minimum(distance,((descriptor-descriptor[chosen[-1]])**2).sum(1))
            index=int(np.argmax(distance))
            if distance[index]<.0004:break
            chosen.append(index)
        for i in chosen:trees.append(BVHTree.FromPolygons(clouds[i].tolist(),faces.tolist(),all_triangles=True))
        print('STEEL_SECTION_ENVELOPE',bone,profile,'motion_samples',len(clouds),'distinct',len(chosen),'core_faces',len(faces),flush=True)
    return trees
