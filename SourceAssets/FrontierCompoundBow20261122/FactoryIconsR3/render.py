"""Blender background authoring, arguments after -- are project root and batch path."""
import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector

root, batch = map(Path, sys.argv[sys.argv.index('--') + 1:])
family = Path(__file__).resolve().parents[1]
rig = family / 'RigContactR2/FrontierCompoundBow_R2.blend'
optics = family / 'CommonModsR1/Frontier_CommonMods.blend'
shots = {
    'riser': (rig, ['Riser', 'UpperLimb', 'LowerLimb', 'UpperCam', 'LowerCam', 'ControlCable1', 'ControlCable2'], (.24, 1, .08), 20),
    'grip': (rig, ['Grip'], (.38, 1, .12), 0),
    'arrow_rest': (rig, ['Rest'], (.57, 1, .40), 0),
    'stabilizer': (rig, ['Stabilizer'], (.2, 1, .13), -15),
    'string': (rig, [], (.10, 1, 0), 17),
    'sight_category': (optics, ['SM_Frontier_Clearfield2x'], (.70, 1, .12), 0),
}
for slot, (model, names, eye, roll) in shots.items():
    bpy.ops.wm.open_mainfile(filepath=str(model))
    scene = bpy.context.scene
    scene.frame_set(1)
    chosen = [scene.objects[name] for name in names]
    if slot == 'string':
        # Frame 13 makes the two limbs of the free strand distinguishable at
        # card size. Read its actual animated exits and centre serving marker.
        scene.frame_set(13)
        arm = scene.objects['Armature']
        curve = bpy.data.curves.new('Factory main string centreline', 'CURVE')
        curve.dimensions = '3D'
        curve.bevel_resolution = 4
        curve.bevel_depth = 1.0
        strand = curve.splines.new('POLY')
        strand.points.add(2)
        for pt, key in zip(strand.points, ['upper_tip', 'preview_nock', 'lower_tip']):
            pt.co = (*tuple(arm.matrix_world @ arm.pose.bones[key].head), 1)
        string = bpy.data.objects.new(curve.name, curve)
        scene.collection.objects.link(string)
        material = bpy.data.materials.new('Braided strand studio grey')
        material.diffuse_color = (.32, .32, .32, 1)
        curve.materials.append(material)
        chosen = [string]
    for ob in scene.objects:
        if ob.type in {'MESH', 'CURVE'}:
            ob.hide_render = ob not in chosen
            if ob in chosen:
                ob.hide_set(False)
                ob.hide_viewport = False
    scene.world = bpy.data.worlds.new('Product studio')
    scene.world.use_nodes = True
    world = next(n for n in scene.world.node_tree.nodes if n.type == 'BACKGROUND')
    world.inputs['Color'].default_value = (.65, .65, .65, 1)
    world.inputs['Strength'].default_value = .65
    camera = bpy.data.cameras.new('Workbench orthographic')
    camera.type = 'ORTHO'
    camera.clip_end = 900
    cam = bpy.data.objects.new(camera.name, camera)
    scene.collection.objects.link(cam)
    scene.camera = cam
    direction = Vector(eye).normalized()
    cam.rotation_euler = (-direction).to_track_quat('-Z', 'Y').to_euler()
    cam.rotation_euler.rotate_axis('Z', math.radians(roll))
    rot = cam.rotation_euler.to_matrix()
    bpy.context.view_layer.update()
    deps = bpy.context.evaluated_depsgraph_get()
    points = []
    for ob in chosen:
        evaluated = ob.evaluated_get(deps)
        mesh = evaluated.to_mesh()
        points.extend(rot.transposed() @ (evaluated.matrix_world @ v.co) for v in mesh.vertices)
        evaluated.to_mesh_clear()
    lo = Vector(tuple(min(v[i] for v in points) for i in range(3)))
    hi = Vector(tuple(max(v[i] for v in points) for i in range(3)))
    middle = (lo + hi) * .5
    # Radial fitting keeps diagonal corners of the grip/rest inside the silver ring.
    radius = max(math.hypot(v.x-middle.x, v.y-middle.y) for v in points)
    camera.ortho_scale = radius / .345
    center = rot @ middle
    cam.location = center + direction * 215
    for offset, energy, size in [((36,-70,67),125000,65),((-60,-25,25),56000,48),((-25,50,63),125000,42)]:
        lamp = bpy.data.lights.new('Softbox', 'AREA')
        lamp.energy, lamp.size = energy, size
        light = bpy.data.objects.new(lamp.name, lamp)
        scene.collection.objects.link(light)
        light.location = center + Vector(offset)
        light.rotation_euler = (-Vector(offset)).to_track_quat('-Z', 'Y').to_euler()
    scene.render.engine = 'CYCLES'
    scene.cycles.samples = 24
    scene.cycles.use_denoising = True
    if slot == 'sight_category':
        scene.cycles.film_transparent_glass = True
        scene.cycles.film_transparent_roughness = .15
    scene.render.film_transparent = True
    scene.render.resolution_x = scene.render.resolution_y = 1024
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = 'PNG'
    scene.render.image_settings.color_mode = 'RGBA'
    scene.render.filepath = str(batch / 'Subjects' / (slot + '.png'))
    bpy.ops.render.render(write_still=True)
