"""Measure the hand against the rounded armrest while refining its drape."""
import sys,json
from pathlib import Path
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
OUT=Path('D:/FPS3D/FPSGAME/SourceAssets/FurnitureRest20261022/RelaxedSeatV5')
sys.argv=['probe','--','--candidate','--all','--review',str(OUT/'Probe'),'--config',str(OUT/'review_config.json')]
code=Path('D:/FPS3D/FPSGAME/Tools/FurnitureRest/render_review.py').read_text()
exec(code[:code.index('bpy.ops.wm.read_factory_settings')])
lookup=json.loads((OUT/'Geometry/index.json').read_text())
dominant=[geo['bone_names'][max(ws,key=lambda x:x[1])[0]] for ws in geo['weights']]
def inside(tree,p):
    votes=0
    for v in ((1,.37,.21),(-.22,1,.41),(.31,-.18,1)):
        d=Vector(v).normalized();origin=Vector(p);hits=0
        for _ in range(40):
            loc,_,_,_=tree.ray_cast(origin,d,1000)
            if loc is None:break
            hits+=1;origin=loc+d*.003
        votes+=hits%2
    return votes>=2
for kind in ('SofaLeft','SofaRight','ApartmentSofaLeft','ApartmentSofaRight'):
    side='r' if kind.endswith('Left') else 'l'
    ids=[i for i,b in enumerate(dominant) if b.endswith('_'+side) and b.startswith(('hand','thumb','index','middle','ring','pinky'))][::3]
    v,_=frame(kind,'Idle',0);p=profiles[kind]
    g=json.loads(Path(lookup[p['mesh']]).read_text());vs=np.array(g['positions'])*p.get('scale',[1,1,1])
    tree=BVHTree.FromPolygons(vs.tolist(),g['triangles'],all_triangles=True)
    rows=[]
    for y,z in ((0,0),(0,.5),(0,1),(1,0),(1,.5),(1,1),(-1,0),(-1,.5),(0,-.5)):
        worst=0.;gap=999.;count=0
        for point in v[ids]+[0,y,z]:
            loc,n,_,distance=tree.find_nearest(Vector(point));gap=min(gap,distance)
            if distance>.3 and inside(tree,point):worst=max(worst,distance);count+=1
        rows.append([y,z,round(worst,3),count,round(gap,3)])
    print('HAND_DRAPE',kind,rows,flush=True)
