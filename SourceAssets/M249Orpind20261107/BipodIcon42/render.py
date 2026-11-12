"""Render the published M249 mount and its two legs in their authored open pose."""
import json
from pathlib import Path
import sys

import bpy
from mathutils import Matrix, Vector

here = Path(__file__).resolve().parent
source = here.parent
project = source.parents[1]
sys.path.insert(0, str(project/'skills/ue5-weapon-workflow/scripts'))
from apply_modification_icon_grayscale import apply_grayscale, neutral_output

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.context.preferences.filepaths.save_version = 0
scene = bpy.context.scene
pivots = json.loads((source/'Repair08/bipod_geometry.json').read_text())['legs']
root = Matrix(json.loads((source/'GripMount40/fit.json').read_text())['root_rotation'])
flip = Matrix.Diagonal(Vector((1., -1., 1.)))
orientation = (flip @ root @ flip).to_4x4()
objects = []
for i, name in enumerate(('Base', 'LegA', 'LegB')):
    folder = 'BipodPin41' if i==0 else 'Repair08'
    path = source/folder/'Exports'/('SM_M249_Bipod_'+name+'.fbx')
    previous = set(scene.objects)
    bpy.ops.import_scene.fbx(filepath=str(path), use_custom_normals=True)
    obj, = [o for o in scene.objects if o not in previous and o.type=='MESH']
    position = Vector((0,0,0)) if i==0 else (flip @ Vector(pivots[i-1]['pivot']))*.01
    obj.matrix_world = orientation @ Matrix.Translation(position) @ obj.matrix_world
    objects.append(obj)

surfaces = json.loads((source/'Finish29/current.json').read_text())['materials']
surface = next(v for k,v in surfaces.items() if 'MI_M249_Bipod.' in k)
mat = bpy.data.materials.new('Bipod steel - icon studio')
mat.use_nodes = True
nodes, links = mat.node_tree.nodes, mat.node_tree.links
bs = nodes.get('Principled BSDF')
def tex(name, data=False):
    node=nodes.new('ShaderNodeTexImage')
    node.image=bpy.data.images.load(str(source/'Textures'/('T_M249_'+name+'.png')))
    if data: node.image.colorspace_settings.name='Non-Color'
    return node.outputs['Color']
color = nodes.new('ShaderNodeMixRGB')
color.inputs[0].default_value = surface['scalars']['SourceColorWeight']
color.inputs[1].default_value = surface['vectors']['FinishColor']
links.new(tex('Color'), color.inputs[2])
links.new(color.outputs[0],bs.inputs['Base Color'])
orm = nodes.new('ShaderNodeSeparateColor')
links.new(tex('ORM',True),orm.inputs[0])
rough = nodes.new('ShaderNodeMath')
rough.operation='MULTIPLY_ADD'
weight=surface['scalars']['SourceRoughnessWeight']
rough.inputs[1].default_value=weight
rough.inputs[2].default_value=surface['scalars']['Roughness']-weight*surface['scalars']['SourceRoughnessPivot']
links.new(orm.outputs['Green'],rough.inputs[0])
links.new(rough.outputs[0],bs.inputs['Roughness'])
bs.inputs['Metallic'].default_value=surface['scalars']['Metallic']
normal=nodes.new('ShaderNodeNormalMap')
links.new(tex('Normal',True),normal.inputs['Color'])
links.new(normal.outputs[0],bs.inputs['Normal'])
for obj in objects:
    for slot in obj.material_slots: slot.material=mat
apply_grayscale(objects)
neutral_output(scene)

scene.render.engine='CYCLES'
scene.cycles.samples=40
scene.cycles.use_denoising=True
scene.render.resolution_x=scene.render.resolution_y=960
scene.render.resolution_percentage=100
scene.render.film_transparent=True
scene.render.image_settings.color_mode='RGBA'
scene.world=bpy.data.worlds.new('Studio soft fill')
scene.world.use_nodes=True
scene.world.node_tree.nodes.get('Background').inputs[0].default_value=(.14,.14,.14,1)
points=[obj.matrix_world @ v.co for obj in objects for v in obj.data.vertices]
center=(Vector([min(p[i] for p in points) for i in range(3)])+
        Vector([max(p[i] for p in points) for i in range(3)]))*.5
direction=Vector((-.48,.877,0)).normalized()
cam_data=bpy.data.cameras.new('Open bipod')
cam=bpy.data.objects.new('Open bipod',cam_data)
scene.collection.objects.link(cam)
cam.location=center+direction
cam.rotation_euler=(-direction).to_track_quat('-Z','Y').to_euler()
cam_data.type='ORTHO'
scene.camera=cam
inverse=cam.rotation_euler.to_matrix().transposed()
q=[inverse @ (p-center) for p in points]
mid=Vector([(min(p[i] for p in q)+max(p[i] for p in q))/2 for i in range(3)])
cam.location += cam.rotation_euler.to_matrix() @ Vector((mid.x,mid.y,0))
cam_data.ortho_scale=1.13*max(max(p[i] for p in q)-min(p[i] for p in q) for i in (0,1))
for name,offset,power,size in [('Left softbox',(.38,.22,.45),14,.29),
                               ('Right fill',(-.44,.12,.10),2.5,.36),
                               ('Rim',(.12,-.35,.36),14,.22)]:
    light=bpy.data.lights.new(name,'AREA')
    light.energy=power
    light.shape='DISK'
    light.size=size
    obj=bpy.data.objects.new(name,light)
    scene.collection.objects.link(obj)
    obj.location=center+Vector(offset)
    obj.rotation_euler=(center-obj.location).to_track_quat('-Z','Y').to_euler()
scene.render.filepath=str(here/'M249_OpenBipod_Model.png')
bpy.ops.render.render(write_still=True)

# The shared plate retains a transparent outer edge. Compose in linear light
# and use the standard view transform so the plate has the original contrast.
scene.view_settings.view_transform='Standard'
scene.view_settings.look='None'
scene.render.resolution_x=scene.render.resolution_y=1254
cam_data.ortho_scale *= 1.54
cam.location -= cam.rotation_euler.to_matrix() @ Vector((0,cam_data.ortho_scale*.073,0))
group = scene.compositing_node_group
n, link = group.nodes, group.links.new
layer = next(node for node in n if node.bl_idname=='CompositorNodeRLayers')
out = next(node for node in n if node.bl_idname=='NodeGroupOutput')
plate = n.new('CompositorNodeImage')
plate.image = bpy.data.images.load(str(project/'SourceAssets/KukriRefinement20261027/StandardEmptyFrame.png'))
def with_alpha(luminance,alpha):
    node = n.new('CompositorNodeSetAlpha')
    node.inputs['Type'].default_value='Replace Alpha'
    link(luminance,node.inputs['Image'])
    link(alpha,node.inputs['Alpha'])
    return node.outputs[0]
def over(bottom,top):
    node=n.new('CompositorNodeAlphaOver')
    link(bottom,node.inputs['Background'])
    link(top,node.inputs['Foreground'])
    return node.outputs[0]
gray=n.new('CompositorNodeRGBToBW')
link(plate.outputs['Image'],gray.inputs[0])
bg=with_alpha(gray.outputs[0],plate.outputs['Alpha'])
shadow=n.new('CompositorNodeBlur')
shadow.inputs['Size'].default_value=(6,6)
link(layer.outputs['Alpha'],shadow.inputs['Image'])
shift=n.new('CompositorNodeTranslate')
shift.inputs['X'].default_value=5
shift.inputs['Y'].default_value=-9
link(shadow.outputs[0],shift.inputs['Image'])
dim=n.new('ShaderNodeMath')
dim.operation='MULTIPLY'
dim.inputs[1].default_value=.56
link(shift.outputs[0],dim.inputs[0])
black=n.new('ShaderNodeValue')
black.outputs[0].default_value=0
bg=over(bg,with_alpha(black.outputs[0],dim.outputs[0]))
tone=n.new('CompositorNodeRGBToBW')
link(layer.outputs['Image'],tone.inputs[0])
# Balance the studio highlights against the silver rim at thumbnail size.
level=n.new('ShaderNodeMath')
level.operation='ADD'
level.inputs[1].default_value=1.06
link(tone.outputs[0],level.inputs[0])
curve=n.new('ShaderNodeMath')
curve.operation='DIVIDE'
link(tone.outputs[0],curve.inputs[0])
link(level.outputs[0],curve.inputs[1])
link(over(bg,with_alpha(curve.outputs[0],layer.outputs['Alpha'])),out.inputs[0])
scene.render.filepath=str(here/'M249_Bipod_Framed.png')
bpy.ops.wm.save_as_mainfile(filepath=str(here/'M249_Bipod_Icon.blend'),relative_remap=True)
bpy.ops.render.render(write_still=True)
