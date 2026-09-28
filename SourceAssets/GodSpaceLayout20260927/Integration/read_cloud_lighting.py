"""Read current lighting inputs for the reported orange cloud sea; no edits."""
import json
from pathlib import Path
import unreal as u

ROOT = Path(__file__).parent

def values(obj, names):
    result = {}
    for name in names:
        try:
            value = obj.get_editor_property(name)
            result[name] = value if isinstance(value, (str, bool, float, int)) else str(value)
        except Exception:
            pass
    return result

common = ['visible', 'intensity', 'light_color', 'use_temperature', 'temperature',
          'indirect_lighting_intensity', 'volumetric_scattering_intensity']
groups = [
    (u.DirectionalLightComponent, common + ['atmosphere_sun_light', 'atmosphere_sun_light_index',
        'cloud_scattered_luminance_scale', 'per_pixel_atmosphere_transmittance',
        'atmosphere_sun_disk_color_scale', 'cast_cloud_shadows']),
    (u.SkyLightComponent, common + ['source_type', 'cubemap', 'source_cubemap_angle',
        'real_time_capture', 'lower_hemisphere_color', 'lower_hemisphere_is_black',
        'cloud_ambient_occlusion', 'cloud_ambient_occlusion_strength']),
    (u.SkyAtmosphereComponent, ['visible', 'transform_mode', 'bottom_radius', 'atmosphere_height',
        'ground_albedo', 'multi_scattering_factor', 'rayleigh_scattering', 'rayleigh_scattering_scale',
        'mie_scattering', 'mie_scattering_scale', 'mie_absorption', 'mie_absorption_scale',
        'absorption', 'absorption_scale', 'sky_luminance_factor', 'aerial_perspective_view_distance_scale']),
    (u.VolumetricCloudComponent, ['visible', 'material', 'ground_albedo', 'layer_bottom_altitude',
        'layer_height', 'sky_light_cloud_bottom_occlusion', 'use_per_sample_atmospheric_light_transmittance']),
    (u.ExponentialHeightFogComponent, ['visible', 'fog_density', 'fog_height_falloff',
        'fog_inscattering_luminance', 'directional_inscattering_luminance', 'volumetric_fog_albedo',
        'volumetric_fog_emissive', 'volumetric_fog_extinction_scale', 'volumetric_fog']),
]
editor = u.get_editor_subsystem(u.UnrealEditorSubsystem)
report = {}
report['cloud_cvars'] = {}
for cvar in ['r.VolumetricCloud.EnableDistantSkyLightSampling',
             'r.VolumetricCloud.EnableAtmosphericLightsSampling',
             'r.SkyAtmosphere.DistantSkyLightLUT']:
    try:
        report['cloud_cvars'][cvar] = u.SystemLibrary.get_console_variable_int_value(cvar)
    except Exception:
        pass
for key, world in [('editor', editor.get_editor_world()), ('game', editor.get_game_world())]:
    if not world:
        continue
    rows = []
    for actor in u.GameplayStatics.get_all_actors_of_class(world, u.Actor):
        components = []
        for cls, names in groups:
            for component in actor.get_components_by_class(cls):
                row = {'name': component.get_path_name(), 'class': cls.__name__,
                    'location': str(component.get_world_location()),
                    'rotation': str(component.get_world_rotation()), **values(component, names)}
                if cls == u.VolumetricCloudComponent:
                    mat = component.get_editor_property('material')
                    if mat:
                        row['material_values'] = values(mat, ['parent', 'scalar_parameter_values', 'vector_parameter_values'])
                components.append(row)
        if components:
            row = {'actor': actor.get_path_name(), 'components': components}
            if 'DayNight' in actor.get_class().get_name():
                row['clock'] = values(actor, ['sun_height', 'SunHeight'])
            rows.append(row)
    report[key] = {'world': world.get_path_name(), 'actors': rows}
path = ROOT / 'Receipts/cloud-lighting-inputs.json'
path.write_text(json.dumps(report, indent=2), encoding='utf8')
print('CLOUD_LIGHTING_INPUTS ' + str(path))
