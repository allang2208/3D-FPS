"""Bounded combined elbow/relaxed-thumb search; no production changes."""
import json,numpy as np
from pathlib import Path
P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/ModularOutfit20260926/FingerlessHuntV2';arm={};thumb={}
exec((P/'Tools/ModularOutfit/solve_fingerless_cuff_arm_clearance.py').read_text().split('manifest=[]')[0],arm)
exec((P/'Tools/ModularOutfit/solve_fingerless_thumb_cuff_clearance.py').read_text().split('files=')[0],thumb)
d=json.loads((R/'ClearanceAfter/A762__base_reload_empty_poses.json').read_text());gd=json.loads((R/'ClearanceAfter/A762_glove.json').read_text());ids={b['index']:n for n,b in gd['bones'].items()};parents={n:ids.get(b['parent']) for n,b in gd['bones'].items()};result=[]
for i,p in enumerate(d['poses']):
    before=thumb['evaluate'](p['bones'])
    if before<=.03:continue
    candidates=[]
    for angle in (0,10,-10,20,-20,30,-30,40,-40,50,-50,60,-60,75,-75,90,-90):
        bones=arm['orbit'](p['bones'],angle,parents);candidates.append((thumb['evaluate'](bones),angle,bones))
    best=min(candidates,key=lambda x:x[0]);chosen=(best[1],0,[0.,0.,1.]);depth=best[0]
    for score,angle,bones in sorted(candidates,key=lambda x:x[0])[:8]:
        for rot,axis in [(a,np.array([0.,np.cos(t),np.sin(t)])) for a in (4,8,12,16,20,25,30) for t in np.arange(0,2*np.pi,np.pi/4)]:
            test=thumb['evaluate'](thumb['change'](bones,axis,rot))
            if test<depth:depth=test;chosen=(angle,rot,axis.tolist())
            if depth<=.005:break
        if depth<=.005:break
    print('COMBINED_CUFF_PROBE',i,before,depth,chosen,flush=True);result.append(dict(index=i,before=before,after=depth,correction=chosen))
(R/'ClearanceAfter/combined-cuff-probe.json').write_text(json.dumps(result,indent=2))
