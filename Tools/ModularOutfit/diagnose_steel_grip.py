"""Locate plate/liner and plate/plate crossings in the reported pistol grip."""
import sys
from collections import Counter
from pathlib import Path
import numpy as np
from mathutils.bvhtree import BVHTree
sys.path.insert(0,str(Path(__file__).resolve().parent))
from original_leather_gloves import PROJECT as P,read,write

R=P/'SourceAssets/MetalGauntlet20260927/SteelGauntletV1'
def matrix(b):
    m=np.eye(4);m[:3,:3]=np.asarray(b['axes']).T;m[:3,3]=b['position'];return m
def deform(d,bones):
    ps=np.asarray(d['positions']);out=np.zeros_like(ps)
    for name in {b for ws in d['weights'] for b in ws}:
        ids=np.asarray([i for i,w in enumerate(d['weights']) if name in w])
        ws=np.asarray([d['weights'][i][name] for i in ids])
        tr=matrix(bones[name])@np.linalg.inv(matrix(d['bones'][name]))
        out[ids]+=(ps[ids]@tr[:3,:3].T+tr[:3,3])*ws[:,None]
    return out
def tree(p,t):
    used=np.unique(t);remap=np.full(len(p),-1);remap[used]=np.arange(len(used))
    return BVHTree.FromPolygons(p[used].tolist(),remap[t].tolist(),all_triangles=True)
def crosses(pa,ta,pb,tb,trees):
    pairs=trees[0].overlap(trees[1])
    if not pairs:return 0,0.
    ids=np.asarray(pairs);a=pa[ta[ids[:,0]]];b=pb[tb[ids[:,1]]]
    an=np.cross(a[:,1]-a[:,0],a[:,2]-a[:,0]);bn=np.cross(b[:,1]-b[:,0],b[:,2]-b[:,0])
    an/=np.maximum(np.linalg.norm(an,axis=1)[:,None],1e-14);bn/=np.maximum(np.linalg.norm(bn,axis=1)[:,None],1e-14)
    da=np.einsum('nki,ni->nk',a-b[:,0,None,:],bn);db=np.einsum('nki,ni->nk',b-a[:,0,None,:],an)
    depths=np.minimum.reduce([-da.min(1),da.max(1),-db.min(1),db.max(1)])
    return int((depths>.002).sum()),float(max(0,depths.max())*10)
def main():
    dest=R/'GripFix';poses=read(dest/'DW715_poses.json')
    if '--candidate' in sys.argv:
        from derive_steel_gauntlet_family import rotation
        master=read(R/'HandBackDiagnosis/Candidate/Master/M4.json')
        parts=read(R/'HandBackDiagnosis/Candidate/parts.json');d=read(R/'Sources/DW715.json')
        for part in parts:
            bn=part['bone'];rot=rotation(d['bones'][bn])@rotation(master['bones'][bn]).T
            vi=part['first_vertex'];nv=part['vertices'];fi=part['first_triangle'];nf=part['triangles'];start=len(d['positions'])
            d['positions'].extend(((np.asarray(master['positions'][vi:vi+nv])-master['bones'][bn]['position'])@rot.T+d['bones'][bn]['position']).tolist())
            d['weights'].extend({bn:1.} for _ in range(nv))
            d['triangles'].extend((np.asarray(master['triangles'][fi:fi+nf])-vi+start).tolist());d['triangle_materials'].extend([1]*nf)
    else:
        d=read(R/'Authored/DW715.json');parts=read(R/'parts.json')
    saved=read(dest/'DW715_saved_before.json')
    metal={v for f,m in zip(saved['triangles'],saved['triangle_materials']) if m==1 for v in f}
    rigid=Counter(len(saved['weights'][v]) for v in metal)
    print('SAVED_STEEL_WEIGHTS',dict(rigid),flush=True)
    t=np.asarray(d['triangles']);skin=t[np.asarray(d['triangle_materials'])==0]
    plates=[]
    for part in parts:
        if part['kind']=='steel_plate':
            start=part['first_triangle'];plates.append((part['name'],t[start:start+part['triangles']]))
    report=dict(saved_steel_weight_counts=dict(rigid),states={})
    for label,pose in [('rest',None),*poses.items()]:
        p=deform(d,pose['bones']) if pose else np.asarray(d['positions'])
        liner=[];metal_cross=[]
        skin_tree=tree(p,skin);plate_trees={name:tree(p,faces) for name,faces in plates}
        for i,(name,faces) in enumerate(plates):
            count,depth=crosses(p,skin,p,faces,(skin_tree,plate_trees[name]))
            if count:
                side=name[-1]
                own=np.asarray([sum(v for b,v in w.items() if b.endswith('_'+side))>.5 for w in d['weights']])
                same=skin[own[skin].all(1)]
                own_count,own_depth=crosses(p,same,p,faces,(tree(p,same),plate_trees[name]))
                liner.append(dict(part=name,pairs=count,plane_cross_mm=depth,same_hand_pairs=own_count,same_hand_mm=own_depth))
            for other,otherfaces in plates[i+1:]:
                count,depth=crosses(p,faces,p,otherfaces,(plate_trees[name],plate_trees[other]))
                if count:metal_cross.append(dict(parts=[name,other],pairs=count,plane_cross_mm=depth))
        liner.sort(key=lambda r:r['pairs'],reverse=True);metal_cross.sort(key=lambda r:r['pairs'],reverse=True)
        report['states'][label]=dict(liner=liner,plates=metal_cross)
        print('GRIP_STATE',label,'LINER',liner[:10],'PLATES',metal_cross[:12],flush=True)
    label='candidate' if '--candidate' in sys.argv else 'after' if '--after' in sys.argv else 'before'
    write(dest/('crossings-'+label+'.json'),report)
if __name__=='__main__':main()
