"""Write the owning Blueprint settings, not only transient component values."""
import json
import unreal as u

# User temporarily hid the lower cloud sea on 2026-09-28. Keep its authored
# material/shape settings for later work without restoring it on layout rebuild.
CLOUD_SEA_VISIBLE=False

def apply(sky,cloud_material):
    # PWL construction/refresh writes this struct back onto VolumetricCloud.
    # Its previous false/3 km values erased the component-only authoring.
    key='volumetric Cloud Settings'
    values=json.loads(u.ToolsetLibrary.get_object_properties(sky,[key]))
    settings=values[key]
    settings.update({'add Volumetric Cloud':CLOUD_SEA_VISIBLE,
        'coud Material':{'refPath':cloud_material.get_path_name()},
        'layer Bottom Altitude':.62,'layer Height':.70,
        'tracing Start Max Distance':160.,'tracing Max Distance':160.,
        'view Sample Count Scale':3.,'reflection View Sample Count Scale':.2,
        'shadow View Sample Count Scale':.5,'shadow Tracing Distance':12.,
        'planet Radius':6360.})
    if not u.ToolsetLibrary.set_object_properties(sky,json.dumps(values)):
        raise RuntimeError('Cannot save cloud settings on the day/night actor')
    sky.tags=list(dict.fromkeys(list(sky.tags)+[u.Name('GodSpace.CloudSea')]))
    atmos=sky.get_components_by_class(u.SkyAtmosphereComponent)[0]
    atmos.set_editor_property('transform_mode',u.SkyAtmosphereTransformMode.PLANET_TOP_AT_COMPONENT_TRANSFORM)
    # This component is attached below the rotating sun root. Its sea-level
    # planet center must not orbit with the day/night light's rotation.
    atmos.set_absolute(True,True,True)
    atmos.set_world_location(u.Vector(-2400,-1300,-150000),False,True)
    atmos.set_world_rotation(u.Rotator(pitch=0,yaw=0,roll=0),False,True)
    cloud=sky.get_components_by_class(u.VolumetricCloudComponent)[0]
    cloud.set_material(cloud_material);cloud.set_visibility(CLOUD_SEA_VISIBLE)
    # Weather writes SetVisibility(true); hidden-in-game must remain independent.
    cloud.set_hidden_in_game(not CLOUD_SEA_VISIBLE)
    cloud.set_layer_bottom_altitude(.62);cloud.set_layer_height(.70)
    # 96*3*.7/15 ~= 13 samples through a 700 m layer, versus ~3 at scale .7.
    # This is local to the hub. Keep project-wide reconstruction and caps intact.
    cloud.set_view_sample_count_scale(3.);cloud.set_shadow_view_sample_count_scale(.5)
    cloud.set_editor_property('reflection_view_sample_count_scale_value',.2)
    cloud.set_editor_property('shadow_reflection_view_sample_count_scale_value',.15)
    cloud.set_editor_property('tracing_max_distance',160.)
    cloud.set_editor_property('tracing_start_max_distance',160.)
    return settings
