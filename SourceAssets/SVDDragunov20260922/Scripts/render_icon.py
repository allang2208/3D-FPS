"""Render the SVD inventory icon in the project's convention (768x320, transparent, facing left).

Existing weapon icons (Content/ColdSteelData/Icons/ue_m4a1.png) are 768x320 side views on a
transparent background with the muzzle pointing left, so this renders the assembled rifle from
its right side with the source albedo/roughness/metallic maps, then mirrors the image
horizontally so the muzzle ends up on the left without showing the mount side.

Run:
    "E:/Program Files/Blender Foundation/Blender 5.1/blender.exe" --background --factory-startup \
        --python <this file> -- <case_root>
"""
import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector

PARTS = {
    'SM_SVD_Body': 'svd', 'SM_SVD_Magazine': 'svd', 'SM_SVD_Trigger': 'svd',
    'SM_SVD_ChargingHandle': 'svd', 'SM_SVD_SafetyLever': 'svd',
    'SM_SVD_ScopeBody': 'pso', 'SM_SVD_ScopeMount': 'pso', 'SM_SVD_ScopeLens': 'pso',
}


def main():
    args = sys.argv[sys.argv.index("--") + 1:]
    case = Path(args[0])
    tex = case / 'Textures'

    bpy.ops.wm.read_factory_settings(use_empty=True)
    objs = []
    for name in PARTS:
        bpy.ops.import_scene.fbx(filepath=str(case / 'Authored' / (name + '.fbx')))
        obj = next(o for o in bpy.context.scene.objects if o.type == 'MESH' and o.name.startswith(name))
        obj.name = name
        objs.append(obj)
    bpy.context.view_layer.update()

    mats = {}
    for name, group in PARTS.items():
        if group in mats:
            continue
        mat = bpy.data.materials.new('icon_' + group)
        mat.use_nodes = True
        bsdf = mat.node_tree.nodes['Principled BSDF']
        nodes, links = mat.node_tree.nodes, mat.node_tree.links
        base = nodes.new('ShaderNodeTexImage')
        base.image = bpy.data.images.load(str(tex / ('T_SVD_%s_basecolor.jpg' % group)))
        links.new(base.outputs['Color'], bsdf.inputs['Base Color'])
        rough = nodes.new('ShaderNodeTexImage')
        rough.image = bpy.data.images.load(str(tex / ('T_SVD_%s_roughness.jpg' % group)))
        rough.image.colorspace_settings.name = 'Non-Color'
        links.new(rough.outputs['Color'], bsdf.inputs['Roughness'])
        metal = nodes.new('ShaderNodeTexImage')
        metal.image = bpy.data.images.load(str(tex / ('T_SVD_%s_metallic.jpg' % group)))
        metal.image.colorspace_settings.name = 'Non-Color'
        links.new(metal.outputs['Color'], bsdf.inputs['Metallic'])
        mats[group] = mat
    for name, group in PARTS.items():
        obj = bpy.context.scene.objects[name]
        obj.data.materials.clear()
        obj.data.materials.append(mats[group])

    # frame the rifle: 1.225 m long, 2.4:1 icon aspect
    pts = [o.matrix_world @ Vector(c) for o in objs for c in o.bound_box]
    mn = Vector((min(p[i] for p in pts) for i in range(3)))
    mx = Vector((max(p[i] for p in pts) for i in range(3)))
    centre = (mn + mx) / 2.0
    length = mx.y - mn.y

    scene = bpy.context.scene
    scene.render.engine = 'CYCLES'
    scene.cycles.device = 'CPU'
    scene.cycles.samples = 96
    scene.cycles.use_denoising = True
    scene.render.film_transparent = True
    scene.render.resolution_x = 1536
    scene.render.resolution_y = 640
    scene.view_settings.view_transform = 'Standard'
    world = bpy.data.worlds.new('WIcon')
    scene.world = world
    world.use_nodes = True
    world.node_tree.nodes['Background'].inputs[0].default_value = (0.35, 0.36, 0.38, 1)
    world.node_tree.nodes['Background'].inputs[1].default_value = 0.9

    for label, offset, energy, size in [
        ('key', (2.2, -1.6, 2.6), 900.0, 3.0),
        ('fill', (2.4, 1.8, 0.6), 260.0, 3.5),
        ('rim', (-1.8, 0.4, 1.4), 320.0, 2.5),
    ]:
        light_data = bpy.data.lights.new('icon_' + label, type='AREA')
        light_data.energy = energy
        light_data.size = size
        light = bpy.data.objects.new('icon_' + label, light_data)
        light.location = centre + Vector(offset)
        light.rotation_euler = (centre - light.location).to_track_quat('-Z', 'Y').to_euler()
        scene.collection.objects.link(light)

    cam_data = bpy.data.cameras.new('icon_cam')
    cam_data.type = 'ORTHO'
    cam_data.ortho_scale = length * 1.06
    cam = bpy.data.objects.new('icon_cam', cam_data)
    scene.collection.objects.link(cam)
    scene.camera = cam
    cam.location = centre + Vector((3.0, 0.0, 0.0))          # weapon's right side
    cam.rotation_euler = (math.radians(90), 0, math.radians(90))
    out = case / 'Previews' / 'icon'
    out.mkdir(parents=True, exist_ok=True)
    scene.render.filepath = str(out / 'ue_svd_raw')
    bpy.ops.render.render(write_still=True)
    (case / 'Receipts' / 'icon_render.json').write_text(json.dumps({
        'raw': str(out / 'ue_svd_raw.png'),
        'rifle_length_m': round(length, 4),
        'ortho_scale_m': round(length * 1.06, 4),
        'camera': 'right side (+X), muzzle +Y, flipped horizontally after render',
    }, indent=2), encoding='utf-8')
    print('ICON_RENDER length=%.4f raw=%s' % (length, out / 'ue_svd_raw.png'))


main()
