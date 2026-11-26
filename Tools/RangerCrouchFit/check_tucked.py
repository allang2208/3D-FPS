"""Check exposed shirt triangles; the lower tucked overlap is intentionally hidden."""
import sys,json
from pathlib import Path
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
P=Path('D:/FPS3D/FPSGAME');sys.path.insert(0,str(P/'Tools/RangerCrouchFit'));import fit
R=fit.R/'TuckedPairV2';inputs=fit.read(R/'inputs.json');pants=fit.canonical(fit.read(P/'SourceAssets/TrouserFit20261018/Jason_LeatherPants.json'));pp=np.array(pants['positions']);pf=np.array(pants['triangles'])
def segment(start,end,tri):
    ray=end-start;e1=tri[:,1]-tri[:,0];e2=tri[:,2]-tri[:,0];h=np.cross(ray,e2);det=np.einsum('ij,ij->i',e1,h);valid=abs(det)>1e-9;inv=np.zeros_like(det);inv[valid]=1/det[valid];s=start-tri[:,0];u=np.einsum('ij,ij->i',s,h)*inv;q=np.cross(s,e1);v=np.einsum('ij,ij->i',ray,q)*inv;t=np.einsum('ij,ij->i',e2,q)*inv
    return valid&(u>=-1e-7)&(v>=-1e-7)&(u+v<=1+1e-7)&(t>1e-6)&(t<1-1e-6)
def crossing(a,b):
    hit=np.zeros(len(a),bool)
    for i in range(3):hit|=segment(a[:,i],a[:,(i+1)%3],b)|segment(b[:,i],b[:,(i+1)%3],a)
    return hit
frames=[('Reference',None)]+[(k+'@'+str(i),s['bones']) for k,r in inputs['clips'].items() for i,s in enumerate(r['samples'])];prepared=[]
for name,frame in frames:
    posed=pp if frame is None else fit.skinned(pp,pants['weights'],fit.transforms(pants,frame));prepared.append((name,frame,posed,BVHTree.FromPolygons([Vector(v) for v in posed],pf.tolist(),all_triangles=True)))
records=[]
for profile in ('Jason','Owner_Jason'):
    d=fit.read(R/'Authored/ue_field_sweater'/(profile+'.json'));p=np.array(d['positions']);fs=np.array(d['triangles']);slots=np.array(d['triangle_materials']);mask=fit.skin_mask(d);selected=fs[np.all(mask[fs],axis=1)&np.isin(slots,[0,1,3,4])];tri_indices=[];coeff=[]
    for tri in selected:
        values=p[tri,2]-100.35;poly=[]
        for a,b in zip(np.eye(3),np.roll(np.eye(3),-1,axis=0)):
            va=a@values;vb=b@values
            if va>=0:poly.append(a)
            if (va>=0)!=(vb>=0):poly.append(a+va/(va-vb)*(b-a))
        for j in range(1,len(poly)-1):tri_indices.extend([tri]*3);coeff.extend([poly[0],poly[j],poly[j+1]])
    tri_indices=np.array(tri_indices);coeff=np.array(coeff);visible_faces=np.arange(len(coeff)).reshape(-1,3);rows=[]
    for name,frame,pants_pos,ptree in prepared:
        skinned=p if frame is None else fit.skinned(p,d['weights'],fit.transforms(d,frame));visible=np.einsum('ij,ijk->ik',coeff,skinned[tri_indices]);tree=BVHTree.FromPolygons([Vector(v) for v in visible],visible_faces.tolist(),all_triangles=True);pairs=np.array(tree.overlap(ptree),int).reshape(-1,2)
        if len(pairs):pairs=pairs[crossing(visible[visible_faces[pairs[:,0]]],pants_pos[pf[pairs[:,1]]])]
        contact_rest=np.einsum('ij,ijk->ik',coeff,p[tri_indices])[visible_faces[pairs[:,0]]] if len(pairs) else None
        rows.append(dict(pose=name,exposed_triangle_intersections=len(pairs),contact_rest_min=contact_rest.min((0,1)).tolist() if contact_rest is not None else None,contact_rest_max=contact_rest.max((0,1)).tolist() if contact_rest is not None else None))
    records.append(dict(profile=profile,total_intersections=sum(row['exposed_triangle_intersections'] for row in rows),samples=rows));print('TUCKED_EXPOSED_CHECK',profile,records[-1]['total_intersections'],flush=True)
boot=[]
for stem in ('Jason_LeatherPants_ShortBootsFit','Jason_LeatherPants_HighBootsFit'):
    d=fit.canonical(fit.read(P/'SourceAssets/TrouserFit20261018'/(stem+'.json')));q=np.array(d['positions']);mask=pp[:,2]>=96;boot.append(dict(profile=stem,max_waist_position_delta_cm=float(np.abs(q[mask]-pp[mask]).max()),waist_weights_equal=all(d['weights'][i]==pants['weights'][i] for i in np.flatnonzero(mask))))
fit.write(R/'check.json',dict(completed=True,scope='Visible shirt surface above100.35cm waist boundary, native reference + 36 crouch samples; lower98..100.35cm intentional under-waist overlap is concealed by existing waistband; no body/leg deletion',records=records,boot_waist=boot,runtime_tested=False))
