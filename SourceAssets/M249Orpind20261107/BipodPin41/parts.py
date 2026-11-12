"""Keep the published pivots, transferable UVs and normal directions in all three static meshes."""
from pathlib import Path
import json

import bpy
import numpy as np
from mathutils.kdtree import KDTree

HERE = Path(__file__).resolve().parent
SOURCE = HERE.parent
pin = json.loads((HERE/'pin.json').read_text())
recipe = json.loads((SOURCE/'assembly.json').read_text(encoding='utf-8'))
out = HERE/'Exports'
out.mkdir(exist_ok=True)
mirror = np.array([1., -1., 1.])
positions = np.asarray(pin['component'])
normals = np.asarray(pin['normals'])
faces = np.asarray(pin['faces'])
body_pivot = np.asarray(pin['body_pivot'])[[2,1,0]] * mirror
in_body = (positions[:,[2,1,0]] * mirror - body_pivot) / 100

def load(path):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=str(path), use_custom_normals=True)
    obj, = [o for o in bpy.context.scene.objects if o.type == 'MESH']
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    return obj

def export(obj, name):
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.export_scene.fbx(filepath=str(out/(name+'.fbx')), use_selection=True, object_types={'MESH'},
                             axis_forward='-Y', axis_up='Z', bake_anim=False, mesh_smooth_type='FACE', path_mode='STRIP')

def add_pin(obj, points, directions, triangles):
    mesh = bpy.data.meshes.new('MountCrossPin')
    mesh.from_pydata(points.tolist(), [], triangles.tolist())
    mesh.update()
    mesh.materials.append(obj.data.materials[0])
    mapped = np.array(pin['uv'])
    mapped[:,1] = 1. - mapped[:,1]
    loops = [loop.vertex_index for loop in mesh.loops]
    mesh.uv_layers.new(name=obj.data.uv_layers.active.name).data.foreach_set('uv', mapped[loops].astype('f').ravel())
    mesh.polygons.foreach_set('use_smooth', np.ones(len(triangles), dtype=bool))
    mesh.normals_split_custom_set_from_vertices(directions.tolist())
    small = bpy.data.objects.new('MountCrossPin', mesh)
    bpy.context.collection.objects.link(small)
    bpy.ops.object.select_all(action='DESELECT')
    small.select_set(True)
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.join()

body = load(SOURCE/'GripMount40/Exports/SM_M249_body.fbx')
tree = KDTree(len(in_body))
for i, point in enumerate(in_body):
    tree.insert(point, i)
tree.balance()
# Remove only this disconnected island from the already revised receiver.
selected = {v.index for v in body.data.vertices if tree.find(body.matrix_world @ v.co)[2] < .00001}
matched = [p for p in body.data.polygons if any(i in selected for i in p.vertices)]
if len(matched) != len(faces) or any(not all(i in selected for i in p.vertices) for p in matched):
    raise ValueError('Unexpected pin in the published workbench receiver')
bpy.ops.object.mode_set(mode='EDIT')
bpy.ops.mesh.select_mode(type='VERT')
bpy.ops.mesh.select_all(action='DESELECT')
bpy.ops.object.mode_set(mode='OBJECT')
for i in selected:
    body.data.vertices[i].select = True
bpy.ops.object.mode_set(mode='EDIT')
bpy.ops.mesh.delete(type='VERT')
bpy.ops.object.mode_set(mode='OBJECT')
export(body, 'SM_M249_body')

table = load(SOURCE/'Exports/SM_M249_bipod.fbx')
target = next(part['target'] for part in recipe['parts'] if part['id']=='bipod')
offset = (np.asarray(recipe['body_position']) - target) * mirror / 100
add_pin(table, in_body + offset, normals[:,[2,1,0]] * mirror, faces[:,::-1])
export(table, 'SM_M249_bipod')

base = load(SOURCE/'Repair08/Exports/SM_M249_Bipod_Base.fbx')
root = np.asarray(pin['root_rotation'])
add_pin(base, (positions - pin['root_position']) @ root * mirror / 100, normals @ root * mirror, faces)
export(base, 'SM_M249_Bipod_Base')
