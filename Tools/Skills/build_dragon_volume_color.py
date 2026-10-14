"""V8 R2: warm Dragon Breath body, preserving the fluid simulation/extinction.

Author/save only. Works in the isolated author commandlet or the existing editor
bridge after PIE stops. No simulation, screenshots or acceptance tests.
"""
import json
import sys
from pathlib import Path
import unreal as u

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'Tools/Skills'))
if not hasattr(u, 'RainAssetEditor'):
    u.RainAssetEditor = u.DragonBreathAuthorLibrary
from build_fireball_assets import LIB, ref, setdata, put

DEST = '/Game/Skills/DragonBreath20261013/VolumeV8'
SYSTEM = DEST + '/NS_DragonVolume'
GRID = 'Grid3D_Gas_Master_Emitter'
REVISION = 'DragonBreathVolumeV8R2_20261014'
OUT = ROOT / 'SourceAssets/DragonBreath20261013/VolumeV8R2_20261014'
COLOR_MIN = .35
COLOR_MAX = 160.
COLOR_GAIN = .4


def duplicate(source, name):
    path = DEST + '/' + name
    asset = u.load_asset(path) if u.EditorAssetLibrary.does_asset_exist(path) else u.AssetToolsHelpers.get_asset_tools().duplicate_asset(name, DEST, u.load_asset(source))
    if not asset:
        raise RuntimeError('Missing Dragon Breath material source: ' + source)
    return asset


def expression_node(material, cls, tag):
    for node in u.ObjectIterator(cls):
        if node.get_outer() == material and str(node.get_editor_property('desc')) == tag:
            return node
    node = LIB.create_material_expression(material, cls)
    node.set_editor_property('desc', tag)
    return node


def flame_material():
    eal = u.EditorAssetLibrary
    # Reuse the already saved RG/local-space/exposure repair. Fresh rebuilds can
    # recreate that baseline, but normal R2 updates never rewrite its packages.
    if not eal.does_asset_exist(DEST + '/M_DragonVolumeFlame_R1'):
        from repair_dragon_volume_visibility import exposure_material
        exposure_material()
    base = duplicate(DEST + '/M_DragonVolumeFlame_R1', 'M_DragonVolumeFlame_R2')
    texture = u.find_object(None, base.get_path_name() + ':MaterialExpressionTextureSampleParameterVolume_0')
    selection = u.find_object(None, base.get_path_name() + ':MaterialExpressionStaticSwitchParameter_2')
    if not texture or not selection:
        raise RuntimeError('Missing native VolumeTex / thermal-color selection nodes')

    ramp = expression_node(base, u.MaterialExpressionCustom, 'DragonVolume.ColorRamp.R2')
    pins = []
    for name in ['Temperature', 'ColorMin', 'ColorMax']:
        pin = u.CustomInput()
        pin.set_editor_property('input_name', name)
        pins.append(pin)
    ramp.set_editor_property('inputs', pins)
    ramp.set_editor_property('output_type', u.CustomMaterialOutputType.CMOT_FLOAT3)
    ramp.set_editor_property('code', (OUT / 'DragonFlameColor.hlsl').read_text(encoding='utf-8'))
    if not LIB.connect_material_expressions(texture, 'G', ramp, 'Temperature'):
        raise RuntimeError('Could not connect the RG grid temperature')
    for name, value in [('ColorMin', COLOR_MIN), ('ColorMax', COLOR_MAX)]:
        scalar = expression_node(base, u.MaterialExpressionScalarParameter, 'DragonVolume.' + name + '.R2')
        scalar.set_editor_property('parameter_name', 'Dragon' + name)
        scalar.set_editor_property('default_value', value)
        if not LIB.connect_material_expressions(scalar, '', ramp, name):
            raise RuntimeError('Could not connect ' + name)
    # Both branches use our warm ramp, so the inherited Niagara blackbody static
    # binding cannot reinstate the white-hot curve. Smoke/extinction are untouched.
    for pin in ['True', 'False']:
        if not LIB.connect_material_expressions(ramp, '', selection, pin):
            raise RuntimeError('Could not replace the thermal-color branch ' + pin)
    eal.set_metadata_tag(base, 'DragonVolume.ColorCurve', REVISION)

    mi = duplicate(DEST + '/MI_DragonVolumeFlame_R1', 'MI_DragonVolumeFlame_R2')
    LIB.set_material_instance_parent(mi, base)
    for name, value in [('DragonColorMin', COLOR_MIN), ('DragonColorMax', COLOR_MAX)]:
        LIB.set_material_instance_scalar_parameter_value(mi, name, value)
    LIB.update_material_instance(mi)
    errors = LIB.recompile_material(base)
    if errors:
        raise RuntimeError(str(errors))
    compiler = u.DragonBreathAuthorLibrary if hasattr(u, 'DragonBreathAuthorLibrary') else u.PoisonMaggotMonster
    if not compiler.compile_material_assets([base, mi]):
        raise RuntimeError('Dragon Breath warm material compilation failed')
    for asset in [base, mi]:
        if not eal.save_loaded_asset(asset, False):
            raise RuntimeError('Save failed: ' + asset.get_path_name())
    return mi


def apply(system):
    mi = flame_material()
    put(system, GRID, 'EmitterUpdateScript', 'Grid3D_Gas_MaterialControls',
        'Temperature Color Gain', '(HlslExpression=".4*saturate(User.Strength)")',
        '/Script/NiagaraEditor.NiagaraExt_StackInputData_HlslExpression')
    setdata('SetRendererData', u.NiagaraExt_RendererData, ref(system, GRID, renderer=1),
            {'Material': mi.get_path_name()})
    u.EditorAssetLibrary.set_metadata_tag(system, 'DragonBreath.Revision', REVISION)
    return mi


def run():
    if not hasattr(u, 'DragonBreathAuthorLibrary') and u.EditorLevelLibrary.get_game_world():
        raise RuntimeError('Stop PIE before saving the active Dragon Breath system')
    system = u.load_asset(SYSTEM)
    if not system:
        raise RuntimeError('Missing active Dragon Breath system')
    mi = apply(system)
    if not u.RainAssetEditor.compile_rain(system, True):
        raise RuntimeError('Dragon Breath Niagara compilation failed')
    if not u.EditorAssetLibrary.save_loaded_asset(system, False):
        raise RuntimeError('Dragon Breath system save failed')
    receipt = {'revision': REVISION, 'stage': 'assets_saved', 'asset': system.get_path_name(),
               'saved_assets': [system.get_path_name(), mi.get_path_name(), mi.get_editor_property('parent').get_path_name()],
               'color_temperature_range': [COLOR_MIN, COLOR_MAX], 'color_gain': COLOR_GAIN,
               'opacity_temperature_range_unchanged': [.35, 5.3], 'opacity_gain_unchanged': 1.25,
               'density_gain_unchanged': .18, 'extra_volume_texture_samples': 0,
               'exposure_inverse_count': 1, 'native_gameplay_changed': False,
               'runtime_tested': False, 'rendered': False, 'visual_acceptance': False}
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / 'delivery.json').write_text(json.dumps(receipt, indent=2), encoding='utf-8')
    (OUT.parent / 'asset-authoring.json').write_text(json.dumps(receipt, indent=2), encoding='utf-8')
    print('DRAGON_VOLUME_R2_SAVED ' + system.get_path_name())


if __name__ == '__main__':
    run()
