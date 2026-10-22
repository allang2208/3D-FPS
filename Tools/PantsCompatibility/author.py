"""Author the shirt around each native waist, sharing only identical waist fits."""
import gc,hashlib,json,math,runpy,sys
from pathlib import Path
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
sys.path.insert(0,str(Path(__file__).parent))
from pants_compatibility_paths import *
sys.path.insert(0,str(P/'Tools/RangerCrouchFit'));import fit
inventory=read(R/'inventory.json');groups={};routes={};records=[]
for row in inventory['meshes']:
    if row.get('reuse_pair'):
        routes[row['asset']]=dict(pair=row['reuse_pair'],reused=True,item=row['item']);continue
    d=read(row['capture']);p=np.asarray(d['positions']);f=np.asarray(d['triangles'],int)
    if d.get('outer_shell_triangles'):f=f[:d['outer_shell_triangles']]
    else:
        excluded={i for i,s in enumerate(d.get('material_slots',[])) if 'skin' in s.lower() or '/asianmale_jason/' in d.get('materials',['']*len(d['material_slots']))[i].lower()}
        f=f[~np.isin(d['triangle_materials'],list(excluded))]
    f=f[(p[f][:,:,2].max(axis=1)>=84)&(p[f][:,:,2].min(axis=1)<=112)]
    tree=BVHTree.FromPolygons([Vector(v) for v in p],f.tolist(),all_triangles=True)
    directions=[Vector((math.cos(a),math.sin(a),0)) for a in np.arange(128)*math.tau/128]
    def ring(z):
        origin=Vector((0,.8,z));hits=[]
        for direction in directions:
            hit,_,tri,_=tree.ray_cast(origin+direction*40,-direction,40)
            if hit is None:return None
            bc=fit.bary(np.array(hit),p[f[tri]])
            weights=fit.norm_weights({n:sum(d['weights'][v].get(n,0)*a for v,a in zip(f[tri],bc)) for n in set().union(*(d['weights'][v] for v in f[tri]))})
            hits.append([round(x,4) for x in hit]+[sorted((n,round(w,5)) for n,w in weights.items())])
        return hits
    top=None
    for z in np.arange(min(107.,float(p[f][:,:,2].max())-.1),89.,-.25):
        if ring(float(z)) is not None:top=round(float(z),4);break
    if top is None:raise RuntimeError('No continuous waistband; provide a native waist guide for '+row['asset'])
    samples=[ring(top-dz) for dz in (0,.65,1.3)]
    if any(s is None for s in samples):raise RuntimeError('Waist overlap band is open '+row['asset'])
    signature=hashlib.sha256(json.dumps(samples,separators=(',',':')).encode()).hexdigest()[:14]
    routes[row['asset']]=dict(signature=signature,reused=False,item=row['item'],waist_top_cm=top)
    if signature not in groups:
        guide=dict(positions=d['positions'],triangles=f.tolist(),outer_shell_triangles=len(f),weights=d['weights'],bones=d['bones'],source=row['asset'])
        path=R/'Guides'/(signature+'.json');fit.write(path,guide);groups[signature]=dict(signature=signature,guide=str(path),waist_top_cm=top,items=[row['item']]);del guide
    elif row['item'] not in groups[signature]['items']:groups[signature]['items'].append(row['item'])
    print('PANTS_WAIST_GROUP',row['item'],signature,top,flush=True);del d,p,f,tree;gc.collect()
for signature,group in groups.items():
    output=R/'Fits'/signature
    if not (output/'authored.json').exists():
        runpy.run_path(str(P/'Tools/RangerCrouchFit/author_tucked.py'),init_globals=dict(OUTPUT_ROOT=str(output),PANTS_FILE=group['guide'],PANTS_ITEM=','.join(group['items']),WAIST_TOP=group['waist_top_cm']),run_name='__main__')
    for row in read(output/'authored.json')['records']:
        row.update(signature=signature,waist_top_cm=group['waist_top_cm'],author_sha256=hashlib.sha256(Path(row['file']).read_bytes()).hexdigest());records.append(row)
    gc.collect()
write(R/'authored.json',dict(completed=True,records=records,routes=routes,groups=groups,runtime_tested=False,preview_rendered=False))
print('PANTS_COMPATIBILITY_AUTHORED',len(groups),len(records),flush=True)
