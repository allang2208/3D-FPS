"""A deeper, common inner-waist tuck for newly registered pants without exact pairs."""
import gc,hashlib,json,math,runpy,sys
from pathlib import Path
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
sys.path.insert(0,str(Path(__file__).parent))
from pants_compatibility_paths import *
sys.path.insert(0,str(P/'Tools/RangerCrouchFit'));import fit
manifest=read(R/'authored.json');groups=manifest['groups'];signature='default_'+hashlib.sha256(json.dumps(sorted(groups)).encode()).hexdigest()[:14];out=R/'Fits'/signature
top=min(g['waist_top_cm'] for g in groups.values());sources=[]
if not (out/'authored.json').exists():
    for group in groups.values():
        d=read(group['guide']);p=np.asarray(d['positions']);f=np.asarray(d['triangles'],int);tree=BVHTree.FromPolygons([Vector(v) for v in p],f.tolist(),all_triangles=True);sources.append((d,p,f,tree,group['waist_top_cm']))
    pfile=P/'SourceAssets/RangerLeatherPants20261021/RealisticCutV3/Authored/ue_leather_pants/Jason.json'
    d=read(pfile);p=np.asarray(d['positions']);f=np.asarray(d['triangles'][:d['outer_shell_triangles']],int);tree=BVHTree.FromPolygons([Vector(v) for v in p],f.tolist(),all_triangles=True);sources.append((d,p,f,tree,99.7))
    positions=[];weights=[];levels=np.arange(top-2.2,107.51,.5);angles=np.arange(128)*math.tau/128
    for z in levels:
        for theta in angles:
            direction=Vector((math.cos(theta),math.sin(theta),0));best=None
            for d,p,f,tree,zmax in sources:
                origin=Vector((0,.8,min(float(z),zmax)));hit,_,ti,_=tree.ray_cast(origin+direction*40,-direction,40)
                if hit is None:continue
                radius=(hit-origin).dot(direction)
                if best is not None and radius>=best[0]:continue
                bc=fit.bary(np.asarray(hit),p[f[ti]]);w=fit.norm_weights({n:sum(d['weights'][v].get(n,0)*a for v,a in zip(f[ti],bc)) for n in set().union(*(d['weights'][v] for v in f[ti]))});best=(radius,w)
            if best is None:raise RuntimeError('No common waist surface for fallback')
            positions.append([direction.x*(best[0]-.25),.8+direction.y*(best[0]-.25),float(z)]);weights.append(best[1])
    faces=[]
    for j in range(len(levels)-1):
        for i in range(128):
            a=j*128+i;b=j*128+(i+1)%128;c=(j+1)*128+i;e=(j+1)*128+(i+1)%128;faces.extend([[a,b,c],[b,e,c]])
    guide=R/'Guides'/(signature+'.json');fit.write(guide,dict(positions=positions,triangles=faces,outer_shell_triangles=len(faces),weights=weights,bones=sources[0][0]['bones']))
    del sources,d,p,f,tree;gc.collect()
    runpy.run_path(str(P/'Tools/RangerCrouchFit/author_tucked.py'),init_globals=dict(OUTPUT_ROOT=str(out),PANTS_FILE=str(guide),PANTS_ITEM='native_waist_default',WAIST_TOP=top),run_name='__main__')
manifest['records']=[r for r in manifest['records'] if not r.get('default_fit')]
for row in read(out/'authored.json')['records']:
    row.update(signature=signature,default_fit=True,author_sha256=hashlib.sha256(Path(row['file']).read_bytes()).hexdigest());manifest['records'].append(row)
manifest['default_signature']=signature;write(R/'authored.json',manifest);print('PANTS_GENERIC_TUCK_AUTHORED',signature,flush=True)
