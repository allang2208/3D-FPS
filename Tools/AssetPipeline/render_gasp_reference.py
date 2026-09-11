"""Render the unmodified Epic motions, preserving the exported frame timing."""
import json
import math
from pathlib import Path
import bpy
from mathutils import Vector

output = Path("D:/FPS3D/FPSGAME/SourceAssets/GASPTraversal20260910/Reference")
reports = {}
for clip in ("Vault", "Mantle", "Climb"):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=str(output / (clip + ".fbx")))
    scene = bpy.context.scene
    rigs = [o for o in scene.objects if o.type == "ARMATURE"]
    assert len(rigs) == 1, rigs
    rig = rigs[0]
    action = rig.animation_data.action
    start, end = map(int, action.frame_range)
    preview_end = min(end, start + 24) if clip == "Vault" else end
    frames = sorted(set(round(start + (preview_end - start) * i / 7) for i in range(8)))
    material = bpy.data.materials.new("Reference Grey")
    material.diffuse_color = (0.35, 0.5, 0.7, 1)
    for obj in scene.objects:
        if obj.type == "MESH":
            obj.data.materials.clear()
            obj.data.materials.append(material)
    points = []
    samples = []
    for frame in frames:
        scene.frame_set(frame)
        bpy.context.view_layer.update()
        row = {"frame": frame}
        for bone in ("root", "pelvis", "hand_l", "hand_r", "head"):
            pose = rig.pose.bones.get(bone)
            if pose:
                pos = rig.matrix_world @ pose.head
                points.append(pos.copy())
                row[bone] = list(pos)
        samples.append(row)
    minimum = Vector(tuple(min(p[i] for p in points) for i in range(3)))
    maximum = Vector(tuple(max(p[i] for p in points) for i in range(3)))
    focus = (minimum + maximum) / 2
    extent = max(maximum - minimum)
    camera_data = bpy.data.cameras.new("ReferenceCamera")
    camera = bpy.data.objects.new("ReferenceCamera", camera_data)
    scene.collection.objects.link(camera)
    scene.camera = camera
    camera_data.type = "ORTHO"
    camera_data.ortho_scale = 2.5
    camera.location = focus + Vector((3, -4, 2)) * extent
    camera.rotation_euler = (focus - camera.location).to_track_quat("-Z", "Y").to_euler()
    scene.render.engine = "BLENDER_WORKBENCH"
    scene.display.shading.light = "STUDIO"
    scene.display.shading.color_type = "MATERIAL"
    scene.display.shading.show_shadows = True
    scene.display.shading.show_cavity = True
    scene.display.shading.background_type = "WORLD"
    scene.world = bpy.data.worlds.new("ReferenceWorld")
    scene.world.color = (0.045, 0.045, 0.045)
    scene.render.resolution_x = 480
    scene.render.resolution_y = 360
    scene.render.resolution_percentage = 100
    for frame in frames:
        scene.frame_set(frame)
        bpy.context.view_layer.update()
        focus = rig.matrix_world @ rig.pose.bones["pelvis"].head
        camera.location = focus + Vector((3, -4, 2))
        camera.rotation_euler = (focus - camera.location).to_track_quat("-Z", "Y").to_euler()
        scene.render.filepath = str(output / (clip + "_" + str(frame) + ".png"))
        bpy.ops.render.render(write_still=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(output / (clip + ".blend")))
    reports[clip] = {"fps": scene.render.fps, "start": start, "end": end, "samples": samples}
(output / "motion_samples.json").write_text(json.dumps(reports, indent=2), encoding="utf-8")
