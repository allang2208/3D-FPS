"""Bake original Mantaflow smoke and project its density into a game flipbook.

Background asset production only: no camera renders or gameplay tests.
blender --background --threads 6 --python this.py -- --output ABS_PATH
"""
import argparse
import json
import sys
from pathlib import Path

import bpy
import numpy as np


def activate(obj):
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj


def setup(out):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.render.fps = 30
    scene.frame_start, scene.frame_end = 1, 64
    scene.unit_settings.system = 'METRIC'
    scene.gravity = (0, 0, -2.0)
    bpy.ops.mesh.primitive_cube_add(size=1.6, location=(0, 0, 0))
    domain = bpy.context.object
    domain.name = 'MuzzleSmoke_Domain'
    mod = domain.modifiers.new('Mantaflow', 'FLUID')
    mod.fluid_type = 'DOMAIN'
    bpy.context.view_layer.update()
    settings = mod.domain_settings
    settings.domain_type = 'GAS'
    settings.resolution_max = 96
    settings.cache_directory = str(out / 'cache')
    settings.cache_frame_start, settings.cache_frame_end = 1, 64
    settings.cache_type = 'MODULAR'
    settings.cache_data_format = 'OPENVDB'
    settings.cache_resumable = False
    settings.use_adaptive_domain = False
    settings.use_noise = False
    settings.time_scale = 0.7
    settings.vorticity = 1.7
    settings.timesteps_max = 4
    settings.use_dissolve_smoke = True
    settings.dissolve_speed = 55
    for side in ('front', 'back', 'left', 'right', 'top', 'bottom'):
        setattr(settings, 'use_collision_border_' + side, False)
    # Three overlapping irregular sources break the symmetry of a round puff.
    for i, (location, scale, velocity) in enumerate([
            ((0, 0, -0.22), (0.125, 0.105, 0.075), (0.22, 0.10, 0.65)),
            ((0.07, -0.025, -0.20), (0.065, 0.080, 0.055), (0.40, -0.20, 0.48)),
            ((-0.055, 0.04, -0.205), (0.075, 0.055, 0.065), (-0.30, 0.18, 0.57))]):
        bpy.ops.mesh.primitive_uv_sphere_add(segments=20, ring_count=12, radius=1, location=location)
        source = bpy.context.object
        source.name = 'MuzzleSmoke_Impulse_%d' % i
        source.scale = scale
        bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
        flowmod = source.modifiers.new('SmokeImpulse', 'FLUID')
        flowmod.fluid_type = 'FLOW'
        bpy.context.view_layer.update()
        flow = flowmod.flow_settings
        flow.flow_type = 'SMOKE'
        flow.flow_behavior = 'INFLOW'
        flow.density = 0.8
        flow.temperature = 0.35
        flow.use_initial_velocity = True
        flow.velocity_coord = velocity
        flow.use_inflow = True
        flow.keyframe_insert(data_path='use_inflow', frame=1)
        flow.keyframe_insert(data_path='use_inflow', frame=4)
        flow.use_inflow = False
        flow.keyframe_insert(data_path='use_inflow', frame=5)
        source.hide_render = True
    scene.frame_set(1)
    activate(domain)
    return domain


def project_density(domain):
    """Integrate through Y, leaving a side-view X/Z optical depth image."""
    bpy.context.view_layer.update()
    evaluated = domain.evaluated_get(bpy.context.evaluated_depsgraph_get())
    settings = evaluated.modifiers['Mantaflow'].domain_settings
    values = np.asarray(settings.density_grid[:], dtype=np.float32)
    size = tuple(settings.domain_resolution)
    if values.size != int(np.prod(size)) or not values.size:
        raise RuntimeError('Cannot project baked smoke density: %s / %s' % (values.size, size))
    # Mantaflow linear indexing: X is the fastest-varying coordinate.
    grid = values.reshape((size[2], size[1], size[0]))
    return grid.sum(axis=1) * (1.6 / size[1])


def resample(image, x, y):
    x = np.clip(x, 0, image.shape[1] - 1)
    y = np.clip(y, 0, image.shape[0] - 1)
    x0, y0 = x.astype(int), y.astype(int)
    x1 = np.minimum(x0 + 1, image.shape[1] - 1)
    y1 = np.minimum(y0 + 1, image.shape[0] - 1)
    tx, ty = x - x0, y - y0
    return ((image[y0[:, None], x0] * (1-tx) + image[y0[:, None], x1] * tx) * (1-ty[:, None])
            + (image[y1[:, None], x0] * (1-tx) + image[y1[:, None], x1] * tx) * ty[:, None])


def export_atlas(domain, out):
    fields = []
    centers = []
    widths = []
    for frame in range(1, 65):
        bpy.context.scene.frame_set(frame)
        field = project_density(domain)
        fields.append(field)
        total = float(field.sum())
        if total <= 0:
            raise RuntimeError('Smoke frame %d has no density to export' % frame)
        yy, xx = np.indices(field.shape)
        cx, cy = float((xx * field).sum()/total), float((yy * field).sum()/total)
        centers.append((cx, cy))
        occupied = np.argwhere(field > field.max() * 0.008)
        radius = np.max(np.abs(occupied - [cy, cx]))
        widths.append(max(12.0, float(radius) * 2.4))
    # Growing sprite size is authored in Niagara. The atlas tracks the puff's
    # center and extent, so a baked plume does not translate twice at runtime.
    width_curve = np.convolve(np.pad(widths, (3, 3), mode='edge'), np.ones(7)/7, mode='valid')
    tiles = []
    coordinates = (np.arange(256, dtype=np.float32) + 0.5) / 256 - 0.5
    uv = coordinates + 0.5
    edge = np.clip(np.minimum(uv, 1-uv)/0.045, 0, 1)
    edge = edge * edge * (3-2*edge)
    for field, (cx, cy), width in zip(fields, centers, width_curve):
        optical_depth = resample(field, cx + coordinates*width, cy + coordinates*width)
        # Beer-Lambert coverage preserves the low-density curled boundary.
        coverage = 1.0 - np.exp(-optical_depth * 16.0)
        coverage *= edge[:, None] * edge[None, :]
        # Four transparent texels protect bilinear filtering at tile seams.
        coverage[:4] = 0; coverage[-4:] = 0
        coverage[:, :4] = 0; coverage[:, -4:] = 0
        tiles.append(coverage.astype(np.float32))
    atlas = np.ones((2048, 2048, 4), dtype=np.float32)
    for index, tile in enumerate(tiles):
        col, row = index % 8, index // 8
        # Blender's pixel buffer is bottom-up; frame zero belongs at PNG top-left.
        y = (7-row) * 256
        atlas[y:y+256, col*256:(col+1)*256, :3] = tile[:, :, None]
    image = bpy.data.images.new('T_MuzzleSmokeMantaflowV14', 2048, 2048, alpha=False, float_buffer=False)
    image.colorspace_settings.name = 'Non-Color'
    image.pixels.foreach_set(atlas.ravel())
    image.filepath_raw = str(out / 'T_MuzzleSmokeMantaflowV14.png')
    image.file_format = 'PNG'
    image.save()
    return {'frames': 64, 'columns': 8, 'rows': 8, 'tile_px': 256, 'gutter_px': 4,
            'atlas_px': [2048, 2048], 'channel': 'R linear density coverage, RGB identical',
            'frame_order': 'left to right, top to bottom', 'interpolation': 'two adjacent frames',
            'projection': 'density integrated along Y; center/extent tracked per frame',
            'fps_source': 30, 'time_scale': 0.7, 'resolution': 96,
            'source': 'Original FPSGAME Mantaflow impulse smoke',
            'runtime': 'World-space Niagara sprites; no runtime volume simulation',
            'status': 'authored_not_gameplay_or_visual_tested'}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', required=True)
    parser.add_argument('--export-only', action='store_true')
    args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:])
    out = Path(args.output).resolve()
    out.mkdir(parents=True, exist_ok=True)
    blend = out / 'MuzzleSmokeMantaflowV14.blend'
    if args.export_only:
        bpy.ops.wm.open_mainfile(filepath=str(blend))
        domain = bpy.data.objects['MuzzleSmoke_Domain']
    else:
        domain = setup(out)
        bpy.ops.wm.save_as_mainfile(filepath=str(blend))
        print('MUZZLE_MANTAFLOW_BAKE_START', flush=True)
        bpy.ops.fluid.bake_data()
        bpy.ops.wm.save_as_mainfile(filepath=str(blend))
    manifest = export_atlas(domain, out)
    (out / 'bake-manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    print('MUZZLE_MANTAFLOW_ATLAS_SAVED', flush=True)


if __name__ == '__main__':
    main()
