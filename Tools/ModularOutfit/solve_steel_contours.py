"""Experimental subtractive solver; not part of the production entry points.

Keeps one continuous broad shell per phalanx; native-weighted mail covers the
excluded flexion and side-contact zones. Does not edit animation or bind data.
The unconstrained 2026-09-28 result was rejected for inadequate rigid coverage;
its output is preserved as contour-unbounded-rejected.json, not applied.
"""
import numpy as np
from pathlib import Path
from original_leather_gloves import PROJECT as P,read,write
R=P/'SourceAssets/MetalGauntlet20260927/SteelGauntletV1/ArticulationSolve20260928'

def runs(values):
    indices=np.flatnonzero(values)
    return np.split(indices,np.flatnonzero(np.diff(indices)>1)+1) if len(indices) else []

def main():
    d=read(R/'Candidate/Master/M4.json');parts=read(R/'Candidate/parts.json');hits=read(R/'contour-hits-after.json')
    path=R/'contour-solution.json';solution=read(path) if path.exists() else {}
    ps=np.asarray(d['positions']);faces=np.asarray(d['triangles'])
    for part in parts:
        name=part['name']
        if name not in hits or not hits[name]:continue
        grid=np.asarray(part['author_grid']);h,w=grid.shape[:2]
        blocked=np.asarray(solution[name]['blocked'],bool) if name in solution else np.zeros((h,w),bool)
        triangles=faces[part['first_triangle']+np.asarray(hits[name])]
        centers=ps[triangles].mean(1)
        nearest=np.argmin(((centers[:,None,:]-grid.reshape((-1,3))[None,:,:])**2).sum(2),axis=1)
        for index in nearest:
            y,x=divmod(int(index),w)
            blocked[y,max(0,x-1):min(w,x+2)]=True
        lo=np.zeros(h);hi=np.zeros(h);valid=np.zeros(h,bool)
        for y in range(h):
            intervals=runs(~blocked[y])
            if not intervals:continue
            interval=max(intervals,key=len)
            if len(interval)<3:continue
            lo[y]=interval[0]+.12;hi[y]=interval[-1]-.12;valid[y]=True
        bands=runs(valid)
        if not bands:raise RuntimeError('No rigid core fits the sampled motion: '+name)
        band=max(bands,key=lambda b:sum(hi[b]-lo[b]))
        if len(band)<3:raise RuntimeError('Motion constraints leave no continuous plate: '+name)
        first,last=int(band[0]),int(band[-1])
        # Smooth inward only. Never grow a neighbouring row back into the
        # motion exclusion that the previous solve already removed.
        for _ in range(2):
            lo[first+1:last]=np.maximum(lo[first+1:last],(lo[first:last-1]+lo[first+2:last+1])*.5)
            hi[first+1:last]=np.minimum(hi[first+1:last],(hi[first:last-1]+hi[first+2:last+1])*.5)
        solution[name]=dict(row_range=[first,last],lo=lo.tolist(),hi=hi.tolist(),blocked=blocked.tolist(),method='motion-constrained continuous shell; flexible mail in excluded zones')
        print('STEEL_CONTOUR_SOLUTION',name,'rows',first,last,'of',h,'mean_width_fraction',round(float(np.mean((hi-lo)[first:last+1])/(w-1)),3),flush=True)
    write(path,solution)
if __name__=='__main__':main()
