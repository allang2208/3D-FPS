"""Matching native leather and exposed-skin surfaces with identical animated seams."""
import json,hashlib,os
from pathlib import Path
from collections import defaultdict
import numpy as np
import author_fingerless_hunt_v2 as lib
P=lib.P;R=lib.ROOT;REVIEW=R/'ClearanceReview';OUT=R/'SkinCoverage';OUT.mkdir(exist_ok=True)
# Cover the knuckle roots instead of opening inside the palm.  The same
# interpolated contour cuts both surfaces, including the thumb web.
ROOT_WEIGHT=float(os.environ.get('FINGERLESS_ROOT_WEIGHT','.50'))
FULL=R/'FullShell';FULL.mkdir(exist_ok=True)
def read(p):return json.loads(p.read_text())
def welded_source(d):
    # UE stores UV/material seams as duplicate vertices. Weld only identical
    # positions AND identical skin weights; retain every corner UV and normal.
    lookup={};pos=[];ws=[];remap=[]
    for p,w in zip(d['positions'],d['weights']):
        key=(*[round(v,5) for v in p],tuple(sorted((n,round(v,6)) for n,v in w.items())))
        if key not in lookup:lookup[key]=len(pos);pos.append(p);ws.append(w)
        remap.append(lookup[key])
    d=dict(d);d['positions']=pos;d['weights']=ws;d['triangles']=np.asarray(remap)[np.asarray(d['triangles'])].tolist()
    return d
def digit(w):
    return max(sum(v for n,v in w.items() if n in {f'{f}_{i:02d}_{s}' for s in ('l','r') for i in ((2,3) if f=='thumb' else (1,2,3))}) for f in ('index','middle','ring','pinky','thumb'))
def exposed_skin(base):
    p=np.asarray(base['positions']);t=base['triangles'];w=base['weights'];field=np.array([digit(v)-ROOT_WEIGHT for v in w])
    out=dict(base);pos=base['positions'].copy();weights=w.copy();faces=[];uvs=[];ns=[];mats=[];lookup={}
    extras={k:[] for k in base if k=='colors' or (k.startswith('uv') and k!='uv')}
    def edge(a,b,alpha):
        key=(min(a,b),max(a,b));k=lookup.get(key)
        if k is None:
            k=len(pos);lookup[key]=k;pos.append((p[a]*(1-alpha)+p[b]*alpha).tolist());ww=defaultdict(float)
            for n,v in w[a].items():ww[n]+=v*(1-alpha)
            for n,v in w[b].items():ww[n]+=v*alpha
            weights.append(dict(ww))
        return k
    for fi,f in enumerate(t):
        uv=np.asarray(base['uv'][fi]);normal=np.asarray(base['normals'][fi]);mat=base['triangle_materials'][fi]
        if mat!=2:
            faces.append(f);uvs.append(uv.tolist());ns.append(normal.tolist());mats.append(mat)
            for k,values in extras.items():values.append(base[k][fi])
            continue
        polygon=[]
        for j in range(3):
            k=(j+1)%3;a=f[j];b=f[k];fa=field[a];fb=field[b]
            if fa>=0:polygon.append((a,uv[j],normal[j],np.eye(3)[j]))
            if (fa<0<fb) or (fb<0<fa):
                alpha=float(fa/(fa-fb));polygon.append((edge(a,b,alpha),uv[j]*(1-alpha)+uv[k]*alpha,lib.unit(normal[j]*(1-alpha)+normal[k]*alpha),np.eye(3)[j]*(1-alpha)+np.eye(3)[k]*alpha))
        for j in range(1,len(polygon)-1):
            rows=[polygon[0],polygon[j],polygon[j+1]];faces.append([v[0] for v in rows]);uvs.append([v[1].tolist() for v in rows]);ns.append([v[2].tolist() for v in rows]);mats.append(mat)
            for k,values in extras.items():values.append([(v[3]@np.asarray(base[k][fi])).tolist() for v in rows])
    out.update(positions=pos,weights=weights,triangles=faces,uv=uvs,normals=ns,triangle_materials=mats);out.update(extras)
    return out
manifest=[];skin_manifest=[]
for row in read(REVIEW/'mesh-manifest.json'):
    name=row['profile'];base=welded_source(read(REVIEW/(name+'_skin.json')))
    frames={}
    for side,f in lib.anatomy.items():
        transform=lib.bind(base['bones']['hand_'+side])@np.linalg.inv(lib.bind(lib.canonical['bones']['hand_'+side]))
        frames[side]={k:lib.unit(transform[:3,:3]@np.asarray(f[k])) for k in ('across','forward','dorsal')}
        frames[side]['wrist']=(transform@np.r_[f['wrist'],1])[:3]
    base['source']=base['path']
    shape=lib.shell(base,base['bones'],frames,ROOT_WEIGHT,None)
    glove=dict(profile=name,source=base['path'],binding_source=base['path'],base_mesh=base['path'],
        positions=shape['positions'].tolist(),weights=shape['weights'],triangles=shape['triangles'].tolist(),normals=shape['normals'].tolist(),
        uv=shape['uv'],uv1=shape['uv1'],uv2=shape['uv2'],triangle_materials=[0]*len(shape['triangles']),bones=base['bones'],
        family='FingerlessHuntV2',surface_winding='ue_native',coverage_root_weight=ROOT_WEIGHT,opening_contours=shape['loops'],
        contract='Full palm, back and thumb web through the finger junction; five exposed digits; coupled native seams; original animation timing')
    path=R/'Authored'/(name+'.json');path.write_text(json.dumps(glove,separators=(',',':')))
    (FULL/path.name).write_bytes(path.read_bytes())
    manifest.append(dict(profile=name,authored=str(path),vertices=len(glove['positions']),triangles=len(glove['triangles']),sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
    skin=exposed_skin(base);skin['profile']=name;skin['source']=base['path'];skin['family']='FingerlessHuntV2_ExposedSkin'
    (OUT/(name+'_review.json')).write_text(json.dumps(skin,separators=(',',':')))
    skin_manifest.append(dict(profile=name,source=base['path'],vertices=len(skin['positions']),triangles=len(skin['triangles'])))
    print('FINGERLESS_COUPLED',name,len(glove['triangles']),len(skin['triangles']),flush=True)
(R/'manifest.json').write_text(json.dumps(manifest,indent=2))
(OUT/'manifest.json').write_text(json.dumps(skin_manifest,indent=2))
(R/'design.json').write_text(json.dumps(dict(revision='CoverageToRoots20260927',exposure='five digits from palm-finger junction',coverage='full palm, back and thumb web',root_weight=ROOT_WEIGHT,skin_companion=True,shared_seam=True,contact_outer_mm=.35,dorsal_outer_mm=.8,edge_roll_extra_mm=.8,new_animations=0,runtime_tested=False),indent=2))
