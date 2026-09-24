"""Bake four original Mantaflow liquid impulses into one packed sprite atlas.

Production texture rendering only; no gameplay, preview, or acceptance renders.
blender --background --threads 6 --python this.py -- --output ABS_PATH
"""
import argparse
import gzip
import json
import math
import struct
import sys
from pathlib import Path

import bpy
import numpy as np
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
from bake_mantaflow_foundation import activate, cube

FRAMES = 32
TILE = 128


def setup(out, variant):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.render.fps = 50
    scene.frame_start, scene.frame_end = 1, FRAMES
    scene.unit_settings.system = 'METRIC'
    domain = cube('LiquidImpulse', (0, 0, .255), (.8, .7, .57))
    mod = domain.modifiers.new('Mantaflow', 'FLUID')
    mod.fluid_type = 'DOMAIN'
    bpy.context.view_layer.update()
    ds = mod.domain_settings
    ds.domain_type = 'LIQUID'
    ds.resolution_max = 72
    ds.cache_directory = str(out / ('variant_%d' % variant) / 'cache')
    ds.cache_frame_start, ds.cache_frame_end = 1, FRAMES
    ds.cache_type = 'MODULAR'
    ds.cache_data_format = 'UNI'
    ds.cache_resumable = False
    ds.timesteps_min, ds.timesteps_max = 1, 6
    ds.use_mesh = True
    ds.mesh_scale = 2
    ds.mesh_particle_radius = 1.35
    ds.mesh_smoothen_pos, ds.mesh_smoothen_neg = 1, 1
    ds.flip_ratio = .94
    for side in ('front', 'back', 'left', 'right', 'top', 'bottom'):
        setattr(ds, 'use_collision_border_' + side, False)

    # Small asymmetric liquid lobes represent the impact's initial displaced
    # water. FLIP solves their merge, stretching, breakup and gravitational fall.
    rng = np.random.default_rng(41023 + variant * 1709)
    count = (8, 7, 9, 8)[variant]
    for i in range(count + 1):
        angle = 2 * math.pi * i / count + variant * .53
        center = i == count
        radius = 0 if center else float(rng.uniform(.035, .052))
        location = (math.cos(angle) * radius, math.sin(angle) * radius, .034)
        bpy.ops.mesh.primitive_uv_sphere_add(segments=16, ring_count=10, radius=1, location=location)
        obj = bpy.context.object
        obj.name = 'DisplacedWater_%02d' % i
        obj.scale = (.023, .026, .032) if center else (.028, .027, float(rng.uniform(.018, .028)))
        bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
        fm = obj.modifiers.new('InitialWater', 'FLUID')
        fm.fluid_type = 'FLOW'
        bpy.context.view_layer.update()
        fs = fm.flow_settings
        fs.flow_type, fs.flow_behavior = 'LIQUID', 'GEOMETRY'
        fs.use_initial_velocity = True
        radial = float(rng.uniform(.45, .9))
        bias = (.0, .18, -.13, .26)[variant]
        upward = float(rng.uniform(1.25, 2.1)) if not center else (2.05, 1.6, 2.25, 1.8)[variant]
        fs.velocity_coord = (math.cos(angle) * radial + bias,
                             math.sin(angle) * radial, upward)
        obj.hide_render = True

    # Bake view-space normal XY, aerated-edge weight, and silhouette coverage.
    mat = bpy.data.materials.new('PackedLiquidSurface')
    mat.use_nodes = True
    nd, links = mat.node_tree.nodes, mat.node_tree.links
    nd.clear()
    geo = nd.new('ShaderNodeNewGeometry')
    transform = nd.new('ShaderNodeVectorTransform')
    transform.vector_type = 'NORMAL'
    transform.convert_from, transform.convert_to = 'WORLD', 'CAMERA'
    links.new(geo.outputs['Normal'], transform.inputs['Vector'])
    sep = nd.new('ShaderNodeSeparateXYZ')
    links.new(transform.outputs['Vector'], sep.inputs[0])
    combine = nd.new('ShaderNodeCombineXYZ')
    for channel in ('X', 'Y'):
        scale = nd.new('ShaderNodeMath'); scale.operation = 'MULTIPLY_ADD'
        scale.inputs[1].default_value = .5; scale.inputs[2].default_value = .5
        links.new(sep.outputs[channel], scale.inputs[0])
        links.new(scale.outputs[0], combine.inputs[channel])
    facing = nd.new('ShaderNodeLayerWeight')
    foam = nd.new('ShaderNodeMath'); foam.operation = 'POWER'
    foam.inputs[1].default_value = 2.5
    links.new(facing.outputs['Facing'], foam.inputs[0])
    links.new(foam.outputs[0], combine.inputs['Z'])
    emission = nd.new('ShaderNodeEmission')
    links.new(combine.outputs[0], emission.inputs['Color'])
    pos = nd.new('ShaderNodeSeparateXYZ'); links.new(geo.outputs['Position'], pos.inputs[0])
    above = nd.new('ShaderNodeMath'); above.operation = 'GREATER_THAN'
    above.inputs[1].default_value = .012; links.new(pos.outputs['Z'], above.inputs[0])
    transparent = nd.new('ShaderNodeBsdfTransparent')
    mix = nd.new('ShaderNodeMixShader')
    links.new(above.outputs[0], mix.inputs[0])
    links.new(transparent.outputs[0], mix.inputs[1]); links.new(emission.outputs[0], mix.inputs[2])
    output = nd.new('ShaderNodeOutputMaterial'); links.new(mix.outputs[0], output.inputs[0])
    domain.data.materials.append(mat)
    camera_data = bpy.data.cameras.new('AtlasCamera')
    camera = bpy.data.objects.new('AtlasCamera', camera_data)
    scene.collection.objects.link(camera)
    target = Vector((0, 0, .185))
    camera.location = (0, -2, .62)
    camera.rotation_euler = (target - camera.location).to_track_quat('-Z', 'Y').to_euler()
    camera_data.type = 'ORTHO'; camera_data.ortho_scale = .64
    scene.camera = camera
    scene.render.engine = 'CYCLES'
    scene.cycles.device = 'CPU'; scene.cycles.samples = 8
    scene.cycles.use_denoising = False
    scene.cycles.max_bounces = 1; scene.cycles.transparent_max_bounces = 8
    scene.render.film_transparent = True
    scene.render.resolution_x = scene.render.resolution_y = TILE
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = 'OPEN_EXR'
    scene.render.image_settings.color_mode = 'RGBA'
    scene.render.image_settings.color_depth = '16'
    scene.view_settings.view_transform = 'Raw'
    scene.world = bpy.data.worlds.new('PackedBakeWorld')
    scene.world.color = (0, 0, 0)
    activate(domain)
    return domain


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', required=True)
    parser.add_argument('--repack-existing', action='store_true',
                        help='Reuse accepted cache and non-empty EXRs without resimulating or rendering')
    args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:])
    out = Path(args.output).resolve(); out.mkdir(parents=True, exist_ok=True)
    atlas = np.zeros((2048, 1024, 4), np.float32)
    atlas[:, :, :2] = .5
    empty_frames = {}
    for variant in range(4):
        folder = out / ('variant_%d' % variant); folder.mkdir(exist_ok=True)
        if not args.repack_existing:
            domain = setup(out, variant)
            bpy.ops.wm.save_as_mainfile(filepath=str(folder / 'LiquidImpulse.blend'))
            print('SPLASH_FLIP_START', variant, flush=True)
            bpy.ops.fluid.bake_data()
            bpy.ops.fluid.bake_mesh()
            bpy.ops.wm.save_as_mainfile(filepath=str(folder / 'LiquidImpulse.blend'))
        empty_frames[str(variant)] = []
        for frame in range(1, FRAMES + 1):
            # Mantaflow can display the domain's original cube when a cached
            # liquid mesh is empty. Never render that fallback into the atlas.
            mesh_cache = folder / 'cache/mesh' / ('fluid_mesh_%04d.bobj.gz' % frame)
            with gzip.open(mesh_cache, 'rb') as stream:
                vertex_count = struct.unpack('<i', stream.read(4))[0]
            if vertex_count == 0:
                empty_frames[str(variant)].append(frame)
                continue  # Neutral RG, zero coverage already in this atlas tile.
            path = folder / ('Packed_%02d.exr' % frame)
            if not args.repack_existing:
                bpy.context.scene.frame_set(frame)
                bpy.context.scene.render.filepath = str(path)
                bpy.ops.render.render(write_still=True)
            img = bpy.data.images.load(str(path), check_existing=False)
            pixels = np.empty(TILE * TILE * 4, np.float32)
            img.pixels.foreach_get(pixels)
            tile = pixels.reshape((TILE, TILE, 4))
            # EXR is premultiplied; UE samples normal/foam as straight channels.
            coverage = tile[:, :, 3:4]
            tile[:, :, :3] /= np.maximum(coverage, .0001)
            tile[:, :, :2] = np.where(coverage > .001, tile[:, :, :2], .5)
            # Two transparent border texels protect adjacent frame filtering.
            tile[:2, :, 3] = 0; tile[-2:, :, 3] = 0
            tile[:, :2, 3] = 0; tile[:, -2:, 3] = 0
            index = variant * FRAMES + frame - 1
            x, y = index % 8 * TILE, (15 - index // 8) * TILE
            atlas[y:y+TILE, x:x+TILE] = np.clip(tile, 0, 1)
            bpy.data.images.remove(img)
        print('SPLASH_VARIANT_BAKED', variant, flush=True)
    image = bpy.data.images.new('T_RiverSplashPacked', 1024, 2048, alpha=True)
    image.colorspace_settings.name = 'Non-Color'
    image.alpha_mode = 'STRAIGHT'
    image.pixels.foreach_set(atlas.ravel())
    image.file_format = 'PNG'; image.filepath_raw = str(out / 'T_RiverSplashPacked.png')
    image.save()
    (out / 'bake-manifest.json').write_text(json.dumps({
        'source': 'Original Blender Mantaflow FLIP displaced-liquid impulses',
        'variants': 4, 'frames_per_variant': FRAMES, 'fps': 50,
        'domain_resolution': 72, 'mesh_upres': 2,
        'atlas': [1024, 2048], 'grid': [8, 16], 'tile': TILE,
        'channels': {'RG': 'camera-space normal XY, encoded 0..1',
                     'B': 'aerated edge shading weight', 'A': 'coverage'},
        'world_width_cm': 64, 'waterline_pivot_v': .79,
        'provenance': 'Project-original simulations; no downloaded artwork',
        'empty_frame_policy': 'zero cached FLIP vertices => fully transparent tile; never render domain fallback',
        'empty_frames': empty_frames, 'repacked_existing_frames': args.repack_existing,
        'runtime_tested': False, 'visual_tested': False,
    }, indent=2), encoding='utf-8')
    print('SPLASH_ATLAS_SAVED', str(out / 'T_RiverSplashPacked.png'), flush=True)


if __name__ == '__main__':
    main()
