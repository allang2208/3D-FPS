"""Native waist fitting for short tops, preserving their materials and upper body.

Uses the same tucked overlap and waistband weight transfer as the accepted
ranger/leather pair. Run with Blender background; no poses or rendering.
"""
import copy, gc, hashlib, json, sys
from pathlib import Path
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/GarmentWaist20261023'
sys.path.insert(0,str(P/'Tools/RangerCrouchFit'));import fit
read=fit.read;write=fit.write
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def disk(p):return P/'Content'/(p.split('.')[0][6:]+'.uasset')
inv=read(R/'inventory.json');old=read(P/'SourceAssets/PantsCompatibility20261022/inventory.json')
policies=read(P/'Tools/GarmentWaist/policies.json')
previous={r['asset']:r for r in old['meshes']}
for path,digest in inv['asset_sha256'].items():
    if previous.get(path,{}).get('asset_sha256')!=digest:raise RuntimeError('Refresh PantsCompatibility before fitting changed trousers: '+path)
base=read(P/'SourceAssets/PantsCompatibility20261022/authored.json')
groups=copy.deepcopy(base['groups']);routes=copy.deepcopy(base['routes'])
# The accepted leather waist is still a separate guide; never replace its
# approved ranger pair merely because a different shirt is being fitted.
leather=P/'SourceAssets/RangerLeatherPants20261021/RealisticCutV3/Authored/ue_leather_pants/Jason.json'
groups['leather_v3']=dict(guide=str(leather),waist_top_cm=99.7,items=['ue_leather_pants'])
for path,row in routes.items():
    if row.get('reused'):row['signature']='leather_v3'
default=base['default_signature']
groups[default]=dict(guide=str(P/'SourceAssets/PantsCompatibility20261022/Guides'/(default+'.json')),waist_top_cm=min(g['waist_top_cm'] for g in groups.values()),items=['fallback'])
algorithm=hashlib.sha256((sha(__file__)+sha(P/'Tools/GarmentWaist/policies.json')).encode()).hexdigest();records=[];audit=[]

def prepare(source):
    d=copy.deepcopy(source);fs=d['triangles'];colors=d.get('colors')
    # Preserve discontinuous per-corner colors used by clothing motion masks.
    if colors and isinstance(colors[0][0],list):
        lookup={};positions=[];weights=[];vertex_colors=[];faces=[]
        for fi,face in enumerate(fs):
            row=[]
            for ci,vi in enumerate(face):
                key=(vi,*colors[fi][ci])
                if key not in lookup:
                    lookup[key]=len(positions);positions.append(d['positions'][vi]);weights.append(d['weights'][vi]);vertex_colors.append(colors[fi][ci])
                row.append(lookup[key])
            faces.append(row)
        d.update(positions=positions,weights=weights,colors=vertex_colors,triangles=faces)
    elif not colors:d['colors']=[[1.,1.,1.,1.] for _ in d['positions']]
    return d

def build(row,signature,group):
    file=R/'Fits'/signature/'Authored'/row['item']/(row['profile']+'.json')
    receipt=file.with_suffix('.receipt.json')
    if file.exists() and receipt.exists():
        cached=read(receipt)
        if sha(file)==cached['record']['author_sha256']:
            audit.append(cached['audit']);print('GARMENT_WAIST_REUSED',row['item'],signature,row['profile'],flush=True);return cached['record']
    source=prepare(read(row['file']));p=np.array(source['positions']);fs=np.array(source['triangles'],int)
    top=group['waist_top_cm'];cut=top-1.7;shift=top-99.7
    mask=fit.skin_mask(source)
    # A short hem must be extended before clipping, otherwise a tucked variant
    # could remain above a low trouser waistband and expose a gap.
    hem=float(p[mask,2].min());extension=max(0.,hem-cut)
    if extension:p[mask,2]-=extension*(1-fit.smooth((p[mask,2]-hem)/5.))
    slots=np.array(source['triangle_materials']);uv=np.array(source['uv']);normals=np.array(source['normals']);colors=np.array(source['colors'])
    outer_slots=policies['shirts'][row['item']]['outer_slots'][row['profile']]
    outer=fs[np.isin(slots,outer_slots)]
    tree=BVHTree.FromPolygons([Vector(v) for v in p],outer.tolist(),all_triangles=True)
    pants=fit.canonical(read(group['guide']));pp=np.asarray(pants['positions']);pf=np.asarray(pants['triangles'][:pants['outer_shell_triangles']],int)
    ptree=BVHTree.FromPolygons([Vector(v) for v in pp],pf.tolist(),all_triangles=True)
    values=np.where(mask,p[:,2]-cut,1000.)
    fields=('positions','triangles','weights','normals','uv','colors','triangle_materials')
    d={k:copy.deepcopy(v) for k,v in source.items() if k not in fields}
    for key in fields:d[key]=[]
    lookup={}
    for fi,tri in enumerate(fs):
        poly=[]
        for a,b in zip(np.eye(3),np.roll(np.eye(3),-1,axis=0)):
            va=a@values[tri];vb=b@values[tri]
            if va>=0:poly.append(a)
            if (va>=0)!=(vb>=0):poly.append(a+va/(va-vb)*(b-a))
        for j in range(1,len(poly)-1):
            indices=[];tex=[];ns=[]
            for b in [poly[0],poly[j],poly[j+1]]:
                q=b@p[tri];color=b@colors[tri]
                w=fit.norm_weights({n:sum(source['weights'][v].get(n,0)*a for v,a in zip(tri,b)) for n in set().union(*(source['weights'][v] for v in tri))})
                key=(*np.round(q,7),*np.round(color,7),tuple(sorted((n,round(v,7)) for n,v in w.items())))
                if key not in lookup:
                    lookup[key]=len(d['positions']);d['positions'].append(q.tolist());d['weights'].append(w);d['colors'].append(color.tolist())
                indices.append(lookup[key]);tex.append((b@uv[fi]).tolist());normal=b@normals[fi];ns.append((normal/max(np.linalg.norm(normal),1e-12)).tolist())
            if len(set(indices))==3:d['triangles'].append(indices);d['uv'].append(tex);d['normals'].append(ns);d['triangle_materials'].append(int(slots[fi]))
    original=np.asarray(d['positions']);out=original.copy();edit=fit.skin_mask(d)
    offsets=[];local_tops={}
    for i in np.flatnonzero(edit):
        # Evaluate one radial deformation field for outer cloth, lining and
        # trim at the same angle/height. Nearest-point anchoring can move a
        # lining vertex sideways across the raised edge of a sloped waistband.
        q=original[i];radial=q-np.array([0.,.8,q[2]]);radial/=max(np.linalg.norm(radial),1e-12)
        anchor,_,_,_=tree.ray_cast(Vector((0.,.8,q[2]))+Vector(radial)*40,Vector(-radial),40)
        if anchor is None:anchor,_,_,_=tree.find_nearest(Vector(q))
        anchor=np.asarray(anchor)
        origin=np.array([0.,.8,anchor[2] if top<98.5 else min(anchor[2],top)])
        direction=np.r_[anchor[:2]-origin[:2],0.];radius=np.linalg.norm(direction);direction/=max(radius,1e-12)
        local_top=top
        if top<98.5 and not group['items']==['fallback']:
            angle_key=tuple(np.round(direction[:2],6))
            if angle_key not in local_tops:
                low=top;high=min(107.,float(pp[:,2].max())+.01)
                for _ in range(12):
                    middle=(low+high)*.5;start=Vector((0.,.8,middle))+Vector(direction)*40
                    found,_,_,_=ptree.ray_cast(start,Vector(-direction),40)
                    if found is None:high=middle
                    else:low=middle
                local_tops[angle_key]=low
            local_top=local_tops[angle_key]
        local_shift=local_top-99.7
        origin[2]=min(anchor[2],local_top)
        hit,_,fi,_=ptree.ray_cast(Vector(origin+direction*40),Vector(-direction),40)
        if hit is None:
            origin[2]=min(anchor[2],top);hit,_,fi,_=ptree.ray_cast(Vector(origin+direction*40),Vector(-direction),40)
        if hit is None:raise RuntimeError('Provide an explicit native waist guide for '+str(original[i]))
        hit=np.asarray(hit);target=(hit-origin)@direction-.65+.85*float(fit.smooth((anchor[2]-100.1-local_shift)/2.8))
        fade=1-float(fit.smooth((anchor[2]-102.5-local_shift)/4.1))
        out[i]+=direction*(target-radius)*fade
        tri=pf[fi];bc=fit.bary(hit,pp[tri]);w=fit.norm_weights({n:sum(pants['weights'][v].get(n,0)*a for v,a in zip(tri,bc)) for n in set().union(*(pants['weights'][v] for v in tri))})
        d['weights'][i]=fit.blend_weights(d['weights'][i],w,1-float(fit.smooth((anchor[2]-102-local_shift)/4.6)))
        if original[i,2]<top:offsets.append(float(radius-(hit-origin)@direction))
    faces=np.asarray(d['triangles']);cross=-np.cross(out[faces[:,1]]-out[faces[:,0]],out[faces[:,2]]-out[faces[:,0]]);vn=np.zeros_like(out)
    for k in range(3):np.add.at(vn,faces[:,k],cross)
    _,iv=np.unique(np.round(out,5),axis=0,return_inverse=True);acc=np.zeros((iv.max()+1,3));np.add.at(acc,iv,vn);vn=acc[iv];vn/=np.maximum(np.linalg.norm(vn,axis=1,keepdims=True),1e-12)
    for fi in np.flatnonzero(np.any(edit[faces],axis=1)):d['normals'][fi]=vn[faces[fi]].tolist()
    d.update(positions=out.tolist(),profile=row['profile'],binding_source=row['asset'],contract='Native tucked waist: measured trouser overlap, matched waistband weights; original upper garment, arms, materials and coverage retained')
    d['waist_fit']=dict(waist_top_cm=top,cut_height_cm=cut,inside_clearance_cm=.65,hem_extension_cm=extension,guide_sha256=sha(group['guide']),source_sha256=row['asset_sha256'],algorithm_sha256=algorithm)
    write(file,d)
    print('GARMENT_WAIST_AUTHORED',row['item'],signature,row['profile'],len(faces),flush=True)
    audit.append(dict(item=row['item'],profile=row['profile'],group=signature,source_hem_cm=hem,waist_top_cm=top,below_waist_max_outward_cm=max(offsets) if offsets else None,edited_vertices=int(edit.sum()),status='authored_native_tuck'))
    record=dict(item=row['item'],profile=row['profile'],signature=signature,file=str(file),source_file=row['file'],source_asset=row['asset'],source_sha256=row['asset_sha256'],author_sha256=sha(file))
    write(receipt,dict(record=record,audit=audit[-1]));return record

for group_id,group in groups.items():
    for row in inv['rows']:
        if policies['shirts'][row['item']]['mode']=='existing_tuck' and (group['waist_top_cm']>=98.5 or group_id==default):continue
        key=group_id+'_'+hashlib.sha256((algorithm+sha(group['guide'])+row['asset_sha256']).encode()).hexdigest()[:10]
        records.append(build(row,key,group)|dict(group=group_id));gc.collect()
write(R/'authored.json',dict(completed=True,records=records,routes=routes,default_group=default,groups=groups,runtime_tested=False))
write(R/'geometry_audit.json',dict(scope='Saved reference-space waist geometry and actual outfit routes; no gameplay test',records=audit))
