"""Ranger/leather-pants paired shirt: a fitted tuck beneath the existing waistband."""
import copy,gc,sys
from pathlib import Path
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
P=Path('D:/FPS3D/FPSGAME');sys.path.insert(0,str(P/'Tools/RangerCrouchFit'));import fit
R=Path(globals().get('OUTPUT_ROOT',fit.R/'TuckedPairV2'));R.mkdir(parents=True,exist_ok=True);inputs=fit.read(fit.R/'inputs.json');pants_file=Path(globals().get('PANTS_FILE',P/'SourceAssets/TrouserFit20261018/Jason_LeatherPants.json'));pants=fit.canonical(fit.read(pants_file))
pp=np.array(pants['positions']);pf=np.array(pants['triangles'][:pants['outer_shell_triangles']]) if pants.get('outer_shell_triangles') else fit.exterior(pants);ptree=BVHTree.FromPolygons([Vector(p) for p in pp],pf.tolist(),all_triangles=True)
waist_top=float(globals().get('WAIST_TOP',99.7));waist_shift=waist_top-99.7
def build(profile):
    source=fit.read(inputs['sources'][profile]['file']);p=np.array(source['positions']);fs=np.array(source['triangles']);slots=np.array(source['triangle_materials']);colors=np.array(source['colors']);uv=np.array(source['uv']);ns_source=np.array(source['normals']);mask=fit.skin_mask(source);outer=fs[np.isin(slots%6,[0,1])]
    tree=BVHTree.FromPolygons([Vector(v) for v in p],outer.tolist(),all_triangles=True)
    values=np.where(mask,p[:,2]-(98.+waist_shift),1000.)
    d={k:copy.deepcopy(v) for k,v in source.items() if k not in ('positions','triangles','weights','normals','uv','colors','triangle_materials')}
    for k in ('positions','triangles','weights','normals','uv','colors','triangle_materials'):d[k]=[]
    lookup={};removed=0
    for fi,tri in enumerate(fs):
        poly=[]
        for a,b in zip(np.eye(3),np.roll(np.eye(3),-1,axis=0)):
            va=a@values[tri];vb=b@values[tri]
            if va>=0:poly.append(a)
            if (va>=0)!=(vb>=0):poly.append(a+va/(va-vb)*(b-a))
        if len(poly)<3:removed+=1;continue
        for j in range(1,len(poly)-1):
            bc=[poly[0],poly[j],poly[j+1]];row=[];tex=[];norm=[]
            for b in bc:
                q=b@p[tri];w=fit.norm_weights({n:sum(source['weights'][v].get(n,0)*a for v,a in zip(tri,b)) for n in set().union(*(source['weights'][v] for v in tri))});key=(*np.round(q,7),tuple(sorted((n,round(a,7)) for n,a in w.items())))
                if key not in lookup:lookup[key]=len(d['positions']);d['positions'].append(q.tolist());d['weights'].append(w);d['colors'].append((b@colors[tri]).tolist())
                row.append(lookup[key]);tex.append((b@uv[fi]).tolist());n=b@ns_source[fi];norm.append((n/max(np.linalg.norm(n),1e-12)).tolist())
            if len(set(row))<3:continue
            d['triangles'].append(row);d['uv'].append(tex);d['normals'].append(norm);d['triangle_materials'].append(source['triangle_materials'][fi])
    original=np.array(d['positions']);out=original.copy();edit=fit.skin_mask(d);weights=d['weights']
    for i in np.flatnonzero(edit):
        q=original[i];anchor,_,_,_=tree.find_nearest(Vector(q));anchor=np.array(anchor);origin=np.array([0.,.8,anchor[2] if waist_top<98.5 else min(anchor[2],waist_top)]);radial=np.r_[anchor[:2]-origin[:2],0.];radius=np.linalg.norm(radial);radial/=max(radius,1e-12)
        hit,_,fi,_=ptree.ray_cast(Vector(origin+radial*40),Vector(-radial),40)
        # A sloped waistband (jeans/cargo) needs its actual front/side section
        # even though the lowest complete ring sets the hidden cut height.
        if hit is None and waist_top<98.5:
            origin[2]=min(anchor[2],waist_top);hit,_,fi,_=ptree.ray_cast(Vector(origin+radial*40),Vector(-radial),40)
        if hit is None:raise RuntimeError('Tucked waist ray missed '+str(q))
        hit=np.array(hit);target=(hit-origin)@radial-.65+.85*float(fit.smooth((anchor[2]-100.1-waist_shift)/2.8));fade=1-float(fit.smooth((anchor[2]-102.5-waist_shift)/4.1))
        out[i]+=radial*(target-radius)*fade
        tri=pf[fi];bc=fit.bary(hit,pp[tri]);w=fit.norm_weights({n:sum(pants['weights'][v].get(n,0)*a for v,a in zip(tri,bc)) for n in set().union(*(pants['weights'][v] for v in tri))})
        weights[i]=fit.blend_weights(weights[i],w,1-float(fit.smooth((anchor[2]-102-waist_shift)/4.6)))
    faces=np.array(d['triangles']);cross=-np.cross(out[faces[:,1]]-out[faces[:,0]],out[faces[:,2]]-out[faces[:,0]]);ns=np.zeros_like(out)
    for k in range(3):np.add.at(ns,faces[:,k],cross)
    _,iv=np.unique(np.round(out,5),axis=0,return_inverse=True);acc=np.zeros((iv.max()+1,3));np.add.at(acc,iv,ns);ns=acc[iv];ns/=np.maximum(np.linalg.norm(ns,axis=1,keepdims=True),1e-12)
    for fi in np.flatnonzero(np.any(edit[faces],axis=1)):d['normals'][fi]=ns[faces[fi]].tolist()
    d['positions']=out.tolist();d['contract']='Ranger trouser pair: shirt lower edge tucked below measured native waistband; thin inner/outer offsets preserved; waistband-matched skin, upper torso and arms preserved; no WPO or body masking changes'
    d['tucked_pair']=dict(pants=globals().get('PANTS_ITEM','ue_leather_pants'),pants_source=str(pants_file),cut_height_cm=98.+waist_shift,waist_sample_top_cm=waist_top,inside_clearance_cm=.65,transition_z_cm=[102+waist_shift,106.6+waist_shift],removed_covered_faces=removed)
    path=R/'Authored/ue_field_sweater'/(profile+'.json');fit.write(path,d);print('RANGER_TUCK_AUTHORED',profile,len(d['triangles']),flush=True)
    return dict(profile=profile,item='ue_field_sweater',file=str(path),authored=str(path),vertices=len(d['positions']),triangles=len(d['triangles']),fit=d['tucked_pair'])
rows=[build(profile) for profile in ('Jason','Owner_Jason')]
fit.write(R/'authored.json',dict(completed=True,records=rows,runtime_tested=False));fit.write(R/'inputs.json',inputs)
