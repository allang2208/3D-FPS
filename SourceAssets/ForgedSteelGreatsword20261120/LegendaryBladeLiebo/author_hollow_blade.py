"""Create the hollow game module directly from the fitted stock mesh and its UVs."""
import math
from pathlib import Path

import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from mathutils.geometry import barycentric_transform

here = Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath=str(here.parent / 'Integration/ForgedSteelGreatsword_Modular_Editable.blend'))
bpy.context.preferences.filepaths.save_version = 0
stock = bpy.data.objects['SM_ForgedSteelGreatsword_Blade_V1']
blade = stock.copy()
blade.data = stock.data.copy()
blade.name = 'SM_ForgedSteelGreatsword_HollowBlade'
bpy.context.scene.collection.objects.link(blade)
source = stock.data
source.calc_loop_triangles()
points = [v.co.copy() for v in source.vertices]
triangles = [tuple(t.vertices) for t in source.loop_triangles]
surface = BVHTree.FromPolygons(points, triangles, all_triangles=True)
zmin, zmax = min(p.z for p in points), max(p.z for p in points)
length = zmax - zmin

def section(t):
    z = zmin + length*t
    xs = []
    for edge in source.edges:
        a, b = [points[i] for i in edge.vertices]
        if (a.z < z) != (b.z < z):
            xs.append(a.x + (b.x-a.x)*(z-a.z)/(b.z-a.z))
    center = (min(xs)+max(xs))*.5
    return center, z, (max(xs)-min(xs))*.095

bottom, top = section(.075), section(.855)
outline = []
for cx, z, radius, start_angle in [(*bottom, math.pi), (*top, 0.)]:
    for step in range(17):
        angle = start_angle + math.pi*step/16
        outline.append((cx+radius*math.cos(angle), z+radius*math.sin(angle)))
depth = max(abs(p.y) for p in points)*3
verts = [(x,y,z) for y in (-depth,depth) for x,z in outline]
n = len(outline)
faces = [tuple(range(n)), tuple(reversed(range(n,2*n)))]
faces.extend(((i+n,(i+1)%n+n,(i+1)%n,i) for i in range(n)))
cutter_mesh = bpy.data.meshes.new('Aperture')
cutter_mesh.from_pydata(verts, [], faces)
cutter_mesh.update()
cutter = bpy.data.objects.new('Aperture',cutter_mesh)
bpy.context.scene.collection.objects.link(cutter)
cutter.matrix_world = blade.matrix_world
inside = bpy.data.materials.new('Aperture face provenance')
cutter_mesh.materials.append(inside)
bpy.ops.object.select_all(action='DESELECT')
blade.hide_set(False)
blade.hide_render = False
blade.select_set(True)
bpy.context.view_layer.objects.active = blade
cut = blade.modifiers.new('Center opening','BOOLEAN')
cut.operation = 'DIFFERENCE'
cut.solver = 'EXACT'
cut.material_mode = 'TRANSFER'
cut.object = cutter
bpy.ops.object.modifier_apply(modifier=cut.name)
mesh = blade.data
inner_faces = [p for p in mesh.polygons if mesh.materials[p.material_index] == inside]
if not inner_faces:
    raise RuntimeError('Boolean produced no inner surface')

uv = mesh.uv_layers.active.data
orig_uv = source.uv_layers.active.data
def original_uv(x, z):
    hit, _, idx, _ = surface.ray_cast(Vector((x,-depth,z)),Vector((0,1,0)))
    if hit is None:
        raise RuntimeError('Missing factory UV surface at aperture')
    tri = source.loop_triangles[idx]
    uvs = [orig_uv[j].uv.to_3d() for j in tri.loops]
    return barycentric_transform(hit, *(points[j] for j in tri.vertices), *uvs).to_2d()

# Map the new inner faces into the same local patch of steel as the adjacent
# blade face. The small depth offset gives the inner walls a usable UV area.
for face in inner_faces:
    for j in face.loop_indices:
        v = mesh.vertices[mesh.loops[j].vertex_index].co
        uv[j].uv = original_uv(v.x+v.y*.45, v.z+v.y*.25)
    face.material_index = 0
    face.use_smooth = False
mesh.materials.pop(index=mesh.materials.find(inside.name))
bpy.data.objects.remove(cutter, do_unlink=True)
mesh.name = blade.name
for obj in list(bpy.context.scene.objects):
    if obj != blade:
        bpy.data.objects.remove(obj, do_unlink=True)
bpy.ops.wm.save_as_mainfile(filepath=str(here/'HollowBlade.blend'))
bpy.ops.export_scene.fbx(filepath=str(here/(blade.name+'.fbx')), use_selection=True, object_types={'MESH'},
                         axis_forward='-Y',axis_up='Z',add_leaf_bones=False,bake_anim=False,
                         mesh_smooth_type='FACE',use_tspace=True,use_triangles=True)
