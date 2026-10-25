import sys,json
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
import numpy as np
root=Path('D:/FPS3D/FPSGAME/SourceAssets/FurnitureRest20261022/RefineV2')
sys.argv=['x','--','--candidate','--all','--review',str(root/'Fit')]
code=Path('D:/FPS3D/FPSGAME/Tools/FurnitureRest/render_review.py').read_text();exec(code[:code.index('bpy.ops.wm.read_factory_settings')])
v,hp=frame('Ward','Idle',0);g=json.loads((root/'Geometry/9.json').read_text());b=BVHTree.FromPolygons(g['positions'],g['triangles'],all_triangles=True)
audit=Path('Tools/FurnitureRest/audit_geometry.py').read_text();exec(audit[audit.index('directions='):audit.index("for profile in config['furniture']:")])
for dy,dz in [(a,b) for a in (-24,-18,12,18,24) for b in (-2,-1,0)]:
 bad=[]
 for p in v[::4]+[0,dy,dz]:
  loc,n,_,dist=b.find_nearest(Vector(p),8)
  if loc is not None and dist>.7 and inside(b,p):bad.append(dist)
 print('OFFSET',dy,dz,'count',len(bad),'max',max(bad) if bad else 0,flush=True)
