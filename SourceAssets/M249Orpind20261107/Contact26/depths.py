"""Measure actual left-hand/arm penetration using native skinned geometry.

Winding numbers classify interior for thin/open components, rather than treating
the sign of the nearest triangle normal as evidence of penetration.
"""
from pathlib import Path
import numpy as np, json, sys
from mathutils.bvhtree import BVHTree
from mathutils import Vector
r=Path(__file__).resolve().parent
label=sys.argv[sys.argv.index('--')+1]
idle_only='--idle-only' in sys.argv
report_label=label+('_idle' if idle_only else '')
results={}

import ctypes
windlib=ctypes.CDLL(str(r/'winding.dll'));windlib.winding.argtypes=[ctypes.c_void_p,ctypes.c_int,ctypes.c_void_p,ctypes.c_int,ctypes.c_void_p]
def winding(points,tri):
 p=np.ascontiguousarray(points,dtype=np.float64);t=np.ascontiguousarray(tri,dtype=np.float64);out=np.zeros(len(p));windlib.winding(p.ctypes.data,len(p),t.ctypes.data,len(t),out.ctypes.data);return out

for folder in sorted((r/label).iterdir()):
    if not (folder/'geometry.json').exists():continue
    if idle_only and not folder.name.startswith('30_normal_'):continue
    meta=json.loads((folder/'geometry.json').read_text());j=json.loads((folder/'review.json').read_text())
    dom=np.fromfile(folder/'dominant.bin',np.uint32)
    left=np.array([n.endswith('_l') and n.startswith(('upperarm','lowerarm','hand','thumb','index','middle','ring','pinky')) for n in meta['bones']])[dom]
    rows=[]
    for row in j['frames']:
        if idle_only and row is not j['frames'][-1]:continue
        stem=folder/Path(row['file']).stem
        v=np.fromfile(stem.with_suffix('.vertices'),np.float32).reshape(-1,3)
        f=np.fromfile(stem.with_suffix('.indices'),np.uint32).reshape(-1,3)
        m=np.fromfile(stem.with_suffix('.materials'),np.uint32)
        armids=np.flatnonzero(left);points=v[armids]
        obstacles=[]
        for slot in ['M249_Factory_Foregrip','M249_Factory_Handguard','M249_Factory_Receiver']:
            mi=meta['slots'].index(slot)
            if mi in row['visible_materials']:obstacles.append((slot,v,f[m==mi]))
        for part in folder.glob(stem.name+'_*.vertices'):
            if 'side_mag' in part.name or any('_'+x in part.name for x in ['vertical','canted','angled','prism']):
                obstacles.append((part.stem.replace(stem.name+'_',''),np.fromfile(part,np.float32).reshape(-1,3),np.fromfile(part.with_suffix('.indices'),np.uint32).reshape(-1,3)))
        contacts={}
        for name,p,faces in obstacles:
            used=p[np.unique(faces)]
            near=np.all(points>=used.min(0)-.1,axis=1)&np.all(points<=used.max(0)+.1,axis=1)
            ids=np.flatnonzero(near)
            if not len(ids):continue
            tree=BVHTree.FromPolygons(p.tolist(),faces.tolist(),all_triangles=True)
            # UE and Blender can disagree on triangle winding. Classify with
            # three parity rays first, then confirm the deepest 64 points with
            # absolute winding numbers. Counts are sample counts, not totals.
            candidates=[]
            directions=[Vector(x).normalized() for x in [(1,.231,.417),(.319,1,.173),(.137,.293,1)]]
            for i in ids:
                pt,n,fi,distance=tree.find_nearest(Vector(points[i]))
                if distance<=.03:continue
                votes=0
                for direction in directions:
                    origin=Vector(points[i]);count=0
                    for step in range(80):
                        hit,normal,index,length=tree.ray_cast(origin,direction,1000.)
                        if hit is None:break
                        count+=1;origin=hit+direction*.0001
                    votes+=count%2
                if votes>=2:candidates.append((float(distance),int(i)))
            candidates=sorted(candidates,reverse=True)[:64]
            if not candidates:continue
            ids=np.array([i for _,i in candidates])
            query=points[ids]
            wn=winding(query,p[faces].astype(np.float64))
            inside=wn>.65
            if not inside.any():continue
            dist=np.array([distance for distance,_ in candidates])[inside]
            if dist.max()<.03:continue
            picked=armids[ids[inside]]
            worst=np.argsort(dist)[-5:]
            contacts[name]=dict(max_depth_cm=float(dist.max()),sampled_vertices_over_2mm=int(np.sum(dist>.2)),sampled_vertices_over_5mm=int(np.sum(dist>.5)),worst_bones=sorted(set(meta['bones'][dom[picked[k]]] for k in worst)))
        if contacts:rows.append(dict(source=row['source'],contacts=contacts))
    results[folder.name]=rows
    (r/('depths_'+report_label+'.json')).write_text(json.dumps(results,indent=2))
    peak=max((c['max_depth_cm'] for row in rows for c in row['contacts'].values()),default=0.)
    print(folder.name,'max interior depth cm',round(peak,3),flush=True)
