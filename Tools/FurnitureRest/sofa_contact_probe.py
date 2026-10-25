import sys,json
from pathlib import Path
import numpy as np
sys.argv=['probe','--','--candidate','--review','D:/FPS3D/FPSGAME/SourceAssets/FurnitureRest20261022/SofaSupportV3/Probe']
code=Path('D:/FPS3D/FPSGAME/Tools/FurnitureRest/render_review.py').read_text();exec(code[:code.index('bpy.ops.wm.read_factory_settings')])
v,hp=frame('Sofa','Idle',0)
dom=[geo['bone_names'][max(ws,key=lambda x:x[1])[0]] for ws in geo['weights']]
for k in ('hand_l','thumb_03_l','middle_03_l','index_01_l','middle_01_l','pinky_03_l'):
 p=v[np.array([b==k for b in dom])];print(k,p.min(0),p.max(0))

from mathutils.bvhtree import BVHTree
g=json.loads((DATA/'Sofa.json').read_text());tree=BVHTree.FromPolygons(g['positions'],g['triangles'],all_triangles=True)
for x in (98,102,108,112,116):
 for y in (0,20,35):
  print('SURFACE',x,y,tree.ray_cast(Vector((x,y,140)),Vector((0,0,-1)))[0])
