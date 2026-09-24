"""Author a compact combustion field for the persistent fireball core.

Background Mantaflow bake + numerical field projection. No camera renders.
blender --background --threads 6 --python this.py -- --output ABS_PATH
"""
import argparse
import json
import math
import sys
from pathlib import Path

import bpy
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from bake_muzzle_smoke import activate, resample


def setup(out):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.render.fps = 24
    scene.frame_start, scene.frame_end = 1, 104
    scene.unit_settings.system = 'METRIC'
    scene.gravity = (0, 0, -2.4)
    bpy.ops.mesh.primitive_cube_add(size=1.6, location=(0, 0, 0))
    domain = bpy.context.object
    domain.name = 'Fireball_CombustionDomain'
    mod = domain.modifiers.new('Mantaflow', 'FLUID')
    mod.fluid_type = 'DOMAIN'
    bpy.context.view_layer.update()
    settings = mod.domain_settings
    settings.domain_type = 'GAS'
    settings.resolution_max = 96
    settings.cache_directory = str(out / 'cache')
    settings.cache_frame_start, settings.cache_frame_end = 1, 104
    settings.cache_type = 'MODULAR'
    settings.cache_data_format = 'OPENVDB'
    settings.cache_resumable = False
    settings.use_adaptive_domain = False
    settings.use_noise = False
    settings.time_scale = 0.8
    settings.vorticity = 1.3
    settings.flame_vorticity = 1.1
    settings.burning_rate = 1.0
    settings.flame_smoke = 0.45
    settings.timesteps_max = 4
    settings.use_dissolve_smoke = True
    settings.dissolve_speed = 35
    for side in ('front', 'back', 'left', 'right', 'top', 'bottom'):
        setattr(settings, 'use_collision_border_' + side, False)
    # Offset fuel lobes produce interlocking curls rather than a symmetric cone.
    for i, (location, scale, velocity) in enumerate([
            ((-0.09, 0.0, -0.15), (0.15, 0.16, 0.13), (0.28, 0.10, 0.18)),
            ((0.10, -0.06, -0.05), (0.13, 0.15, 0.15), (-0.16, 0.24, 0.11)),
            ((0.01, 0.09, 0.08), (0.14, 0.12, 0.13), (-0.10, -0.22, 0.08))]):
        bpy.ops.mesh.primitive_uv_sphere_add(segments=24, ring_count=16, radius=1, location=location)
        obj = bpy.context.object
        obj.name = 'Fireball_FuelLobe_%d' % i
        obj.scale = scale
        bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
        flowmod = obj.modifiers.new('Fuel', 'FLUID')
        flowmod.fluid_type = 'FLOW'
        bpy.context.view_layer.update()
        flow = flowmod.flow_settings
        flow.flow_type = 'BOTH'
        flow.flow_behavior = 'INFLOW'
        flow.density = 0.4
        flow.temperature = 1.0
        flow.use_initial_velocity = True
        flow.velocity_coord = velocity
        for frame in list(range(1, 105, 8)) + [104]:
            phase = frame * 0.075 + i * 2.1
            flow.fuel_amount = 1.1 + 0.22 * math.sin(phase)
            flow.keyframe_insert(data_path='fuel_amount', frame=frame)
            obj.location = (location[0] + 0.025 * math.sin(phase),
                            location[1] + 0.025 * math.cos(phase), location[2])
            obj.keyframe_insert(data_path='location', frame=frame)
        obj.hide_render = True
    scene.frame_set(1)
    activate(domain)
    return domain


def project(domain):
    bpy.context.view_layer.update()
    evaluated = domain.evaluated_get(bpy.context.evaluated_depsgraph_get())
    settings = evaluated.modifiers['Mantaflow'].domain_settings
    sx, sy, sz = settings.domain_resolution
    fields = []
    for name in ('flame_grid', 'density_grid', 'temperature_grid'):
        data = np.asarray(getattr(settings, name)[:], dtype=np.float32)
        if data.size != sx * sy * sz or not data.size:
            raise RuntimeError('Cannot export combustion grid ' + name)
        fields.append(data.reshape((sz, sy, sx)))
    flame, density, temperature = fields
    # Project the compact central volume, not the entire upward exhaust plume.
    coordinates = (np.arange(256, dtype=np.float32) + 0.5) / 256
    x = (coordinates * 1.0 + 0.3) / 1.6 * sx - 0.5
    y = (coordinates * 1.0 + 0.3) / 1.6 * sz - 0.5
    depth = flame.sum(axis=1) * (1.6 / sy)
    smoke = density.sum(axis=1) * (1.6 / sy)
    heat = (np.maximum(temperature, 0) * flame).sum(axis=1) / np.maximum(flame.sum(axis=1), 0.001)
    return np.stack([resample(value, x, y) for value in (depth, heat, smoke)], axis=-1)


def export(domain, out):
    raw = []
    for frame in range(33, 105):
        bpy.context.scene.frame_set(frame)
        raw.append(project(domain))
    raw = np.stack(raw)
    # One scale per channel over the complete sequence avoids per-frame pumping.
    scale = np.maximum(np.percentile(raw, 99.2, axis=(0, 1, 2)), 0.001)
    raw = np.clip(raw / scale, 0, 1).astype(np.float32)
    frames = list(raw[8:64])
    for i in range(8):
        blend = (i + 1) / 8
        blend = blend * blend * (3 - 2 * blend)
        frames.append(raw[64+i] * (1-blend) + raw[i] * blend)
    atlas = np.ones((2048, 2048, 4), dtype=np.float32)
    for i, field in enumerate(frames):
        # Repeat edge texels into a four-pixel gutter. The material's own smooth
        # core mask provides silhouette opacity; this texture only carries fields.
        field[:4] = field[4]; field[-4:] = field[-5]
        field[:, :4] = field[:, 4:5]; field[:, -4:] = field[:, -5:-4]
        x, y = (i % 8) * 256, (7-i//8) * 256
        atlas[y:y+256, x:x+256, :3] = field
    image = bpy.data.images.new('T_FireballCombustionFields', 2048, 2048, alpha=False)
    image.colorspace_settings.name = 'Non-Color'
    image.pixels.foreach_set(atlas.ravel())
    image.filepath_raw = str(out / 'T_FireballCombustionFields.png')
    image.file_format = 'PNG'
    image.save()
    (out / 'bake-manifest.json').write_text(json.dumps({
        'source': 'Original FPSGAME Mantaflow combustion simulation',
        'resolution': [96, 96, 96], 'simulation_frames': 104,
        'simulation_fps': 24, 'simulation_time_scale': 0.8,
        'atlas': [2048, 2048], 'grid': [8, 8], 'frames': 64, 'tile_size': 256,
        'channels': {'R': 'integrated flame', 'G': 'flame-weighted temperature', 'B': 'integrated smoke'},
        'linear_data': True, 'normalization': [float(v) for v in scale],
        'loop_seam': '8-frame smooth overlap from 72 warm simulation frames',
        'provenance': 'Original procedural sources, no downloaded artwork',
        'runtime_tested': False, 'visual_tested': False,
    }, indent=2), encoding='utf-8')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', required=True)
    parser.add_argument('--export-only', action='store_true')
    args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:])
    out = Path(args.output).resolve()
    out.mkdir(parents=True, exist_ok=True)
    blend = out / 'FireballCombustion.blend'
    if args.export_only:
        bpy.ops.wm.open_mainfile(filepath=str(blend))
        domain = bpy.data.objects['Fireball_CombustionDomain']
    else:
        domain = setup(out)
        bpy.ops.wm.save_as_mainfile(filepath=str(blend))
        print('FIREBALL_COMBUSTION_BAKE_START', flush=True)
        bpy.ops.fluid.bake_data()
        bpy.ops.wm.save_as_mainfile(filepath=str(blend))
    export(domain, out)
    print('FIREBALL_COMBUSTION_ATLAS_SAVED', flush=True)


if __name__ == '__main__':
    main()
