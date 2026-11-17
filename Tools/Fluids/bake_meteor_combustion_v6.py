"""Original Meteor V6 combustion atlases. Background production, no renders/tests.

Blender --background --threads 6 --python this.py -- --kind impact|wake
The two recipes retain editable blends, OpenVDB caches, raw projected fields and
an explicit linear-data atlas contract. No existing fire or ground assets change.
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

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'SourceAssets/MeteorCombustionV6_20261114'


def setup(kind, folder):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.render.fps = 30
    frames = 72 if kind == 'impact' else 104
    scene.frame_start, scene.frame_end = 1, frames
    scene.unit_settings.system = 'METRIC'
    scene.gravity = (0, 0, -2.4)
    width = 4.0 if kind == 'impact' else 2.4
    bpy.ops.mesh.primitive_cube_add(size=width)
    domain = bpy.context.object
    domain.name = 'Meteor_' + kind + '_Domain'
    modifier = domain.modifiers.new('Mantaflow', 'FLUID')
    modifier.fluid_type = 'DOMAIN'
    bpy.context.view_layer.update()
    settings = modifier.domain_settings
    settings.domain_type = 'GAS'
    settings.resolution_max = 96 if kind == 'impact' else 80
    settings.cache_directory = str(folder / 'cache')
    settings.cache_frame_start, settings.cache_frame_end = 1, frames
    settings.cache_type = 'MODULAR'
    settings.cache_data_format = 'OPENVDB'
    settings.cache_resumable = False
    settings.use_adaptive_domain = False
    settings.use_noise = False
    settings.time_scale = .8
    settings.vorticity = 1.7
    settings.flame_vorticity = 1.35
    settings.burning_rate = 1.1 if kind == 'impact' else .85
    settings.flame_smoke = .65 if kind == 'impact' else .35
    settings.timesteps_max = 4
    settings.use_dissolve_smoke = True
    settings.dissolve_speed = 38 if kind == 'impact' else 30
    for side in ('front', 'back', 'left', 'right', 'top', 'bottom'):
        setattr(settings, 'use_collision_border_' + side, False)

    if kind == 'impact':
        lobes = [((-.18, .02, -1.10), (.29, .24, .20), (-1.1, .15, 1.0)),
                 ((.17, -.09, -1.06), (.25, .28, .22), (1.0, -.55, 1.2)),
                 ((.02, .19, -1.01), (.22, .21, .24), (.1, 1.1, 1.5)),
                 ((.01, -.13, -.92), (.20, .19, .22), (.2, -.4, 1.75))]
    else:
        lobes = [((-.10, .02, -.62), (.17, .14, .16), (.22, .12, 1.0)),
                 ((.10, -.07, -.55), (.15, .18, .16), (-.18, .25, 1.3)),
                 ((.00, .11, -.48), (.13, .12, .15), (.1, -.21, 1.15))]
    for i, (location, scale, velocity) in enumerate(lobes):
        bpy.ops.mesh.primitive_uv_sphere_add(segments=20, ring_count=12, radius=1, location=location)
        obj = bpy.context.object
        obj.name = 'Meteor_' + kind + '_Fuel_%d' % i
        obj.scale = scale
        bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
        mod = obj.modifiers.new('Fuel', 'FLUID')
        mod.fluid_type = 'FLOW'
        bpy.context.view_layer.update()
        flow = mod.flow_settings
        flow.flow_type = 'BOTH'
        flow.flow_behavior = 'INFLOW'
        flow.density = .65 if kind == 'impact' else .30
        flow.temperature = 1.2
        flow.fuel_amount = 1.3
        flow.use_initial_velocity = True
        flow.velocity_coord = velocity
        if kind == 'impact':
            flow.use_inflow = True
            flow.keyframe_insert(data_path='use_inflow', frame=1)
            flow.keyframe_insert(data_path='use_inflow', frame=4 + i % 2)
            flow.use_inflow = False
            flow.keyframe_insert(data_path='use_inflow', frame=5 + i % 2)
        else:
            for frame in list(range(1, frames + 1, 8)) + [frames]:
                phase = frame * .075 + i * 2.1
                flow.fuel_amount = 1.05 + .24 * math.sin(phase)
                flow.keyframe_insert(data_path='fuel_amount', frame=frame)
                obj.location = (location[0] + .035 * math.sin(phase),
                                location[1] + .025 * math.cos(phase), location[2])
                obj.keyframe_insert(data_path='location', frame=frame)
        obj.hide_render = True
    scene.frame_set(1)
    activate(domain)
    return domain, width


def project(domain, width):
    bpy.context.view_layer.update()
    ds = domain.evaluated_get(bpy.context.evaluated_depsgraph_get()).modifiers['Mantaflow'].domain_settings
    sx, sy, sz = ds.domain_resolution
    fields = []
    for field in ('flame_grid', 'density_grid', 'temperature_grid'):
        array = np.asarray(getattr(ds, field)[:], dtype=np.float32)
        if array.size != sx * sy * sz or not array.size:
            raise RuntimeError('Missing baked field ' + field)
        fields.append(array.reshape((sz, sy, sx)))
    flame, density, temperature = fields
    flame_depth = flame.sum(axis=1) * width / sy
    smoke_depth = density.sum(axis=1) * width / sy
    heat = (np.maximum(temperature, 0) * flame).sum(axis=1) / np.maximum(flame.sum(axis=1), .001)
    x = (np.arange(248, dtype=np.float32) + .5) / 248 * sx - .5
    y = (np.arange(248, dtype=np.float32) + .5) / 248 * sz - .5
    return np.stack([resample(field, x, y) for field in (flame_depth, heat, smoke_depth)], axis=-1)


def export(kind, domain, width, folder):
    source_frames = list(range(1, 73)) if kind == 'impact' else list(range(33, 105))
    projected = []
    for frame in source_frames:
        bpy.context.scene.frame_set(frame)
        projected.append(project(domain, width))
    raw = np.stack(projected)
    np.savez_compressed(folder / 'projected-fields.npz', fields=raw, source_frames=source_frames)
    # One sequence-wide range; never renormalize individual frames.
    scales = np.maximum(np.percentile(raw, 99.65, axis=(0, 1, 2)), .001)
    normalized = np.clip(raw / scales, 0, 1)
    if kind == 'impact':
        frames = []
        for source in np.linspace(0, 71, 64):
            lo = int(source)
            frames.append(normalized[lo] * (1 - source + lo) + normalized[min(lo + 1, 71)] * (source - lo))
    else:
        frames = list(normalized[8:64])
        for i in range(8):
            t = (i + 1) / 8
            t = t * t * (3 - 2 * t)
            frames.append(normalized[64 + i] * (1 - t) + normalized[i] * t)
    atlas = np.zeros((2048, 2048, 4), dtype=np.float32)
    coord = (np.arange(248, dtype=np.float32) + .5) / 248
    margin = np.minimum(coord, 1 - coord)
    edge = np.clip(margin / .045, 0, 1)
    edge = edge * edge * (3 - 2 * edge)
    for i, field in enumerate(frames):
        field = field.copy()
        field *= edge[:, None, None] * edge[None, :, None]
        dz, dx = np.gradient(field[:, :, 2])
        shade = np.clip(.62 + dz * 2.8 - dx * 1.7, .28, .9)
        tile = np.zeros((256, 256, 4), dtype=np.float32)
        tile[4:-4, 4:-4, :3] = field
        tile[4:-4, 4:-4, 3] = shade
        x, y = i % 8 * 256, (7 - i // 8) * 256
        atlas[y:y + 256, x:x + 256] = tile
    name = 'T_MeteorImpactFields' if kind == 'impact' else 'T_MeteorWakeFields'
    image = bpy.data.images.new(name, 2048, 2048, alpha=True)
    image.colorspace_settings.name = 'Non-Color'
    image.alpha_mode = 'CHANNEL_PACKED'
    image.pixels.foreach_set(atlas.ravel())
    image.filepath_raw = str(folder / (name + '.png'))
    image.file_format = 'PNG'
    image.save()
    manifest = dict(kind=kind, source='Original FPSGAME Mantaflow simulation',
                    texture=name, atlas=[2048, 2048], grid=[8, 8], tile=256, gutter=4,
                    frames=64, source_frames=source_frames, fps=30, time_scale=.8,
                    domain_metres=width, resolution=96 if kind == 'impact' else 80,
                    channels=dict(R='integrated flame', G='flame weighted heat',
                                  B='integrated smoke', A='baked smoke shading, NOT opacity'),
                    normalization=scales.tolist(), linear_data=True,
                    playback='clamp' if kind == 'impact' else 'loop with 8 frame overlap',
                    generated_video_used=False, rendered=False, runtime_tested=False)
    (folder / 'atlas-manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    print('METEOR_V6_ATLAS_SAVED ' + str(image.filepath_raw), flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--kind', choices=['impact', 'wake'], required=True)
    parser.add_argument('--export-only', action='store_true')
    args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:])
    folder = OUT / args.kind
    folder.mkdir(parents=True, exist_ok=True)
    blend = folder / ('Meteor_' + args.kind + '.blend')
    if args.export_only:
        bpy.ops.wm.open_mainfile(filepath=str(blend))
        domain = bpy.data.objects['Meteor_' + args.kind + '_Domain']
        width = 4.0 if args.kind == 'impact' else 2.4
    else:
        domain, width = setup(args.kind, folder)
        bpy.ops.wm.save_as_mainfile(filepath=str(blend))
        print('METEOR_V6_BAKE_START ' + args.kind, flush=True)
        bpy.ops.fluid.bake_data()
        bpy.ops.wm.save_as_mainfile(filepath=str(blend))
    export(args.kind, domain, width, folder)


if __name__ == '__main__':
    main()
