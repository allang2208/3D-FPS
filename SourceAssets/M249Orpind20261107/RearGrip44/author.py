"""Export one complete original grip per slot with its production surface binding."""
import json
from pathlib import Path
import sys

import bpy
from mathutils import Matrix
from mathutils.kdtree import KDTree
import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
from source import CACHE, MODELS

FIT = json.loads((HERE.parent/'GripMount40/fit.json').read_text())
PLACEMENTS = json.loads((HERE/'placement.json').read_text())
EXPORTS = HERE/'Exports'


def coat(mesh, donor):
    # UV0 is the selected original texture atlas. The M249 finish also uses
    # two local tiling channels and the previously authored paint mask.
    for channel in list(donor.uv_layers)[1:]:
        uv = mesh.uv_layers.new(name=channel.name)
        for face in mesh.polygons:
            axes = [i for i in range(3) if i != np.argmax(abs(np.array(face.normal)))]
            for index in face.loop_indices:
                p = mesh.vertices[mesh.loops[index].vertex_index].co
                uv.data[index].uv = (p[axes[0]]/.05,p[axes[1]]/.05)
    mesh.uv_layers.active_index = 0
    mesh.uv_layers[0].active_render = True
    attr = donor.color_attributes.active_color
    if attr is None:
        return
    source = donor.uv_layers[0].data
    tree = KDTree(len(source))
    for i, uv in enumerate(source):
        tree.insert((*uv.uv,0), i)
    tree.balance()
    colors = mesh.color_attributes.new(name=attr.name,type=attr.data_type,domain='CORNER')
    mesh.color_attributes.active_color = colors
    for i, uv in enumerate(mesh.uv_layers[0].data):
        _, index, _ = tree.find((*uv.uv,0))
        if attr.domain == 'POINT':
            index = donor.loops[index].vertex_index
        colors.data[i].color = attr.data[index].color


def author(key):
    name = 'SM_M249_'+key
    bpy.ops.wm.open_mainfile(filepath=str(CACHE/(key+'.blend')),use_scripts=False)
    bpy.context.preferences.filepaths.save_version = 0
    obj, = list(bpy.context.scene.objects)
    mirror = np.diag([1.,-1.,1.])
    to_component = np.eye(4)
    to_component[:3,:3] = mirror @ FIT['root_rotation'] @ mirror * 100
    to_component[:3,3] = mirror @ FIT['root_position']
    transform = np.linalg.solve(to_component, PLACEMENTS[key]['source_to_component_cm'])
    obj.data.transform(Matrix(transform))
    obj.data.update()
    # Read surface attributes only. No donor object is linked or exported.
    with bpy.data.libraries.load(str(HERE.parent/'Repair13/Exports'/(name+'.blend')),link=False) as (src,dst):
        dst.objects = [s for s in src.objects if s.startswith('SM_PKM_')]
    donor, = dst.objects
    coat(obj.data,donor.data)
    bpy.data.objects.remove(donor,do_unlink=True)
    # Blender may have loaded the historical material with this name. Free
    # the name on it before giving the original atlas its production slot.
    slot = 'M24913_'+key+'_1'
    old = bpy.data.materials.get(slot)
    if old:
        old.name = slot+'_reference'
    obj.data.materials[0].name = slot
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.export_scene.fbx(filepath=str(EXPORTS/(name+'.fbx')),use_selection=True,
                             object_types={'MESH'},axis_forward='-Y',axis_up='Z',
                             bake_anim=False,mesh_smooth_type='FACE',use_tspace=True,
                             path_mode='STRIP',colors_type='LINEAR')
    bpy.ops.wm.save_as_mainfile(filepath=str(EXPORTS/(name+'.blend')))
    print('M249_ORIGINAL_GRIP',key,MODELS[key][0],len(obj.data.polygons),flush=True)


if __name__ == '__main__':
    EXPORTS.mkdir(exist_ok=True)
    for model in MODELS:
        author(model)
