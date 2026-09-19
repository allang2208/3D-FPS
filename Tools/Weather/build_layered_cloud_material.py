"""Author project-owned volume clouds and connect the existing hills instance.

Run in UE Python. This creates/saves materials only; it never opens a map or PIE.
The engine's weather layout, volume textures, conservative-density path and
native sun/moon lighting remain in use. No Fab or engine source asset is edited.
"""
import json
import shutil
import runpy
from datetime import datetime
from pathlib import Path
import unreal as u

ROOT = Path('D:/FPS3D/FPSGAME')
DEST = '/Game/Weather/Materials'
MASTER_PATH = DEST + '/M_FPSLayeredClouds'
INSTANCE_PATH = DEST + '/MI_FPSLayeredClouds'
HILLS_PATH = '/Game/WorldGeneration/TemperateHills/Sky/MI_HillsClouds'
SOURCE_PATH = '/Engine/EngineSky/VolumetricClouds/m_SimpleVolumetricCloud'
OUT = ROOT / 'Saved/CloudMaterialUpgrade20260919'
BACKUP = OUT / ('Before-' + datetime.now().strftime('%Y%m%d-%H%M%S-%f'))
LIB = u.MaterialEditingLibrary
EAL = u.EditorAssetLibrary
TOOLS = u.AssetToolsHelpers.get_asset_tools()
REPORT = {'scope': 'Material authoring and integration; no gameplay or visual tests',
          'source': SOURCE_PATH, 'saved': [], 'backup': str(BACKUP)}
MARKER = 'FPS cloud edge and layer shaping'


def load(path):
    asset = u.load_asset(path)
    if asset is None:
        raise RuntimeError('Missing cloud dependency: ' + path)
    return asset


def backup(path):
    file = ROOT / 'Content' / (path.removeprefix('/Game/') + '.uasset')
    if file.exists():
        dest = BACKUP / file.relative_to(ROOT / 'Content')
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(file, dest)


def save(asset):
    if not EAL.save_loaded_asset(asset, False):
        raise RuntimeError('Could not save ' + asset.get_path_name())
    REPORT['saved'].append(asset.get_path_name())


def wire(source, output, target, pin):
    if not LIB.connect_material_expressions(source, output, target, pin):
        raise RuntimeError('Could not wire ' + target.get_name() + '.' + pin)


def parameter_nodes(master, name):
    return [n for n in LIB.get_material_expressions(master)
            if isinstance(n, (u.MaterialExpressionScalarParameter, u.MaterialExpressionVectorParameter,
                              u.MaterialExpressionStaticSwitchParameter))
            and str(n.get_editor_property('parameter_name')) == name]


def scalar(master, name, value, desc):
    nodes = parameter_nodes(master, name)
    node = nodes[0] if nodes else LIB.create_material_expression(master, u.MaterialExpressionScalarParameter)
    node.set_editor_property('parameter_name', name)
    node.set_editor_property('default_value', value)
    node.set_editor_property('group', 'FPS Cloud Shape')
    node.set_editor_property('desc', desc)
    return node


def instance(path, parent):
    asset = load(path) if EAL.does_asset_exist(path) else TOOLS.create_asset(
        path.rsplit('/', 1)[1], path.rsplit('/', 1)[0], u.MaterialInstanceConstant,
        u.MaterialInstanceConstantFactoryNew())
    LIB.set_material_instance_parent(asset, parent)
    return asset


OUT.mkdir(parents=True, exist_ok=True)
targets = {MASTER_PATH, INSTANCE_PATH, HILLS_PATH}
dirty = {p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
if targets.intersection(dirty):
    raise RuntimeError('Cloud target has unsaved editor changes: ' + ', '.join(targets.intersection(dirty)))
for path in targets:
    backup(path)
EAL.make_directory(DEST)
master = load(MASTER_PATH) if EAL.does_asset_exist(MASTER_PATH) else TOOLS.duplicate_asset(
    MASTER_PATH.rsplit('/', 1)[1], DEST, load(SOURCE_PATH))
if master is None:
    raise RuntimeError('Could not create project cloud master')

# Keep three different spatial bands: broad lobes, slower medium distortion,
# and restrained fine detail. Alpha values here are documented wind/strength
# controls, not color opacity. Albedo alpha is retained independently below.
vectors = {
    'Noise1_Coordinates': (3.2, 3.8, 7.2, 5.0),
    'Noise2_Coordinates': (24.0, 28.0, 32.0, -2.0),
    'Noise3_Coordinates': (80.0, 88.0, 68.0, 2.6),
    'Noise_Strength': (.70, .055, .022, 2.2),
    'Noise_Bias': (.50, .78, .52, 0.0),
    'Noise3_MultChannel': (0.0, 0.0, 1.0, .18),
    'Layout_CloudType': (1.0, 1.0, 1.0, 2.0),
    'Layout_CloudPerTypeScale': (1.0, 1.0, 1.0, 1.0),
    'Multiscatter_Controls': (.72, .20, .25, 1.0),
    'Phase_Controls': (.55, -.12, .28, 1.0),
    'Layout_WindControls': (1.0, .32, .12, 1 / 3),
    'Storm_LightningColor': (0.0, 0.0, 0.0, 0.0),
}
for name, value in vectors.items():
    for node in parameter_nodes(master, name):
        node.set_editor_property('default_value', u.LinearColor(*value))
for name, rgb in [('Cloud_AlbedoColor', (.96, .98, 1.0)), ('Storm_AlbedoColor', (.76, .79, .82))]:
    for node in parameter_nodes(master, name):
        original = node.get_editor_property('default_value')
        node.set_editor_property('default_value', u.LinearColor(*rgb, original.a))
for node in parameter_nodes(master, 'UseNoise3'):
    node.set_editor_property('default_value', True)

advanced = [n for n in LIB.get_material_expressions(master)
            if isinstance(n, u.MaterialExpressionVolumetricAdvancedMaterialOutput)][0]
advanced.set_editor_property('multi_scattering_approximation_octave_count', 1)
advanced.set_editor_property('ground_contribution', True)
advanced.set_editor_property('per_sample_phase_evaluation', False)
# Retain ray-marched self shadowing; a shadow-map-only mode would depend on each
# map's atmosphere light having cloud shadow maps enabled.
advanced.set_editor_property('ray_march_volume_shadow', True)

shape_nodes = [n for n in LIB.get_material_expressions(master)
               if isinstance(n, u.MaterialExpressionCustom) and n.get_editor_property('desc') == MARKER]
if shape_nodes:
    shape = shape_nodes[0]
    source = LIB.get_inputs_for_material_expression(master, shape)[0]
    source_output = LIB.get_input_node_output_name_for_material_expression(shape, source)
else:
    # In the volume domain Extinction is RGB SubsurfaceColor, not Opacity.
    source = LIB.get_material_property_input_node(master, u.MaterialProperty.MP_SUBSURFACE_COLOR)
    source_output = LIB.get_material_property_input_node_output_name(master, u.MaterialProperty.MP_SUBSURFACE_COLOR)
    shape = LIB.create_material_expression(master, u.MaterialExpressionCustom)
if source is None:
    raise RuntimeError('Cloud extinction source is not connected')

parameters = {
    'Density': scalar(master, 'Cloud_GlobalDensity', .008, 'Extinction multiplier; never a coverage bias.'),
    'Weather': scalar(master, 'FPS_WeatherBlend', 0.0, '0 clear to 1 storm, owned by FPSWeatherManager.'),
    'EdgeWidth': scalar(master, 'FPS_EdgeFeather', .18, 'Density interval with gradual edge extinction.'),
    'EdgeSoftness': scalar(master, 'FPS_EdgeSoftness', .80, 'Blend from source extinction to feathered edges.'),
    'BaseFade': scalar(master, 'FPS_BaseFade', .08, 'Normalized layer-base fade; retains the height-profile texture.'),
    'TopFade': scalar(master, 'FPS_TopFade', .14, 'Normalized layer-top fade.'),
}
shape.set_editor_property('desc', MARKER)
shape.set_editor_property('output_type', u.CustomMaterialOutputType.CMOT_FLOAT3)
shape.set_editor_property('code', '''
// Only remove matter from the original field: the original conservative
// density remains valid, and empty parts of the sky stay empty.
float3 extinction = max((float3)Extinction, 0.0);
float field = dot(extinction, float3(0.333333, 0.333333, 0.333333)) / max(Density, 0.0001);
float weather = saturate(Weather);
float width = max(EdgeWidth * lerp(1.0, 0.80, weather), 0.001);
float feather = lerp(1.0, smoothstep(0.0, width, field), saturate(EdgeSoftness));
float h = saturate(Height);
float bottom = smoothstep(0.0, max(BaseFade, 0.001), h);
float top = 1.0 - smoothstep(1.0 - max(TopFade, 0.001), 1.0, h);
return extinction * feather * bottom * top;
''')
if not shape_nodes:
    pins = []
    for name in ['Extinction', 'Height', *parameters.keys()]:
        pin = u.CustomInput()
        pin.set_editor_property('input_name', name)
        pins.append(pin)
    shape.set_editor_property('inputs', pins)
wire(source, source_output, shape, 'Extinction')
attributes = LIB.create_material_expression(master, u.MaterialExpressionCloudSampleAttribute) if not shape_nodes else None
if attributes is None:
    attributes = next(n for n in LIB.get_material_expressions(master) if isinstance(n, u.MaterialExpressionCloudSampleAttribute))
wire(attributes, 'NormAltitudeInLayer', shape, 'Height')
for name, node in parameters.items():
    wire(node, '', shape, name)
if not LIB.connect_material_property(shape, '', u.MaterialProperty.MP_SUBSURFACE_COLOR):
    raise RuntimeError('Could not connect shaped cloud extinction')

# The weather controller supplies the only flash envelope. Rebuilding this
# graph retains lightning integration, with zero emission between strikes.
lightning = runpy.run_path(str(ROOT / 'Tools/Weather/build_storm_lightning_materials.py'))
lightning['connect_cloud_lightning'](master, shape, parameters['Density'])
motion = runpy.run_path(str(ROOT / 'Tools/Weather/build_cloud_motion.py'))
motion['connect_cloud_motion'](master)
density_repair = runpy.run_path(str(ROOT / 'Tools/Weather/repair_layered_cloud_density.py'))
density_repair['repair_cloud_density'](master)
LIB.layout_material_expressions(master)
LIB.recompile_material(master)

shared = instance(INSTANCE_PATH, master)
# The engine master is a template with black placeholder textures. The working
# layout, height profile, mask and volume noise are authored on its instance.
texture_bindings = runpy.run_path(str(ROOT / 'Tools/Weather/repair_layered_cloud_textures.py'))
cloud_textures = texture_bindings['bind_cloud_textures'](shared)
for name, value in {'Cloud_GlobalCoverage': -.18, 'Cloud_GlobalDensity': .008,
                    'StormClouds': 0.0, 'FPS_WeatherBlend': 0.0}.items():
    LIB.set_material_instance_scalar_parameter_value(shared, name, value)
LIB.set_material_instance_static_switch_parameter_value(shared, 'UseNoise3', True)
LIB.update_material_instance(shared)

# Existing biome assets already point here. Reparent in place so old maps and
# the native async loader receive the new graph without regenerating a level.
hills = instance(HILLS_PATH, shared)
LIB.set_material_instance_static_switch_parameter_value(hills, 'UseNoise3', True)
LIB.update_material_instance(hills)
# Commandlet shutdown otherwise cancels queued shader jobs immediately after
# saving. Finish the asset build without entering a level or rendering a frame.
u.SystemLibrary.execute_console_command(None, 'Editor.AsyncAssetCompilationFinishAll')
for asset in [master, shared, hills]:
    save(asset)
REPORT.update(master=MASTER_PATH, instance=INSTANCE_PATH, hills=HILLS_PATH,
              cloud_textures=cloud_textures,
              vectors=vectors, extinction_source=source.get_name(),
              scattering_octaves=1, ground_contribution=True,
              authored_assets='Project-owned UE graph using engine textures; no Fab assets imported')
(OUT / 'authoring.json').write_text(json.dumps(REPORT, indent=2), encoding='utf-8')
u.log('FPS_LAYERED_CLOUDS_AUTHORED ' + ', '.join(REPORT['saved']))
