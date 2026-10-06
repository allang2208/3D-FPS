"""Save the reported laser visibility/aperture fixes in the existing editor."""
import json
import runpy
import shutil
from datetime import datetime
from pathlib import Path
import unreal as u

PROJECT = Path(__file__).resolve().parents[3]
L = u.MaterialEditingLibrary
E = u.EditorAssetLibrary
A = u.AssetToolsHelpers.get_asset_tools()
OUT = PROJECT / 'Saved/BlessedLaser20261006'
BEFORE = OUT / ('BeforeAssets-' + datetime.now().strftime('%H%M%S'))
PREFIX = 'LaserApertureV3:'
SCOPE = '/Game/Weapons/ScopeOptics20260927/M_ScopeAwareLaser'
BODY = '/Game/Weapons/M1911/Tactical20260913'
MATERIALS = [BODY + '/Materials/M_M1911_laser_Body', BODY + '/Wet/M_Wet_M_M1911_laser_Body']
GOLD = '/Game/Weapons/TacticalDevices20260913/BlessedLaser20261006/M_BlessedLaser'
for path in MATERIALS + [SCOPE + k for k in ['Dot', 'Beam']] + [GOLD + k for k in ['Dot', 'Beam']]:
    relative = Path(path.removeprefix('/Game/') + '.uasset')
    original = PROJECT / 'Content' / relative
    copy = BEFORE / relative
    copy.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(original, copy)


def node(mat, cls, desc):
    result = L.create_material_expression(mat, cls)
    result.set_editor_property('desc', desc)
    return result


def connect(source, target, pin, output=''):
    if not L.connect_material_expressions(source, output, target, pin):
        raise RuntimeError('Material pin connection failed: ' + pin)


def output(source, prop):
    if not L.connect_material_property(source, '', prop):
        raise RuntimeError('Material output connection failed: ' + str(prop))


def compile_material(mat):
    errors = L.recompile_material(mat)
    if errors:
        raise RuntimeError('Material compile failed: ' + str(errors))
    L.get_statistics(mat)


texture_path = '/Game/Weapons/TacticalDevices20260913/BlessedLaser20261006/T_LaserApertureMask'
task = u.AssetImportTask()
task.filename = str(PROJECT / 'SourceAssets/BlessedLaser20261006/Repair/T_LaserApertureMask.png')
task.destination_path, task.destination_name = texture_path.rsplit('/', 1)
task.automated = True
task.replace_existing = True
task.save = False
A.import_asset_tasks([task])
mask = E.load_asset(texture_path)
if mask is None:
    raise RuntimeError('Lens aperture texture was not imported')
mask.set_editor_property('srgb', False)
mask.set_editor_property('compression_settings', u.TextureCompressionSettings.TC_GRAYSCALE)
mask.set_editor_property('lod_group', u.TextureGroup.TEXTUREGROUP_WEAPON)
E.set_metadata_tag(mask, 'Source', 'Original M1911 compact lens region baked into shared laser UV0; housing excluded')
packages = [mask.get_outermost()]
saved_assets = [mask.get_path_name()]

for path in MATERIALS:
    mat = E.load_asset(path)
    if not isinstance(mat, u.Material):
        raise RuntimeError('Expected legacy body material: ' + path)
    for old in L.get_material_expressions(mat):
        if str(old.get_editor_property('desc')).startswith(PREFIX):
            L.delete_material_expression(mat, old)
    uv = node(mat, u.MaterialExpressionTextureCoordinate, PREFIX + ' Shared UV0')
    uv.set_editor_property('coordinate_index', 0)
    aperture = node(mat, u.MaterialExpressionTextureSample, PREFIX + ' Authored lens only')
    aperture.set_editor_property('texture', mask)
    aperture.set_editor_property('sampler_type', u.MaterialSamplerType.SAMPLERTYPE_LINEAR_GRAYSCALE)
    connect(uv, aperture, 'UVs')
    # Colour controls intensity only inside the explicit optical region.
    texture = node(mat, u.MaterialExpressionTextureSample, PREFIX + ' Optical red texture')
    texture.set_editor_property('texture', E.load_asset('/Game/Weapons/TacticalDevices20260913/Textures/T_laser_BaseColor'))
    texture.set_editor_property('sampler_type', u.MaterialSamplerType.SAMPLERTYPE_COLOR)
    connect(uv, texture, 'UVs')
    emission = node(mat, u.MaterialExpressionCustom, PREFIX + ' Red optical emission')
    emission.set_editor_property('code', 'float OpticalRed=saturate((Colour.r-max(Colour.g,Colour.b))*12.0); return float3(16.0,0.001,0.0005)*OpticalRed*saturate(Aperture);')
    emission.set_editor_property('output_type', u.CustomMaterialOutputType.CMOT_FLOAT3)
    inputs = []
    for name in ['Colour', 'Aperture']:
        pin = u.CustomInput()
        pin.set_editor_property('input_name', name)
        inputs.append(pin)
    emission.set_editor_property('inputs', inputs)
    connect(texture, emission, 'Colour', 'RGB')
    connect(aperture, emission, 'Aperture', 'R')
    output(emission, u.MaterialProperty.MP_EMISSIVE_COLOR)
    E.set_metadata_tag(mat, 'LaserApertureVersion', 'v3-uv-region-independent-of-vertex-colour')
    compile_material(mat)
    packages.append(mat.get_outermost())
    saved_assets.append(mat.get_path_name())

# Red is still red. Exposure compensation fixes bright outdoor attenuation
# without raising the whole scene or changing its accepted scope fade graph.
for kind in ['Dot', 'Beam']:
    mat = E.load_asset(SCOPE + kind)
    if E.get_metadata_tag(mat, 'LaserExposureVersion') != 'v1-signal':
        source = L.get_material_property_input_node(mat, u.MaterialProperty.MP_EMISSIVE_COLOR)
        source_pin = L.get_material_property_input_node_output_name(mat, u.MaterialProperty.MP_EMISSIVE_COLOR)
        strength = node(mat, u.MaterialExpressionMultiply, 'LaserExposure: signal intensity')
        strength.set_editor_property('const_b', 0.4)
        connect(source, strength, 'A', source_pin)
        inverse = node(mat, u.MaterialExpressionEyeAdaptationInverse, 'LaserExposure: preserve daylight red')
        light_pin = next(name for name in L.get_material_expression_input_names(inverse) if 'LightValue' in name)
        connect(strength, inverse, light_pin)
        output(inverse, u.MaterialProperty.MP_EMISSIVE_COLOR)
        E.set_metadata_tag(mat, 'LaserExposureVersion', 'v1-signal')
    compile_material(mat)
    packages.append(mat.get_outermost())
    saved_assets.append(mat.get_path_name())

if not u.EditorLoadingAndSavingUtils.save_packages(packages, False):
    raise RuntimeError('Laser repair packages did not save')
runpy.run_path(str(Path(__file__).with_name('create_materials.py')), run_name='__main__')
saved_assets += [GOLD + k for k in ['Dot', 'Beam']]
receipt = {'saved': True, 'assets': saved_assets, 'backup': str(BEFORE),
           'changes': ['G18/M1911 shared dry and wet shell emission limited to optical UV region',
                       'red and gold beam/dot exposure compensation', 'gold beam opacity and saturation increased'],
           'mesh_geometry_changed': False, 'new_emitter_model': 'concept_only', 'game_tested': False}
(OUT / 'visual-repair-save.json').write_text(json.dumps(receipt, indent=2), encoding='utf-8')
print('LASER_VISUAL_REPAIR_SAVED ' + json.dumps(receipt))
