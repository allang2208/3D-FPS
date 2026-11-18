import bpy,math,json
from pathlib import Path
from mathutils import Matrix,Vector
from mathutils.bvhtree import BVHTree
ROOT=Path('D:/FPS3D/FPSGAME');OUT=ROOT/'SourceAssets/HillsVillageBlacksmith20261117/WindowR7'
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=str(ROOT/'SourceAssets/HillsVillageBlacksmith20261117/DetailR6/SM_H_OldWall_Window_00A.fbx'))
wall=next(o for o in bpy.context.scene.objects if o.type=='MESH')
xy=1.2*math.sqrt(1.25);scale=Matrix.Diagonal((xy,xy,1.2,1))
wverts=[scale@wall.matrix_world@v.co for v in wall.data.vertices]
wbvh=BVHTree.FromPolygons(wverts,[list(p.vertices) for p in wall.data.polygons])
with bpy.data.libraries.load(str(OUT/'Authored/VillageBlacksmith_WindowR7.blend'),link=False) as (src,dst):dst.objects=['SM_SmithLoft_WindowLeft_R7b','SM_SmithLoft_WindowRight_R7b']
results=[]
for depth in (22,24,26,28):
 root=Matrix.Translation((2.6952*xy/100,depth*xy/100,30.2665*1.2/100))@Matrix.Rotation(math.pi/2,4,'Z')
 collisions=[]
 for i,o in enumerate(dst.objects):
  lo=Vector([min(v.co[a] for v in o.data.vertices) for a in range(3)]);hi=Vector([max(v.co[a] for v in o.data.vertices) for a in range(3)])
  ext=(hi-lo)/2-Vector((.005,.01,.01));centre=(lo+hi)/2
  for step in range(1,13):
   turn=math.radians(105*step/12)*(1 if i==0 else -1)
   trans=root@Matrix.Translation((0,.74 if i==0 else -.74,0))@Matrix.Rotation(turn,4,'Z')
   v=[trans@(centre+Vector((sx*ext.x,sy*ext.y,sz*ext.z))) for sx,sy,sz in [(-1,-1,-1),(1,-1,-1),(1,1,-1),(-1,1,-1),(-1,-1,1),(1,-1,1),(1,1,1),(-1,1,1)]]
   bvh=BVHTree.FromPolygons(v,[(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)])
   if bvh.overlap(wbvh):collisions.append([i,step,round(math.degrees(turn),2)])
 results.append(dict(depth_native_cm=depth,collisions=collisions))
print('AUTHORED_SWING_BOX_WALL',results)
(OUT/'swing-mesh-check.json').write_text(json.dumps(results,indent=2))
