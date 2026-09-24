"""Author and bake original fluid source assets; no preview renders or tests.

blender --background --threads 4 --python this.py -- --kind fire --output ABS_PATH
Units are meters in Blender. VDB keeps its original grid transform; UE actors
apply a meter-to-centimeter scale. Alembic is converted at import instead.
"""
import argparse
import json
import sys
from pathlib import Path

import bpy


def cube(name, location, dimensions):
    bpy.ops.mesh.primitive_cube_add(size=1, location=location)
    obj = bpy.context.object
    obj.name = name
    obj.dimensions = dimensions
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    return obj


def activate(obj):
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--kind', choices=['fire', 'liquid'], required=True)
    parser.add_argument('--output', required=True)
    parser.add_argument('--resolution', type=int, default=64)
    parser.add_argument('--frames', type=int, default=72)
    args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:])
    out = Path(args.output).resolve()
    out.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.unit_settings.system = 'METRIC'
    scene.unit_settings.scale_length = 1.0
    scene.render.fps = 24
    scene.frame_start, scene.frame_end = 1, args.frames
    fire = args.kind == 'fire'
    domain = cube('Domain_Fire' if fire else 'Domain_Liquid',
                  (0, 0, 1.5) if fire else (0, 0, 0.8),
                  (2, 2, 3) if fire else (2, 2, 1.6))
    mod = domain.modifiers.new('Mantaflow', 'FLUID')
    mod.fluid_type = 'DOMAIN'
    bpy.context.view_layer.update()
    settings = mod.domain_settings
    settings.domain_type = 'GAS' if fire else 'LIQUID'
    settings.resolution_max = args.resolution
    settings.cache_directory = str(out / 'cache')
    settings.cache_frame_start, settings.cache_frame_end = 1, args.frames
    settings.cache_type = 'MODULAR'
    settings.cache_data_format = 'OPENVDB' if fire else 'UNI'
    settings.cache_resumable = False
    settings.timesteps_max = 4
    settings.timesteps_min = 1
    if fire:
        settings.use_noise = False
        settings.use_adaptive_domain = False
        settings.vorticity = 0.65
        settings.burning_rate = 0.8
        settings.flame_smoke = 0.7
        settings.flame_vorticity = 0.65
        settings.use_dissolve_smoke = True
        settings.dissolve_speed = 45
        settings.use_collision_border_top = False
        bpy.ops.mesh.primitive_uv_sphere_add(segments=20, ring_count=12, radius=1,
                                           location=(0, 0, 0.22))
        source = bpy.context.object
        source.name = 'Original_Fire_Source'
        source.scale = (0.22, 0.19, 0.14)
        bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    else:
        settings.use_mesh = True
        settings.mesh_scale = 2
        settings.mesh_particle_radius = 1.4
        settings.mesh_smoothen_pos = 2
        settings.mesh_smoothen_neg = 2
        settings.flip_ratio = 0.95
        bpy.ops.mesh.primitive_uv_sphere_add(segments=20, ring_count=12, radius=0.27,
                                           location=(-0.25, 0, 1.15))
        source = bpy.context.object
        source.name = 'Original_Liquid_Drop'
    flowmod = source.modifiers.new('Fluid_Source', 'FLUID')
    flowmod.fluid_type = 'FLOW'
    bpy.context.view_layer.update()
    flow = flowmod.flow_settings
    flow.flow_type = 'BOTH' if fire else 'LIQUID'
    flow.flow_behavior = 'INFLOW' if fire else 'GEOMETRY'
    flow.use_initial_velocity = True
    flow.velocity_coord = (0.12, 0.0, 0.45) if fire else (0.6, 0, -0.2)
    if fire:
        flow.density = 0.8
        flow.fuel_amount = 1.1
        flow.temperature = 1.2
    source.hide_render = True
    activate(domain)
    blend_path = out / ('Mantaflow_' + args.kind + '.blend')
    bpy.ops.wm.save_as_mainfile(filepath=str(blend_path))
    print('FLUID_BAKE_START', args.kind, flush=True)
    bpy.ops.fluid.bake_data()
    exported = []
    grids = []
    if fire:
        exported = sorted((out / 'cache' / 'data').glob('*.vdb'))
        if not exported:
            raise RuntimeError('Mantaflow did not produce OpenVDB files')
        volume = bpy.data.volumes.new('Baked_Grid_Layout')
        volume.filepath = str(exported[min(23, len(exported)-1)])
        volume.grids.load()
        grids = [{'name': grid.name, 'data_type': grid.data_type,
                  'channels': grid.channels} for grid in volume.grids]
        bpy.data.volumes.remove(volume)
    else:
        bpy.ops.fluid.bake_mesh()
        scene.frame_set(1)
        activate(domain)
        abc = out / 'LiquidDrop.abc'
        bpy.ops.wm.alembic_export(filepath=str(abc), start=1, end=args.frames,
                                 selected=True, flatten=True, as_background_job=False,
                                 uvs=True, normals=True)
        exported = [abc]
    bpy.ops.wm.save_as_mainfile(filepath=str(blend_path))
    manifest = {'kind': args.kind, 'source': str(blend_path), 'fps': 24,
                'frames': args.frames, 'resolution': args.resolution,
                'units': 'meters', 'grids': grids,
                'files': [str(p) for p in exported],
                'provenance': 'Original procedural Mantaflow setup authored for FPSGAME',
                'status': 'baked_not_runtime_tested', 'seamless_loop': False}
    (out / 'bake-manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    print('FLUID_BAKE_SAVED', str(out / 'bake-manifest.json'), flush=True)


if __name__ == '__main__':
    main()
