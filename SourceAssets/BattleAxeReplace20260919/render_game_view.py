"""Game-camera renders of the harvest axe viewmodel for grip selection.

Blender --background --python <this> -- <blend> <out_dir> <tag> [fitted.fbx grip_z]

Camera follows FPSGAMECharacter.h: vertical 75 deg, viewmodel at +7 cm right / -7 cm down
in camera space, so the Blender camera sits at (-0.07, 0, +0.07) in rig space looking +Y
(rig head is the origin, forward is +Y). Same convention as RifleStockMelee20260918.
Diagnostic only.
"""
import bpy
import math
import sys
from pathlib import Path
from mathutils import Matrix, Vector

args = sys.argv[sys.argv.index('--') + 1:]
blend = Path(args[0])
out = Path(args[1])
tag = args[2]
out.mkdir(parents=True, exist_ok=True)

bpy.ops.wm.open_mainfile(filepath=str(blend))
scene = bpy.context.scene
scene.frame_set(0)
rig = bpy.data.objects['SK_Harvest_Axe_Rig']
arms = bpy.data.objects['SK_Manny_Arms_Export']

if len(args) > 4:
    fitted = Path(args[3])
    grip_z = float(args[4])
    for obj in list(scene.objects):
        if obj.type == 'MESH' and obj.name.startswith('Harvest_Axe'):
            bpy.data.objects.remove(obj, do_unlink=True)
    rest = {b.name: b.matrix_local.copy() for b in rig.data.bones}
    bpy.ops.import_scene.fbx(filepath=str(fitted))
    tool = next(o for o in scene.objects if o.type == 'MESH' and o.name.startswith('SM_BattleAxe'))
    tool.data.transform(tool.matrix_world)
    tool.matrix_world = Matrix.Identity(4)
    section = [v.co for v in tool.data.vertices if abs(v.co.z - grip_z) < .06]
    center = Vector(((min(v.x for v in section) + max(v.x for v in section)) * .5,
                     (min(v.y for v in section) + max(v.y for v in section)) * .5, grip_z))
    tool.data.transform(Matrix.Translation(-center))
    tool.data.materials.clear()
    tool.data.materials.append(bpy.data.materials.new('M_Harvest_Axe'))
    tool.data.transform(rest['WPN_root'])
    tool.parent = rig
    group = tool.vertex_groups.new(name='WPN_root')
    group.add(list(range(len(tool.data.vertices))), 1., 'REPLACE')
    modifier = tool.modifiers.new('Rigid tool to shared grip motion', 'ARMATURE')
    modifier.object = rig
    tool.name = 'Harvest_Axe'

# Hide every unrelated prop/scene mesh the authoring file carries.
keep = {arms.name, rig.name, 'Harvest_Axe'}
for obj in scene.objects:
    if obj.type in ('MESH', 'ARMATURE'):
        obj.hide_render = obj.name not in keep

scene.render.engine = 'BLENDER_WORKBENCH'
scene.display.shading.light = 'STUDIO'
scene.display.shading.color_type = 'TEXTURE'
scene.render.resolution_x = 960
scene.render.resolution_y = 540
camera_data = bpy.data.cameras.new('GameCam')
camera_data.lens = 13.2
camera_data.sensor_width = 36.0
camera = bpy.data.objects.new('GameCam', camera_data)
scene.collection.objects.link(camera)
scene.camera = camera
camera.location = (-0.07, 0.0, 0.07)
camera.rotation_euler = (math.radians(90.0), 0.0, 0.0)
scene.render.filepath = str(out / f'{tag}_game.png')
bpy.ops.render.render(write_still=True)

# A side view from the player's right for structure: axe silhouette against a clean frame.
camera_data.type = 'ORTHO'
camera_data.ortho_scale = 1.4
current = (rig.matrix_world @ rig.pose.bones['WPN_root'].matrix).translation
camera.location = current + Vector((1.2, 0, .05))
camera.rotation_euler = (current - camera.location).to_track_quat('-Z', 'Y').to_euler()
scene.render.filepath = str(out / f'{tag}_side.png')
bpy.ops.render.render(write_still=True)

# And a front-of-player view to judge how far the head sits from the body.
camera.location = current + Vector((0, 1.2, .1))
camera.rotation_euler = (current - camera.location).to_track_quat('-Z', 'Y').to_euler()
scene.render.filepath = str(out / f'{tag}_front.png')
bpy.ops.render.render(write_still=True)
print('GAME_VIEW_DONE', tag, flush=True)