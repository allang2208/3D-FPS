"""Bounded whole-grasp fit; keep all accepted digit angles and native lengths."""
import bpy,json,sys,numpy as np
from pathlib import Path
from mathutils import Matrix,Vector
from mathutils.bvhtree import BVHTree
O=Path(__file__).parent;sys.path.insert(0,str(O))
from grip_math import load,pose,matrix,skinned
d=load('SK_Super90_V7');profiles=load('profiles_after');poses=load('poses')
mount=Matrix(((0,-1,0,0),(1,0,0,.16),(0,0,1,-.8015),(0,0,0,1)));inv=np.array(mount.inverted())
ids=[i for i,w in enumerate(d['weights']) if sum(v for n,v in w.items() if n.endswith('_l') and n.startswith(('hand','thumb','index','middle','ring','pinky')))>.98]
report={}
for family in ('vertical','canted','angled'):
    layer=next(c for c in profiles[family]['clips'] if c['base'].split('/')[-1].startswith('A_Super90_idle.'))
    w,_=pose(d,poses[layer['base']]['samples'][0],layer);normal=matrix(d['rest']['WPN_root'])@w['WPN_root'].inverted();w={n:normal@m for n,m in w.items()}
    v=skinned(d,w)[ids]*np.array([.01,-.01,.01]);v=v@inv[:3,:3].T+inv[:3,3]
    points=[Vector(x) for x in v[::3]];trees=[]
    for kind in (('vertical','tactical_vertical') if family=='vertical' else (family,)):
        bpy.ops.wm.open_mainfile(filepath=str(O/'Exports'/('SM_Super90_'+kind+'_Editable.blend')))
        ob=next(o for o in bpy.context.scene.objects if o.type=='MESH')
        trees.append(BVHTree.FromPolygons([p.co for p in ob.data.vertices],[list(f.vertices) for f in ob.data.polygons]))
    def distances(offset,tree):
        result=[]
        for p in points:
            hit,n,_,distance=tree.find_nearest(p+offset)
            result.append(distance if (p+offset-hit).dot(n)>=0 else -distance)
        return np.array(result)
    base=[distances(Vector(),tree) for tree in trees];near=[np.abs(a)<.004 for a in base]
    def score(offset):
        if offset.length>.007:return 1e8
        costs=[]
        for tree,contact in zip(trees,near):
            a=distances(offset,tree)
            costs.append(8*np.mean(np.maximum(0,-a-.0007)**2)+np.mean(np.maximum(0,a[contact]-.002)**2))
        return max(costs)+.025*offset.length_squared
    offset=Vector();initial=score(offset)
    for step in (.004,.002,.001):
        for repeat in range(3):
            options=[offset.copy()]
            for axis in range(3):
                for sign in (-1,1):
                    p=offset.copy();p[axis]+=step*sign;options.append(p)
            best=min(options,key=score)
            if (best-offset).length<1e-8:break
            offset=best
    final=[distances(offset,tree) for tree in trees]
    report[family]={'offset_grip_m':list(offset),'score_before':initial,'score_after':score(offset),
        'nearest_normal_depth_mm_before':[max(0,-a.min())*1000 for a in base],
        'nearest_normal_depth_mm_after':[max(0,-a.min())*1000 for a in final],
        'deep_samples_before':[int(sum(a<-.001)) for a in base],'deep_samples_after':[int(sum(a<-.001)) for a in final]}
    print('WHOLE_GRASP_FIT',family,json.dumps(report[family]),flush=True)
(O/'contact_fit.json').write_text(json.dumps(report,indent=2))
