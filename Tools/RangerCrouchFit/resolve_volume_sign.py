"""Distinguish analysis-cap ray artifacts from actual outer-sheet penetration."""
import sys,json
from pathlib import Path
import numpy as np
from mathutils import Vector
P=Path('D:/FPS3D/FPSGAME');sys.path.insert(0,str(P/'Tools/RangerCrouchFit'));import fit
R=fit.R;inputs=fit.read(R/'inputs.json');pants=fit.read(R/'Authored/ue_leather_pants/LeatherPants.json');frames=[(k+'@'+str(i),s['bones']) for k,v in inputs['clips'].items() for i,s in enumerate(v['samples'])];surfaces={name:tree for name,tree,_ in fit.surfaces(pants,frames)}
check=fit.read(R/'check.json');rows=[]
for result in check['records'][0]['vertex_samples']:
    if not result['penetrating']:continue
    for v in result['worst_vertices']:
        if v['gap']>=-.025:continue
        tree=surfaces[result['pose']];q=np.array(v['posed']);hit,n,fi,_=tree.find_nearest(Vector(q));dot=float((q-np.array(hit))@(-np.array(n)));rest=np.array(v['rest']);rh,rn,_,_=surfaces['Reference'].find_nearest(Vector(rest));rdot=float((rest-np.array(rh))@(-np.array(rn)))
        rows.append(dict(pose=result['pose'],vertex=v['vertex'],weights=v['weights'],parity_gap=v['gap'],outer_sheet_signed_gap=dot,reference_sheet_gap=rdot,nearest_face=int(fi),analysis_cap=fi>=len(fit.exterior(pants))))
fit.write(R/'sign_diagnosis.json',rows);print(json.dumps(rows),flush=True)
