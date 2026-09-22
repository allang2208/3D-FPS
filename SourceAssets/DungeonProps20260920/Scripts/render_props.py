"""Render studio shots of each downloaded textured GLB for visual review.

Same pipeline as the project's earlier asset reviews (Cycles, fixed studio lights,
orthographic camera, AgX view transform). Renders front / side / angle per prop.
Read-only: writes PNGs next to each prop, never touches the GLBs or the UE project.

Run (per prop folder, Blender is started once per prop):
  "E:/Program Files/Blender Foundation/Blender 5.1/blender.exe" -b -t 8 \
     --python render_props.py
"""
import sys
from pathlib import Path
import bpy
from mathutils import Vector

P = Path(__file__).resolve().parent.parent   # task root holds the prop folders
PROPS = ['goddess_statue', 'demon_statue', 'supply_pile', 'bone_pile', 'broken_crate']

for prop in PROPS:
    folder = P / prop
    glbs = sorted(folder.glob('textured_master*.glb'))
    if not glbs:
        print(f'SKIP {prop}: no textured glb yet', flush=True)
        continue
    out = folder / 'render'
    if (out / 'angle.png').exists():
        print(f'SKIP {prop}: already rendered', flush=True)
        continue
    out.mkdir(exist_ok=True)

    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(glbs[0]))
    meshes = [o for o in bpy.context.scene.objects if o.type == 'MESH']
    points = [o.matrix_world @ Vector(c) for o in meshes for c in o.bound_box]
    lo = Vector([min(p[i] for p in points) for i in range(3)])
    hi = Vector([max(p[i] for p in points) for i in range(3)])
    center = (lo + hi) / 2
    span = max(hi - lo)
    for o in meshes:
        o.location = (o.location - center) / span
        o.scale /= span

    s = bpy.context.scene
    s.render.engine = 'CYCLES'
    s.cycles.samples = 32
    s.cycles.use_denoising = True
    s.render.resolution_x = 900
    s.render.resolution_y = 900
    s.render.resolution_percentage = 100
    s.world = bpy.data.worlds.new('Studio')
    s.world.use_nodes = True
    s.world.node_tree.nodes['Background'].inputs[0].default_value = (.18, .21, .25, 1)
    s.world.node_tree.nodes['Background'].inputs[1].default_value = .6
    s.view_settings.view_transform = 'AgX'
    s.view_settings.exposure = .6

    def aim(o):
        o.rotation_euler = (-o.location).to_track_quat('-Z', 'Y').to_euler()

    for pos, power in [((-2, -3, 4), 330), ((3, -2, 2), 250), ((1, 3, 3), 400)]:
        bpy.ops.object.light_add(type='AREA', location=pos)
        o = bpy.context.object
        o.data.energy = power
        o.data.size = 3
        aim(o)

    bpy.ops.object.camera_add()
    cam = bpy.context.object
    cam.data.type = 'ORTHO'
    cam.data.ortho_scale = 1.3
    s.camera = cam
    for name, pos in [('front', (0, -3, .05)), ('side', (3, 0, .05)), ('angle', (2, -3, 1))]:
        cam.location = pos
        aim(cam)
        s.render.filepath = str(out / (name + '.png'))
        bpy.ops.render.render(write_still=True)
    print(f'RENDERED {prop} -> {out}', flush=True)

print('RENDER_ALL_DONE', flush=True)