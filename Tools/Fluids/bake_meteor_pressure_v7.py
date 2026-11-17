"""Bake an impulsive hemispherical meteor blast, with a fixed tight atlas frame.

Production export only. No camera render, gameplay or acceptance run.
"""
import argparse
import json
import math
import sys
from pathlib import Path
import bpy
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'SourceAssets/MeteorImpactReferenceV7_20261114/Blast'
sys.path.insert(0, str(ROOT / 'Tools/Fluids'))
from bake_muzzle_smoke import activate, resample


def setup():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.render.fps = 60
    scene.frame_start, scene.frame_end = 1, 96
    scene.unit_settings.system = 'METRIC'
    scene.gravity = (0, 0, -3)
    bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 0, 2.8))
    domain = bpy.context.object
    domain.name = 'MeteorPressureDomainV7'
    domain.dimensions = (7.2, 7.2, 5.6)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    mod = domain.modifiers.new('Mantaflow', 'FLUID')
    mod.fluid_type = 'DOMAIN'
    bpy.context.view_layer.update()
    ds = mod.domain_settings
    ds.domain_type = 'GAS'
    ds.resolution_max = 128
    ds.cache_directory = str(OUT / 'cache')
    ds.cache_frame_start, ds.cache_frame_end = 1, 96
    ds.cache_type = 'MODULAR'
    ds.cache_data_format = 'OPENVDB'
    ds.cache_resumable = False
    ds.use_adaptive_domain = False
    ds.use_noise = False
    ds.time_scale = 1
    ds.vorticity = 2.2
    ds.flame_vorticity = 1.8
    ds.burning_rate = 1.65
    ds.flame_smoke = .85
    ds.timesteps_max = 6
    ds.use_dissolve_smoke = True
    ds.dissolve_speed = 65
    for side in ('front', 'back', 'left', 'right', 'top'):
        setattr(ds, 'use_collision_border_' + side, False)
    ds.use_collision_border_bottom = True
    # A substantial initial connected volume, followed by short radial pulses.
    # All sources switch off after 50 ms; this is not a sustained flame plume.
    sources = [((0, 0, .40), (.66, .61, .38), (0, 0, 4.0), 2.4)]
    for i in range(9):
        angle = i * math.tau / 9 + .17
        radius = .49 + .08 * math.sin(i * 2.4)
        speed = 5.4 + .9 * math.sin(i * 1.71)
        sources.append(((math.cos(angle)*radius, math.sin(angle)*radius, .30+.08*(i % 3)),
                        (.31+.025*(i % 3), .31, .25),
                        (math.cos(angle)*speed, math.sin(angle)*speed, 2.1+.7*(i % 3)), 1.9))
    for i, (pos, scale, velocity, fuel) in enumerate(sources):
        bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=3, radius=1, location=pos)
        obj = bpy.context.object
        obj.name = f'PressureFuelV7_{i:02}'
        obj.scale = scale
        bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
        mod = obj.modifiers.new('Fuel', 'FLUID')
        mod.fluid_type = 'FLOW'
        bpy.context.view_layer.update()
        flow = mod.flow_settings
        flow.flow_type = 'BOTH'
        flow.flow_behavior = 'INFLOW'
        flow.density = .9
        flow.temperature = 1.7
        flow.fuel_amount = fuel
        flow.use_initial_velocity = True
        flow.velocity_coord = velocity
        flow.use_inflow = True
        flow.keyframe_insert(data_path='use_inflow', frame=1)
        flow.keyframe_insert(data_path='use_inflow', frame=3)
        flow.use_inflow = False
        flow.keyframe_insert(data_path='use_inflow', frame=4)
        obj.hide_render = True
    scene.frame_set(1)
    activate(domain)
    return domain


def export(domain):
    projected = []
    for frame in range(1, 97):
        bpy.context.scene.frame_set(frame)
        ds = domain.evaluated_get(bpy.context.evaluated_depsgraph_get()).modifiers['Mantaflow'].domain_settings
        sx, sy, sz = ds.domain_resolution
        fields = []
        for key in ('flame_grid', 'density_grid', 'temperature_grid'):
            field = np.asarray(getattr(ds, key)[:], dtype=np.float32)
            if field.size != sx*sy*sz or not field.size:
                raise RuntimeError(f'Missing production field {key} / {frame}')
            fields.append(field.reshape((sz, sy, sx)))
        fire, smoke, temp = fields
        projected.append(np.stack((fire.sum(1)*7.2/sy,
            (np.maximum(temp,0)*fire).sum(1)/np.maximum(fire.sum(1),.001),
            smoke.sum(1)*7.2/sy), axis=-1))
    raw = np.stack(projected)
    np.savez_compressed(OUT / 'pressure-fields.npz', fields=raw)
    # One fixed crop for the whole event: no per-frame resize or brightness gain.
    activity = np.maximum(raw[:64,:,:,0].max(0), raw[:,:,:,2].max(0)*.25)
    occupied = np.argwhere(activity > max(float(activity.max())*.012,.001))
    if not len(occupied):
        raise RuntimeError('Empty baked combustion; do not import a fallback')
    z0,x0 = occupied.min(0); z1,x1 = occupied.max(0)+1
    z0=max(0,int(z0)-2); z1=min(sz,int(z1)+3)
    half=max(abs(int(x0)-sx/2), abs(int(x1)-sx/2))+3
    x0=max(0,int(sx/2-half)); x1=min(sx,int(sx/2+half))
    raw = raw[:,z0:z1,x0:x1,:]
    scale = np.maximum(np.percentile(raw,99.6,axis=(0,1,2)),.001)
    normalized = np.clip(raw/scale,0,1)
    atlas=np.zeros((2048,2048,4),np.float32)
    x=(np.arange(248)+.5)/248*raw.shape[2]-.5
    z=(np.arange(248)+.5)/248*raw.shape[1]-.5
    t=np.linspace(0,95,64)
    fire_frames=[]
    for i, source in enumerate(t):
        lo=int(source); weight=source-lo
        field=normalized[lo]*(1-weight)+normalized[min(lo+1,95)]*weight
        tile=np.zeros((256,256,4),np.float32)
        values=np.stack([resample(field[:,:,k],x,z) for k in range(3)],axis=-1)
        coord=(np.arange(248)+.5)/248
        margin=np.clip(np.minimum(coord,1-coord)/.025,0,1)
        values*=margin[:,None,None]*margin[None,:,None]
        if np.any(values[:,:,0]>.08):
            fire_frames.append(i)
        gz,gx=np.gradient(values[:,:,2])
        tile[4:-4,4:-4,:3]=values
        tile[4:-4,4:-4,3]=np.clip(.66+gz*3.8-gx*2.4,.20,.95)
        cx,cy=i%8*256,(7-i//8)*256
        atlas[cy:cy+256,cx:cx+256]=tile
    image=bpy.data.images.new('T_MeteorPressureFieldsV7',2048,2048,alpha=True)
    image.colorspace_settings.name='Non-Color'
    image.alpha_mode='CHANNEL_PACKED'
    image.pixels.foreach_set(atlas.ravel())
    image.file_format='PNG'
    image.filepath_raw=str(OUT/'T_MeteorPressureFieldsV7.png')
    image.save()
    manifest=dict(texture='T_MeteorPressureFieldsV7',source='Original Mantaflow pressure impulse',
        atlas=[2048,2048],grid=[8,8],frames=64,tile=256,gutter=4,
        source_fps=60,source_frames=[1,96],normalization=scale.tolist(),
        domain_metres=[7.2,7.2,5.6],resolution=128,fixed_crop=[x0,z0,x1,z1],
        visible_width_metres=(x1-x0)*7.2/sx,visible_height_metres=(z1-z0)*5.6/sz,
        channels={'R':'flame depth','G':'heat','B':'smoke depth','A':'smoke shading, not alpha'},
        playback_windows={'fire':[min(fire_frames),max(fire_frames)+.65], 'smoke':[0,63]},
        reference_pixels_used=False,rendered=False,runtime_tested=False)
    (OUT/'atlas-manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf8')
    print('METEOR_V7_ATLAS_SAVED '+json.dumps(manifest),flush=True)


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--export-only',action='store_true')
    args=parser.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
    OUT.mkdir(parents=True,exist_ok=True)
    if args.export_only:
        bpy.ops.wm.open_mainfile(filepath=str(OUT/'MeteorPressureV7.blend'))
        domain=bpy.data.objects['MeteorPressureDomainV7']
    else:
        domain=setup()
        bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'MeteorPressureV7.blend'))
        print('METEOR_V7_BAKE_START',flush=True)
        bpy.ops.fluid.bake_data()
        bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'MeteorPressureV7.blend'))
    export(domain)


if __name__=='__main__':
    main()
