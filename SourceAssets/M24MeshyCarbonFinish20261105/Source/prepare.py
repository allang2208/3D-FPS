"""Create unique UVs and collect the evaluated tangent basis and local occlusion."""
from pathlib import Path
import math, os, tempfile
import bpy
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

work = Path(tempfile.gettempdir()) / "M24MeshyCarbon1105124237_finish"
work.mkdir(exist_ok=True)
source = Path(__file__).with_name("Meshy_AI_Carbon_Stock_1105124237_generate.glb")
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(source))
obj = next(o for o in bpy.context.scene.objects if o.type == 'MESH')
obj.name = 'M24_Xuanji_Carbon_Stock'
mesh = obj.data
bpy.context.view_layer.objects.active = obj
obj.select_set(True)
for polygon in mesh.polygons:
    polygon.use_smooth = True
bpy.ops.object.mode_set(mode='EDIT')
bpy.ops.mesh.select_all(action='SELECT')
bpy.ops.uv.smart_project(angle_limit=math.radians(66), island_margin=.0035, scale_to_bounds=True)
bpy.ops.object.mode_set(mode='OBJECT')
mesh.uv_layers.active.name = 'FinishUV'
mesh.calc_tangents(uvmap='FinishUV')
def attr(collection, key, width=3, dtype=np.float32):
    out = np.empty(len(collection)*width, dtype)
    collection.foreach_get(key,out)
    return out.reshape(len(collection), width)
pos = attr(mesh.vertices, 'co')
ids = attr(mesh.loops, 'vertex_index', 1, np.int32).reshape(-1)
uv = attr(mesh.uv_layers.active.data,'uv',2)
tangent = attr(mesh.loops,'tangent')
sign = attr(mesh.loops,'bitangent_sign',1)
normal = attr(mesh.corner_normals,'vector')
vert_normal = attr(mesh.vertices,'normal')
tri = ids.reshape(-1,3)
tree = BVHTree.FromPolygons(pos,tri,all_triangles=True)
ao = np.ones(len(pos),np.float32)
ray_count = 24
horizon = .085
directions = []
for j in range(ray_count):
    radius = math.sqrt((j+.5)/ray_count)
    angle = j*2.3999632297
    directions.append((math.cos(angle)*radius,math.sin(angle)*radius,math.sqrt(1-radius*radius)))
for i,(point,n) in enumerate(zip(pos,vert_normal)):
    N = Vector(n).normalized()
    axis = Vector((1,0,0)) if abs(N.x)<.85 else Vector((0,1,0))
    T = N.cross(axis).normalized()
    B = N.cross(T)
    origin = Vector(point) + .00036*N
    shade = 0
    for a,b,c in directions:
        hit = tree.ray_cast(origin, a*T+b*B+c*N, horizon)
        if hit[0] is not None:
            shade += (1-hit[3]/horizon)**2
    ao[i] = 1 - .84*shade/ray_count
np.savez(work/'basis.npz',pos=pos,ids=tri,uv=uv,tangent=tangent,sign=sign,normal=normal,ao=ao)
bpy.ops.wm.save_as_mainfile(filepath=str(work/'prepared.blend'))
