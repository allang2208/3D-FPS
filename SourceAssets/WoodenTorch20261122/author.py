"""Run in Blender with FPS_PROJECT_ROOT pointing to the active FPSGAME project."""
import json
import os
from pathlib import Path

import bpy
import numpy as np
from mathutils import Vector

root = Path(os.environ["FPS_PROJECT_ROOT"])
source = root / "SourceAssets/WoodenTorch20261122"
out = source / "Export"
bpy.ops.wm.read_factory_settings(use_empty=True)

def vertices(obj):
    co = np.empty(len(obj.data.vertices) * 3, dtype=np.float32)
    obj.data.vertices.foreach_get("co", co)
    return co.reshape(-1, 3)

def cross_sections(obj, levels):
    xyz = vertices(obj)
    pairs = np.asarray([e.vertices[:] for e in obj.data.edges])
    a, b = xyz[pairs[:, 0]], xyz[pairs[:, 1]]
    sections = []
    for z in levels:
        use = (a[:, 2] > z) != (b[:, 2] > z)
        fraction = (z - a[use, 2]) / (b[use, 2] - a[use, 2])
        xy = a[use, :2] + (b[use, :2] - a[use, :2]) * fraction[:, None]
        sections.append([*xy.min(axis=0), *xy.max(axis=0)])
    return np.asarray(sections)

bpy.ops.import_scene.fbx(filepath=str(root / "SourceAssets/Kukri20261020/Export/SM_Kukri.fbx"))
donor = next(o for o in bpy.context.selected_objects if o.type == "MESH")
donor.data.transform(donor.matrix_world)
levels = np.linspace(-.045, .045, 13)
target = cross_sections(donor, levels)
for o in list(bpy.context.scene.objects):
    bpy.data.objects.remove(o, do_unlink=True)

bpy.ops.import_scene.gltf(filepath=str(next((source / "Original").glob("*.glb"))))
torch = next(o for o in bpy.context.scene.objects if o.type == "MESH")
torch.data.transform(torch.matrix_world)
torch.matrix_world.identity()
p = vertices(torch)
height = p[:, 2].max() - p[:, 2].min()
p[:, 2] -= p[:, 2].min() + .40 * height
p *= .46 / height
torch.data.vertices.foreach_set("co", p.ravel())
native = cross_sections(torch, levels)
middle = (native[:, :2] + native[:, 2:]) / 2
p[:, :2] -= middle[len(levels) // 2]
native[:, :2] -= middle[len(levels) // 2]
native[:, 2:] -= middle[len(levels) // 2]
# Match the closed native hand only under the fingers. Ease back into the original
# wood between the fist and the wider head / butt; UVs stay on the original bark.
weight = np.clip((.094 - abs(p[:, 2])) / (.094 - .045), 0., 1.)
weight = weight * weight * (3. - 2. * weight)
for axis in range(2):
    lo = np.interp(p[:, 2], levels, native[:, axis])
    hi = np.interp(p[:, 2], levels, native[:, axis + 2])
    dlo = np.interp(p[:, 2], levels, target[:, axis])
    dhi = np.interp(p[:, 2], levels, target[:, axis + 2])
    fitted = dlo + (p[:, axis] - lo) * (dhi - dlo) / (hi - lo)
    p[:, axis] += weight * (fitted - p[:, axis])
torch.data.vertices.foreach_set("co", p.ravel())
torch.data.update()
torch.name = torch.data.name = "SM_WoodenTorch"
mat = torch.data.materials[0]
mat.name = "M_WoodenTorch"
for o in bpy.context.selected_objects:
    o.select_set(False)
torch.select_set(True)
bpy.context.view_layer.objects.active = torch
bpy.ops.export_scene.fbx(filepath=str(out / "SM_WoodenTorch.fbx"), use_selection=True, object_types={"MESH"},
                         apply_unit_scale=True, bake_anim=False, axis_forward="-Y", axis_up="Z",
                         mesh_smooth_type="FACE", use_triangles=True, path_mode="STRIP")
head = p[p[:, 2] > p[:, 2].max() - .017]
flame = (head.min(axis=0) + head.max(axis=0)) * .5
(out / "fit.json").write_text(json.dumps({"length_cm": 46, "handle_from_base_cm":18.4,
    "grip_section_cm": ((target[6,2:] - target[6,:2]) * 100).tolist(),
    "flame_blender_cm": (flame * 100).tolist()},indent=2), encoding="utf8")
bpy.ops.wm.save_as_mainfile(filepath=str(source / "WoodenTorch.blend"))

# Produce the inventory icon using the supplied textured mesh and a transparent background.
scene = bpy.context.scene
scene.render.engine = "CYCLES"
scene.cycles.samples = 5
scene.render.film_transparent = True
scene.render.resolution_x, scene.render.resolution_y = 256, 768
scene.render.resolution_percentage = 100
center = Vector((0, 0, (float(p[:, 2].min()) + float(p[:, 2].max())) / 2))
bpy.ops.object.camera_add(location=center + Vector((.35, -1.5, .06)))
camera = bpy.context.object
camera.rotation_euler = (center - camera.location).to_track_quat("-Z", "Y").to_euler()
camera.data.type = "ORTHO"
camera.data.ortho_scale = .505
scene.camera = camera
for loc, power, size in [((-.5,-.6,.6), 32, .65), ((.5,-.35,.2), 18, .55), ((.15,.4,.65), 25, .45)]:
    bpy.ops.object.light_add(type="AREA", location=loc)
    lamp = bpy.context.object
    lamp.rotation_euler = (center - lamp.location).to_track_quat("-Z", "Y").to_euler()
    lamp.data.energy, lamp.data.shape, lamp.data.size = power, "DISK", size
scene.render.filepath = str(out / "ue_wooden_torch.png")
bpy.ops.render.render(write_still=True)
