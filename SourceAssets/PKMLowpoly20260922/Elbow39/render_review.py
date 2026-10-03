"""Clean review render of the PKM left arm as the game actually poses it.

Only the locally bound arm object plus the PKM weapon parts are rendered, so
overlapping template meshes and rig controllers cannot fake a silhouette.
"""
import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector

ROOT = Path(r'D:\FPS3D\FPSGAME\SourceAssets\PKMLowpoly20260922')
OUT = ROOT / 'Elbow39' / 'Review'
OUT.mkdir(parents=True, exist_ok=True)

ARGS = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
TAG = ARGS[0] if ARGS else 'current'

CLIPS = {
    'idle': (ROOT / 'Wrist12' / 'PKM_WristContact_Editable.blend',
             'PKM_Game_idle_Wrist12', 60),
    'reload': (ROOT / 'Reload16' / 'PKM_base_Reload_Editable.blend',
               'PKM16_base_reload', 120),
}


def setup_scene(blend, action_name):
    bpy.ops.wm.open_mainfile(filepath=str(blend))
    scene = bpy.context.scene
    rig = bpy.data.objects['PKM_Manny_Rig']
    action = bpy.data.actions[action_name]
    rig.animation_data.action = action
    rig.animation_data.action_slot = action.slots[0]

    keep = []
    for ob in bpy.data.objects:
        if ob.type != 'MESH':
            continue
        name = ob.name
        if name == 'SK_Manny_Arms' and ob.library is None:
            keep.append(ob)
        elif 'PKM' in name and 'Belt' not in name and 'Round' not in name:
            keep.append(ob)
    keep_names = {ob.name for ob in keep}
    for ob in bpy.data.objects:
        if ob.type == 'MESH':
            ob.hide_render = ob.name not in keep_names
        else:
            ob.hide_render = True
    keep_ids = {ob.name_full for ob in keep}
    for ob in bpy.context.view_layer.objects:
        if ob.type == 'MESH':
            ob.hide_set(ob.name_full not in keep_ids)
        else:
            ob.hide_set(True)

    scene.render.engine = 'BLENDER_WORKBENCH'
    scene.display.shading.light = 'STUDIO'
    scene.display.shading.color_type = 'SINGLE'
    scene.display.shading.single_color = (0.62, 0.62, 0.62)
    scene.display.shading.show_shadows = True
    scene.display.shading.show_cavity = True
    scene.display.shading.cavity_type = 'BOTH'
    scene.render.image_settings.file_format = 'PNG'
    return scene, rig, [o.name for o in keep]


def camera_at(scene, name, location, target, lens):
    data = bpy.data.cameras.new(name)
    cam = bpy.data.objects.new(name, data)
    scene.collection.objects.link(cam)
    data.lens = lens
    cam.location = location
    cam.rotation_euler = (Vector(target) - Vector(location)).to_track_quat('-Z', 'Y').to_euler()
    return cam


report = {}
for key, (blend, action_name, fps) in CLIPS.items():
    scene, rig, kept = setup_scene(blend, action_name)
    scene.render.fps = fps
    start, end = map(int, bpy.data.actions[action_name].frame_range)
    report[key] = {'kept_meshes': kept, 'frames': [start, end]}

    folder = OUT / TAG / key
    folder.mkdir(parents=True, exist_ok=True)

    # first-person camera from the authoring scene
    fp = bpy.data.objects.get('Camera')
    scene.camera = fp

    frames = list(range(start, end + 1, max(1, (end - start) // 12 or 1)))[:13]

    scene.render.resolution_x, scene.render.resolution_y = 960, 540
    for f in frames:
        scene.frame_set(f)
        bpy.context.view_layer.update()
        scene.render.filepath = str(folder / ('fp_%04d.png' % f))
        bpy.ops.render.render(write_still=True)

    # elbow close-up, from the outside of the left arm
    scene.frame_set(start)
    bpy.context.view_layer.update()
    elbow = rig.pose.bones['lowerarm_l'].matrix.translation
    up = rig.pose.bones['upperarm_l'].matrix.translation
    out_dir = (elbow - up).normalized()
    side = out_dir.cross(Vector((0, 0, 1))).normalized()
    cam = camera_at(scene, 'ElbowCam',
                    elbow + side * 0.30 - out_dir * 0.06 + Vector((0, 0, 0.02)),
                    elbow, 55)
    scene.camera = cam
    scene.render.resolution_x, scene.render.resolution_y = 720, 720
    for f in frames:
        scene.frame_set(f)
        bpy.context.view_layer.update()
        scene.render.filepath = str(folder / ('elbow_%04d.png' % f))
        bpy.ops.render.render(write_still=True)
    report[key]['elbow_world'] = [round(v, 4) for v in elbow]

(OUT / TAG / 'render_report.json').write_text(
    json.dumps(report, indent=2, ensure_ascii=False), encoding='utf-8')
print('RENDER_DONE', TAG, flush=True)