"""Render V42 and V46 side by side: viewmodel frames plus right-elbow close-ups."""
import bpy, math
from pathlib import Path
from mathutils import Vector

P = Path(__file__).parent
SOURCES = {
    'v42': P.parent / 'OffscreenLeftInspectV42/AzureRunesword_OffscreenLeftInspectV42.blend',
    'v46': P / 'AzureRunesword_InspectGripArcV46.blend',
}
CLIP = 'A_RuneSword_Inspect'
FPS = 120.0
TIMES = (0.35, 0.40, 0.45, 0.50, 0.55, 0.60, 0.65, 0.75, 1.00, 1.60)
OUT = P / 'Review'
OUT.mkdir(exist_ok=True)


def setup(scene, viewmodel):
    scene.render.engine = 'BLENDER_WORKBENCH'
    scene.display.shading.light = 'STUDIO'
    scene.display.shading.color_type = 'OBJECT'
    scene.display.shading.show_shadows = True
    scene.display.shading.show_cavity = True
    scene.display.shading.cavity_type = 'BOTH'
    scene.display.shading.show_backface_culling = True
    scene.display.shading.background_type = 'WORLD'
    scene.world.color = (0.06, 0.07, 0.09)
    scene.render.resolution_x, scene.render.resolution_y = (960, 540) if viewmodel else (640, 640)
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = 'PNG'
    scene.render.film_transparent = False
    data = bpy.data.cameras.new('AuditCamera')
    camera = bpy.data.objects.new('AuditCamera', data)
    scene.collection.objects.link(camera)
    data.sensor_fit = 'VERTICAL'
    data.sensor_height = 24
    data.clip_start = 0.005
    scene.camera = camera
    if viewmodel:
        camera.location = (0, 0, 0)
        camera.rotation_euler = (math.pi / 2, 0, 0)
        data.lens = 24 / (2 * math.tan(math.radians(75 / 2)))
    else:
        data.type = 'ORTHO'
    return camera, data


for label, path in SOURCES.items():
    bpy.ops.wm.open_mainfile(filepath=str(path))
    scene = bpy.context.scene
    rig = bpy.data.objects['SK_RuneSword_Rig']
    arms = bpy.data.objects['SK_Manny_Arms_Export']
    blade = bpy.data.objects['RuneSword_Blade']
    action = bpy.data.actions[CLIP]
    rig.animation_data.action = action
    rig.animation_data.action_slot = action.slots[0]
    for ob in list(scene.objects):
        keep = ob in (rig, arms, blade)
        ob.hide_render = not keep
        if keep:
            ob.hide_set(False)
            ob.hide_viewport = False
    arms.color = (0.52, 0.66, 0.76, 1)
    blade.color = (0.60, 0.40, 0.14, 1)
    camera, data = setup(scene, True)
    for seconds in TIMES:
        frame = seconds * FPS
        scene.frame_set(int(frame), subframe=frame - int(frame))
        scene.render.filepath = str(OUT / ('%s_fp_%04d.png' % (label, round(seconds * 1000))))
        bpy.ops.render.render(write_still=True)
    # Right elbow / forearm close-up, three-quarter from outside and above.
    for seconds in TIMES:
        frame = seconds * FPS
        scene.frame_set(int(frame), subframe=frame - int(frame))
        bpy.context.view_layer.update()
        elbow = rig.pose.bones['lowerarm_r'].matrix.translation
        wrist = rig.pose.bones['hand_r'].matrix.translation
        centre = (elbow + wrist) / 2.0
        span = max((wrist - elbow).length, 0.25) * 1.6
        data.type = 'ORTHO'
        data.ortho_scale = span
        for view, offset in (('out', Vector((-1.0, 0.25, 0.35))),
                             ('top', Vector((-0.15, 0.25, 1.0)))):
            camera.location = centre + offset.normalized() * span * 2.0
            camera.rotation_euler = (centre - camera.location).to_track_quat(
                '-Z', 'Y').to_euler()
            scene.render.filepath = str(
                OUT / ('%s_%s_%04d.png' % (label, view, round(seconds * 1000))))
            bpy.ops.render.render(write_still=True)
    print('RENDERED', label, flush=True)

print('BEFORE_AFTER_RENDER_DONE')
