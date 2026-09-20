"""Author the DayNight HDR sky adapter and connect the hills biome asset.

Run using the updated FPSGAMEEditor module. No level, gameplay or preview is run.
Source PWL assets are referenced in place and never edited.
"""
import json
import shutil
import runpy
from datetime import datetime
from pathlib import Path
import unreal as u

ROOT = Path('D:/FPS3D/FPSGAME')
BASE = '/Game/WorldGeneration/TemperateHills'
DEST = BASE + '/Sky'
OUT = ROOT / 'Saved/HillsHDRSky20260915'
OUT.mkdir(parents=True, exist_ok=True)
BACKUP = OUT / ('BeforeAuthoring-' + datetime.now().strftime('%Y%m%d-%H%M%S-%f'))
EAL = u.EditorAssetLibrary
LIB = u.MaterialEditingLibrary
TOOLS = u.AssetToolsHelpers.get_asset_tools()
REPORT = {'scope': 'Sky asset authoring and integration; not gameplay or visual testing',
          'sources': [], 'saved': []}
EAL.make_directory(DEST)


def load(path):
    obj = u.load_asset(path)
    if obj is None:
        raise RuntimeError('Missing sky source: ' + path)
    return obj


def backup(path):
    source = ROOT / 'Content' / (path.split('.')[0].removeprefix('/Game/') + '.uasset')
    if source.exists():
        target = BACKUP / source.relative_to(ROOT / 'Content')
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)


def save(obj):
    if not EAL.save_loaded_asset(obj, False):
        raise RuntimeError('Unable to save ' + obj.get_path_name())
    REPORT['saved'].append(obj.get_path_name())
    return obj


def node(mat, cls):
    return LIB.create_material_expression(mat, cls)


def wire(source, target, pin):
    if not LIB.connect_material_expressions(source, '', target, pin):
        raise RuntimeError('Unable to connect sky material pin ' + pin)


def scalar(mat, name, value):
    expr = node(mat, u.MaterialExpressionScalarParameter)
    expr.set_editor_property('parameter_name', name)
    expr.set_editor_property('default_value', value)
    return expr


def custom(mat, code, inputs):
    expr = node(mat, u.MaterialExpressionCustom)
    expr.set_editor_property('code', code)
    expr.set_editor_property('output_type', u.CustomMaterialOutputType.CMOT_FLOAT3)
    pins = []
    for name in inputs:
        pin = u.CustomInput()
        pin.set_editor_property('input_name', name)
        pins.append(pin)
    expr.set_editor_property('inputs', pins)
    for name, source in inputs.items():
        wire(source, expr, name)
    return expr


source_master = '/Game/PWL_Light_Manager/Shader/M_Cubemap_Sky_Material'
master_path = DEST + '/M_HillsDayNightSky'
backup(master_path)
master = (load(master_path) if EAL.does_asset_exist(master_path)
          else EAL.duplicate_asset(source_master, master_path))
if master is None:
    raise RuntimeError('Unable to create hills HDR sky master')
# Keep the source sky's unlit/opaque rendering, replacing its global MPC ownership
# with a world-local material instance. The source graph remains untouched.
LIB.delete_all_material_expressions(master)
master.set_editor_property('shading_model', u.MaterialShadingModel.MSM_UNLIT)
master.set_editor_property('is_sky', True)
master.set_editor_property('two_sided', True)
master.set_editor_property('blend_mode', u.BlendMode.BLEND_OPAQUE)
view = node(master, u.MaterialExpressionCameraVectorWS)
rotation = scalar(master, 'SkyRotationDegrees', 0.0)
direction = custom(master, '''float3 d = normalize(-View);
float s, c; sincos(radians(Rotation), s, c);
return float3(c*d.x-s*d.y, s*d.x+c*d.y, d.z);''',
                   dict(View=view, Rotation=rotation))

samples = {}
phases = [('Dawn', 'MI_Sky_Sunrise'), ('Day', 'MI_Sky_Sunshine'),
          ('Dusk', 'MI_Sky_Sunset'), ('Night', 'MI_HDR_Night_Sky')]
for phase, name in phases:
    source = load('/Game/PWL_Light_Manager/Shader/' + name)
    cube = LIB.get_material_instance_texture_parameter_value(source, 'Sky Cubemap')
    if not isinstance(cube, u.TextureCube):
        raise RuntimeError('Source material has no HDR cubemap: ' + name)
    sample = node(master, u.MaterialExpressionTextureSampleParameterCube)
    sample.set_editor_property('parameter_name', phase + 'Cubemap')
    sample.set_editor_property('texture', cube)
    sample.set_editor_property('sampler_type', u.MaterialSamplerType.SAMPLERTYPE_COLOR
                               if cube.get_editor_property('srgb')
                               else u.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR)
    wire(direction, sample, 'UVs')
    samples[phase] = sample
    REPORT['sources'].append({'phase': phase, 'material': source.get_path_name(),
                              'cubemap': cube.get_path_name(),
                              'source_intensity': LIB.get_material_instance_scalar_parameter_value(source, 'Sky Intensity')})

weights = node(master, u.MaterialExpressionVectorParameter)
weights.set_editor_property('parameter_name', 'SkyPhaseWeights')
weights.set_editor_property('default_value', u.LinearColor(0, 1, 0, 0))
# Vector parameters expose RGB on their default pin. Derive the night weight from
# the other three so midnight does not depend on an implicit alpha connection.
color = custom(master, '''float nightWeight = saturate(1-dot(Weights.rgb,float3(1,1,1)));
// The source sunrise/night HDRs exceed 65504 in a few pixels. TC_HDR stores
// half floats, so those samples can be infinite. Multiplying an inactive sky
// by zero still produces NaN and contaminates the visible daytime sky.
// Select active phases explicitly and bound samples before the weighted sum.
float3 hdr = float3(0,0,0);
if (Weights.r > 0) hdr += clamp(Dawn.rgb,0.0,65504.0)*Weights.r;
if (Weights.g > 0) hdr += clamp(Day.rgb,0.0,65504.0)*Weights.g;
if (Weights.b > 0) hdr += clamp(Dusk.rgb,0.0,65504.0)*Weights.b;
if (nightWeight > 0) hdr += clamp(Night.rgb,0.0,65504.0)*nightWeight;
hdr *= SourceIntensity * exp2(Exposure);
// PWL Sunshine is a pink horizon photograph, not a complete daytime sky.
// Retain its tint while the existing atmosphere provides the daytime base.
float3 fallback = lerp(float3(.10,.135,.17),float3(.022,.045,.075),saturate(-View.z));
fallback *= lerp(.025,.8,Daylight);
float3 atmosphere = max(Atmosphere.rgb,fallback);
float3 clearSky = lerp(hdr,atmosphere,saturate(Weights.g)*DayAtmosphereWeight);
// IsSky opaque materials replace the atmosphere pass. ViewLuminance only
// includes sky scattering: explicitly add the EXISTING light's disk, whose
// direction, angular size, color and weather attenuation remain light-owned.
return lerp(clearSky,atmosphere,smoothstep(0,.65,Weather)) + LightDisk.rgb;''',
               dict(**samples, Weights=weights, View=view,
                    SourceIntensity=scalar(master, 'HDRSourceIntensity', 1.5),
                    Exposure=scalar(master, 'SkyExposureCompensation', -4.5),
                    Weather=scalar(master, 'WeatherSkyBlend', 0.0),
                    Daylight=scalar(master, 'WeatherSkyDaylight', 1.0),
                    DayAtmosphereWeight=scalar(master, 'DayAtmosphereWeight', .8),
                    LightDisk=node(master, u.MaterialExpressionSkyAtmosphereLightDiskLuminance),
                    Atmosphere=node(master, u.MaterialExpressionSkyAtmosphereViewLuminance)))
if not LIB.connect_material_property(color, '', u.MaterialProperty.MP_EMISSIVE_COLOR):
    raise RuntimeError('Unable to connect sky emissive output')
lightning = runpy.run_path(str(ROOT / 'Tools/Weather/build_storm_lightning_materials.py'))
lightning['connect_sky_lightning'](master)
LIB.layout_material_expressions(master)
LIB.recompile_material(master)
save(master)

mi_path = DEST + '/MI_HillsDayNightSky'
backup(mi_path)
mi = (load(mi_path) if EAL.does_asset_exist(mi_path)
      else TOOLS.create_asset('MI_HillsDayNightSky', DEST, u.MaterialInstanceConstant,
                              u.MaterialInstanceConstantFactoryNew()))
if mi is None:
    raise RuntimeError('Unable to create hills sky material instance')
LIB.set_material_instance_parent(mi, master)
save(mi)

config_path = BASE + '/DA_TemperateHillsStreaming'
backup(config_path)
assets = load(config_path)
mesh = load('/Engine/EngineSky/SM_SkySphere')
assets.set_editor_property('day_night_sky_material', mi)
assets.set_editor_property('day_night_sky_mesh', mesh)
assets.set_editor_property('sky_exposure_compensation', -4.5)
assets.set_editor_property('sky_rotation_degrees', 0.0)
assets.set_editor_property('sky_turns_per_game_day', 1.08)
save(assets)
REPORT['configuration'] = config_path
REPORT['master_source'] = source_master
REPORT['sun_source'] = 'SkyAtmosphereLightDiskLuminance, existing atmosphere light index 0'
REPORT['day_atmosphere_weight'] = .8
REPORT['clouds'] = 'Existing volumetric cloud layer remains visible in clear weather'
REPORT['mesh'] = mesh.get_path_name()
REPORT['exposure'] = {'source_sunshine_ev100': 5.5, 'source_global_intensity': 1.5,
                      'hills_ev100': 1.0, 'compensation_stops': -4.5}
REPORT['phase_hours'] = {'night_to_dawn': [4.5, 6], 'dawn_to_day': [6, 8.5],
                          'day_to_dusk': [16.5, 18], 'dusk_to_night': [18, 19.5]}
(OUT / 'authoring.json').write_text(json.dumps(REPORT, ensure_ascii=False, indent=2), encoding='utf-8')
u.log('HILLS_DAYNIGHT_SKY_AUTHORED: ' + ', '.join(REPORT['saved']))
