"""Reconstruct sewn ribbon sections after moving carriers; keep hardware rigid."""
import numpy as np
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components,dijkstra
from scipy.interpolate import CubicHermiteSpline
from scipy.ndimage import gaussian_filter1d
def unit(v):return v/np.maximum(np.linalg.norm(v,axis=-1,keepdims=True),1e-12)
def rigid_fit(source,target):
    a,b=source.mean(0),target.mean(0);u,_,vt=np.linalg.svd((source-a).T@(target-b));r=u@vt
    if np.linalg.det(r)<0:u[:,-1]*=-1;r=u@vt
    return (source-a)@r+b
def free_curve(start,end,start_tangent,end_tangent,count):
    length=np.linalg.norm(end-start)
    curve=CubicHermiteSpline([0.,1.],[start,end],[unit(start_tangent)*length*.9,unit(end_tangent)*length*.65])
    dense=curve(np.linspace(0,1,max(count*5,100)));arc=np.r_[0,np.cumsum(np.linalg.norm(np.diff(dense,axis=0),axis=1))]
    result=np.column_stack([np.interp(np.linspace(0,arc[-1],count),arc,dense[:,axis]) for axis in range(3)])
    result[0]=start;result[-1]=end;return result
def repair(original,target,faces,mask):
    # SourceModel can split positions at UV/hard-normal seams. Use a welded
    # *analysis graph* only; retain every original vertex and corner attribute.
    _,inverse=np.unique(np.round(original,4),axis=0,return_inverse=True)
    counts=np.bincount(inverse);n=len(counts)
    source=np.column_stack([np.bincount(inverse,weights=original[:,a],minlength=n)/counts for a in range(3)])
    proposed=np.column_stack([np.bincount(inverse,weights=target[:,a],minlength=n)/counts for a in range(3)])
    weights=np.bincount(inverse,weights=mask,minlength=n)/counts
    result,stats=_repair(source,proposed,inverse[faces],weights)
    stats['analysis_graph_weld_only']=True
    return result[inverse]+original-source[inverse],stats
def _repair(original,target,faces,mask):
    edges=np.concatenate([faces[:,[0,1]],faces[:,[1,2]],faces[:,[2,0]]]);edges=np.unique(np.sort(edges,axis=1),axis=0)
    graph=coo_matrix((np.ones(len(edges)),(edges[:,0],edges[:,1])),shape=(len(original),len(original))).tocsr();graph=graph+graph.T
    count,labels=connected_components(graph,directed=False);result=target.copy();stats={'ribbons':0,'rigid_hardware':0,'unclassified':0}
    for label in range(count):
        ids=np.flatnonzero(labels==label)
        if len(ids)<3 or np.min(mask[ids])>.98:continue
        local=graph[ids][:,ids];degree=np.diff(local.indptr);caps=np.flatnonzero(degree>=10)
        if len(caps)!=2 or len(ids)<150:
            # Small buckles and keepers are rigid parts, not deformable cloth.
            if len(ids)<300:
                result[ids]=rigid_fit(original[ids],target[ids]);stats['rigid_hardware']+=1
            else:stats['unclassified']+=1
            continue
        distance=dijkstra(local,directed=False,indices=int(caps[0]),unweighted=True)
        stations=np.rint(distance).astype(int)
        # Merge each cap center with its adjacent end ring.
        stations[caps[0]]=1;last=stations[caps[1]];stations[caps[1]]=last-1;stations-=1
        groups=[ids[stations==i] for i in range(stations.max()+1)]
        if any(len(g)<3 for g in groups):stats['unclassified']+=1;continue
        before=np.asarray([original[g].mean(0) for g in groups]);after=np.asarray([target[g].mean(0) for g in groups]);weights=np.asarray([mask[g].mean() for g in groups])
        fixed=np.flatnonzero(weights<.05)
        if len(fixed)>4:
            first,last=int(fixed[0]),int(fixed[-1]);smooth=gaussian_filter1d(after,1.,axis=0)
            after[first:last+1]=smooth[first:last+1]
            if first>=2:after[:first+1]=free_curve(after[0],after[first],after[first]-after[0],smooth[first+1]-smooth[first],first+1)
            if last<len(after)-3:after[last:]=free_curve(after[last],after[-1],smooth[last]-smooth[last-1],after[-1]-after[last],len(after)-last)
        else:
            ends=after[[0,-1]].copy();after=gaussian_filter1d(after,1.,axis=0);after[[0,-1]]=ends
        old_t=unit(np.gradient(before,axis=0));new_t=unit(np.gradient(after,axis=0))
        for index,g in enumerate(groups):
            axis=np.cross(old_t[index],new_t[index]);s=np.linalg.norm(axis);c=float(np.dot(old_t[index],new_t[index]))
            rotation=np.eye(3)
            if s>1e-8:
                x,y,z=axis;k=np.array([[0,-z,y],[z,0,-x],[-y,x,0]])
                rotation+=k+k@k*((1-c)/(s*s))
            result[g]=(original[g]-before[index])@rotation.T+after[index]
        stats['ribbons']+=1
    return result,stats
