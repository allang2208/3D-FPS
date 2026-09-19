exec((__import__('pathlib').Path(__file__).parent/'measure_mount.py').read_text().split('for ob in bpy.context.scene.objects:')[0])
from mathutils import Vector
from mathutils.bvhtree import BVHTree
ob=bpy.data.objects['M4_Handguard Kmode Unreal_Export'];e=ob.evaluated_get(bpy.context.evaluated_depsgraph_get());m=e.to_mesh();m.calc_loop_triangles();vs=[inv@e.matrix_world@v.co for v in m.vertices];tree=BVHTree.FromPolygons(vs,[tuple(t.vertices) for t in m.loop_triangles],all_triangles=True)
for x in [-.018,-.009,0,.009,.018]:
 print('RAYS',x,[(y,tuple(tree.ray_cast(Vector((x,y,-.03)),Vector((0,0,1)))[0] or [])) for y in [-.014,-.011,-.009,0,.009,.011,.014]])
