"""Scoped geometric recheck of the user's crouch overlap, without starting PIE."""
import json,sys
from pathlib import Path
import numpy as np
from mathutils import Vector
P=Path('D:/FPS3D/FPSGAME');sys.path.insert(0,str(P/'Tools/RangerCrouchFit'));import fit
R=fit.R;inputs=fit.read(R/'inputs.json');pants=fit.read(R/'Authored/ue_leather_pants/LeatherPants.json');frames=[(k+'@'+str(i),s['bones']) for k,v in inputs['clips'].items() for i,s in enumerate(v['samples'])]
surfaces=fit.surfaces(pants,frames);records=[]
for profile in ('Jason','Owner_Jason'):
    d=fit.read(R/'Authored/ue_field_sweater'/(profile+'.json'));vertices=fit.gaps(d,surfaces);p=np.array(d['positions']);f=np.array(d['triangles']);slots=np.array(d['triangle_materials']);mask=fit.skin_mask(d);centers=p[f].mean(1)
    chosen=f[np.all(mask[f],axis=1)&np.isin(slots,[0,1,3,4])&(centers[:,2]<100.2)];used=np.unique(chosen);mp=np.full(len(p),-1,int);mp[used]=np.arange(len(used));chosen=mp[chosen];pp=p[used];ws=[d['weights'][i] for i in used];face_results=[]
    for name,tree,frame in surfaces:
        posed=pp if frame is None else fit.skinned(pp,ws,fit.transforms(d,frame));mid=posed[chosen].mean(1);distances=[]
        for q in mid:
            hit,_,_,_=tree.find_nearest(Vector(q));gap=float(np.linalg.norm(q-np.array(hit)));distances.append(-gap if fit.inside(tree,q) else gap)
        ds=np.array(distances);face_results.append(dict(pose=name,face_samples=len(ds),penetrating=int(sum(ds<-.025)),min_clearance_cm=float(ds.min())))
    record=dict(profile=profile,vertex_samples=vertices,triangle_centroid_samples=face_results,penetrating_vertices=sum(r['penetrating'] for r in vertices),penetrating_centroids=sum(r['penetrating'] for r in face_results),worst_vertex=min(r['min_signed_clearance_cm'] for r in vertices),worst_centroid=min(r['min_clearance_cm'] for r in face_results))
    records.append(record);print('CROUCH_FIT_CHECK',json.dumps({k:v for k,v in record.items() if k not in ('vertex_samples','triangle_centroid_samples')}),flush=True)
waist=[];ref=np.array(pants['positions']);select=ref[:,2]>77
for profile in ('LeatherPants_ShortBootsFit','LeatherPants_HighBootsFit'):
    d=fit.read(R/'Authored/ue_leather_pants'/(profile+'.json'));p=np.array(d['positions']);waist.append(dict(profile=profile,max_upper_position_delta_cm=float(np.abs(p[select]-ref[select]).max()),upper_weights_identical=all(d['weights'][int(i)]==pants['weights'][int(i)] for i in np.flatnonzero(select))))
fit.write(R/'check.json',dict(completed=True,scope='Native reference plus 9 crouch clips x 4 times; visible waist vertices and triangle centroids; closed analysis volume, no collision mesh added to assets',records=records,boot_fit_waist=waist,runtime_tested=False))
authored=fit.read(R/'authored.json')
for row in authored['records']:
    if row['item']=='ue_field_sweater':row['fit']=fit.read(row['file'])['crouch_waist_fit'];row['total_penetrating_samples']=next(r['penetrating_vertices'] for r in records if r['profile']==row['profile'])
fit.write(R/'authored.json',authored)
