"""Bake original Mantaflow combustion fields for the runtime fireball flipbooks.

Run headless in Blender. This produces simulation source/cache/field data, not
a gameplay preview. Atlas shading/packing is performed by pack_fluid_atlases.py.
"""
import bpy
import json
import math
import sys
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parent
SCENE = ROOT / 'Fireball_Fluid_Editable.blend'
START, END, FIRST_CAPTURE = 1, 144, 49
FPS, RESOLUTION = 24, 96


def author():
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)
    scene = bpy.context.scene
    scene.frame_start, scene.frame_end = START, END
    scene.render.fps = FPS
    scene.gravity = (0, 0, -5.0)
    scene.render.threads_mode = 'FIXED'
    scene.render.threads = 12

    bpy.ops.mesh.primitive_cube_add(size=2, location=(0, 0, .32))
    domain = bpy.context.object
    domain.name = 'Fireball_Combustion_Domain'
    fluid = domain.modifiers.new('Mantaflow_Combustion', 'FLUID')
    fluid.fluid_type = 'DOMAIN'
    ds = fluid.domain_settings
    ds.domain_type = 'GAS'
    ds.resolution_max = RESOLUTION
    ds.cache_type = 'MODULAR'
    ds.cache_directory = str(ROOT / 'Cache')
    ds.cache_frame_start, ds.cache_frame_end = START, END
    ds.cache_data_format = 'OPENVDB'
    ds.cache_resumable = True
    ds.use_adaptive_domain = False
    ds.time_scale = .85
    ds.alpha, ds.beta = -.015, .65
    ds.vorticity = .65
    ds.burning_rate = 1.25
    ds.flame_vorticity = 1.15
    ds.flame_ignition, ds.flame_max_temp = 1.15, 2.3
    ds.flame_smoke = .08
    ds.use_dissolve_smoke = True
    ds.dissolve_speed = 10
    ds.use_dissolve_smoke_log = True
    ds.use_noise = True
    ds.noise_scale = 2
    ds.noise_strength = .85
    ds.noise_pos_scale = 1.1
    ds.noise_time_anim = .8
    for side in ['front', 'back', 'left', 'right', 'top', 'bottom']:
        setattr(ds, 'use_collision_border_' + side, False)

    # Uneven fuel surface and independently pulsing lobes prevent a stable shell.
    noise = bpy.data.textures.new('Fuel_Surface_Clouds', type='CLOUDS')
    noise.noise_scale, noise.noise_depth = .16, 2
    lobes = [((0, 0, -.06), (.29, .26, .23), .95),
             ((-.18, .06, .04), (.18, .17, .20), .70),
             ((.12, -.13, .07), (.17, .18, .22), .62)]
    for index, (location, scale, fuel) in enumerate(lobes):
        bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=3, radius=1, location=location)
        source = bpy.context.object
        source.name = 'Fuel_Lobe_' + str(index)
        source.scale = scale
        bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
        displace = source.modifiers.new('Uneven_Fuel_Surface', 'DISPLACE')
        displace.texture, displace.strength, displace.mid_level = noise, .085, .5
        flow = source.modifiers.new('Continuous_Fuel', 'FLUID')
        flow.fluid_type = 'FLOW'
        fs = flow.flow_settings
        fs.flow_type, fs.flow_behavior, fs.flow_source = 'FIRE', 'INFLOW', 'MESH'
        fs.fuel_amount, fs.surface_distance, fs.volume_density = fuel, 1.3, .45
        fs.use_initial_velocity = True
        fs.velocity_coord = (.04 * math.cos(index * 2.1), .04 * math.sin(index * 2.1), .06)
        fs.velocity_normal = .10
        fs.subframes = 1
        source.hide_render = True
        source.display_type = 'WIRE'
        for frame in range(1, END + 9, 8):
            phase = frame * .115 + index * 2.2
            fs.fuel_amount = fuel * (.82 + .18 * math.sin(phase))
            fs.keyframe_insert(data_path='fuel_amount', frame=frame)
            source.location = (location[0] + .025 * math.sin(phase * .83),
                               location[1] + .025 * math.cos(phase),
                               location[2] + .018 * math.sin(phase * 1.3))
            source.keyframe_insert(data_path='location', frame=frame)

    # This editable volume shader is provided for subsequent authoring. No
    # camera render is launched; the runtime bake integrates the cached fields.
    material = bpy.data.materials.new('Editable_Combustion_Volume')
    material.use_nodes = True
    nodes, links = material.node_tree.nodes, material.node_tree.links
    nodes.clear()
    output = nodes.new('ShaderNodeOutputMaterial')
    volume = nodes.new('ShaderNodeVolumePrincipled')
    volume.inputs['Density'].default_value = .3
    volume.inputs['Blackbody Intensity'].default_value = 1
    links.new(volume.outputs['Volume'], output.inputs['Volume'])
    domain.data.materials.append(material)
    bpy.ops.object.select_all(action='DESELECT')
    domain.select_set(True)
    bpy.context.view_layer.objects.active = domain
    scene.frame_set(1)
    bpy.ops.wm.save_as_mainfile(filepath=str(SCENE))
    (ROOT / 'simulation.json').write_text(json.dumps({
        'source': 'Project-authored Blender Mantaflow continuous gas combustion',
        'blender': bpy.app.version_string, 'fps': FPS, 'frames': [START, END],
        'capture_frames': [FIRST_CAPTURE, END], 'domain_resolution': RESOLUTION,
        'noise_upres': 2, 'domain_world_size': [2, 2, 2], 'domain_center': [0, 0, .32],
        'burning_rate': 1.25, 'fuel_lobes': 3, 'buoyancy': .65,
        'outputs': ['Fireball_Fluid_Editable.blend', 'Cache', 'Fields'],
        'purpose': 'Production simulation and texture baking; no game/visual acceptance',
    }, indent=2), encoding='utf-8')
    return domain


def bake(domain):
    print('FIREBALL_FLUID_BAKE_DATA_BEGIN', flush=True)
    bpy.ops.fluid.bake_data()
    bpy.ops.wm.save_as_mainfile(filepath=str(SCENE))
    print('FIREBALL_FLUID_BAKE_NOISE_BEGIN', flush=True)
    bpy.ops.fluid.bake_noise()
    bpy.ops.wm.save_as_mainfile(filepath=str(SCENE))
    print('FIREBALL_FLUID_BAKE_COMPLETE', flush=True)


def export_fields(domain):
    output = ROOT / 'Fields'
    output.mkdir(exist_ok=True)
    ds = domain.modifiers['Mantaflow_Combustion'].domain_settings
    for frame in range(FIRST_CAPTURE, END + 1):
        bpy.context.scene.frame_set(frame)
        bpy.context.view_layer.update()
        evaluated = domain.evaluated_get(bpy.context.evaluated_depsgraph_get())
        current = evaluated.modifiers['Mantaflow_Combustion'].domain_settings
        flame = np.array(current.flame_grid[:], dtype=np.float32)
        dims = np.array(current.domain_resolution[:], dtype=int)
        # High-resolution noise grids contain an integer upscale in each axis.
        factor = round((flame.size / max(1, int(np.prod(dims)))) ** (1 / 3))
        shape = tuple((dims * factor)[::-1])
        if flame.size == 0:
            raise RuntimeError('No combustion field loaded for baking at frame ' + str(frame))
        np.savez_compressed(output / f'flame_{frame:04d}.npz', flame=flame.reshape(shape))
        if (frame - FIRST_CAPTURE) % 12 == 0:
            print('FIREBALL_FLUID_FIELD', frame, shape, flush=True)
    print('FIREBALL_FLUID_FIELDS_EXPORTED', flush=True)


if __name__ == '__main__':
    ROOT.mkdir(parents=True, exist_ok=True)
    mode = sys.argv[sys.argv.index('--') + 1] if '--' in sys.argv else 'all'
    if mode == 'export':
        bpy.ops.wm.open_mainfile(filepath=str(SCENE))
        domain = bpy.data.objects['Fireball_Combustion_Domain']
    else:
        domain = author()
        bake(domain)
    export_fields(domain)
