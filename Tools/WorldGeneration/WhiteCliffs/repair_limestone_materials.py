"""Repair the three owned limestone graphs after SM6 reported missing Clamp inputs."""
import json
import shutil
from pathlib import Path
import sys
import unreal as u

tool_dir = str(Path(__file__).resolve().parent)
if tool_dir not in sys.path:
    sys.path.insert(0, tool_dir)
from quarry_spoil_surface import WEATHER_COLOR, apply_weathered_finish

ROOT = Path('D:/FPS3D/FPSGAME')
OUT = ROOT / 'SourceAssets/HillsLandscapeRepair20261117/MaterialsR7'
OUT.mkdir(parents=True, exist_ok=True)
L = u.MaterialEditingLibrary
E = u.EditorAssetLibrary
report = {'materials': []}

def connect(source, output, target, pin=''):
    if not L.connect_material_expressions(source, output, target, pin):
        raise RuntimeError(f'Cannot connect {source.get_name()} -> {target.get_name()}:{pin}')

for name in ('CliffA', 'CliffB', 'LimestoneSpoil'):
    package = '/Game/WorldGeneration/TemperateHills/WhiteCliffs/Materials/M_' + name
    source = ROOT / ('Content/' + package.removeprefix('/Game/') + '.uasset')
    backup = OUT / source.name
    if not backup.exists():
        shutil.copy2(source, backup)
    mat = u.load_asset(package)
    if not isinstance(mat, u.Material):
        raise RuntimeError('Missing owned material ' + package)
    nodes = list(L.get_material_expressions(mat))
    def one(cls, upstream=None):
        found = [n for n in nodes if isinstance(n, cls)]
        if upstream is not None and len(found) > 1:
            found = [n for n in found if upstream in L.get_inputs_for_material_expression(mat, n)]
        if len(found) != 1:
            raise RuntimeError(f'{package}: expected one {cls.__name__}, got {len(found)}')
        return found[0]
    texture = next(n for n in nodes if isinstance(n, u.MaterialExpressionTextureSample)
                   and n.texture.get_name().endswith('_BaseColor'))
    mono = one(u.MaterialExpressionDesaturation, texture)
    power = one(u.MaterialExpressionPower, mono)
    multiply = one(u.MaterialExpressionMultiply, power)
    # The finish can add its own vectors. The limestone tint feeds this multiply.
    inputs = list(L.get_inputs_for_material_expression(mat, multiply))
    tint = next((n for n in inputs if isinstance(n, u.MaterialExpressionConstant3Vector)), None)
    if tint is None:
        tint = one(u.MaterialExpressionConstant3Vector)
    clamp = one(u.MaterialExpressionClamp, multiply)
    constants = [n for n in nodes if isinstance(n, u.MaterialExpressionConstant)]
    fraction = next((n for n in L.get_inputs_for_material_expression(mat, mono)
                     if isinstance(n, u.MaterialExpressionConstant)), None)
    if fraction is None:
        fraction = next(n for n in constants if abs(n.r - 1.) < .001)
    exponent = next((n for n in L.get_inputs_for_material_expression(mat, power)
                     if isinstance(n, u.MaterialExpressionConstant)), None)
    if exponent is None:
        exponent = next(n for n in constants if abs(n.r - .65) < .001)
    exponent.r = .65
    tint.constant = u.LinearColor(1.05, 1.035, .98, 1.)
    clamp.set_editor_property('min_default', 0.)
    clamp.set_editor_property('max_default', .58)
    # Empty pin names select input zero; UE shortens that displayed pin name.
    connect(texture, 'RGB', mono)
    connect(fraction, '', mono, 'Fraction')
    connect(mono, '', power, 'Base')
    connect(exponent, '', power, 'Exp')
    connect(power, '', multiply, 'A')
    connect(tint, '', multiply, 'B')
    connect(multiply, '', clamp)
    weather_color = next((n for n in nodes if isinstance(n, u.MaterialExpressionCustom)
                         and str(n.get_editor_property("desc")) == WEATHER_COLOR), None)
    if weather_color:
        connect(clamp, '', weather_color, 'Base')
    elif not L.connect_material_property(clamp, '', u.MaterialProperty.MP_BASE_COLOR):
        raise RuntimeError('Cannot connect limestone base color')
    mat.set_editor_property('used_with_instanced_static_meshes', True)
    # Both closed scan revisions have outward-facing backs. Open scans still need both sides.
    mesh_prefix = '/Game/WorldGeneration/TemperateHills/WhiteCliffs/Meshes/SM_White' + name
    two_sided = not any(E.does_asset_exist(mesh_prefix + suffix) for suffix in ('_SolidR9', '_Solid'))
    mat.set_editor_property('two_sided', two_sided)
    apply_weathered_finish(mat)
    errors = L.recompile_material(mat)
    if errors or not E.save_loaded_asset(mat, False):
        raise RuntimeError(f"Cannot save {package}: {errors}")
    report['materials'].append({'path': package,
        'texture': texture.texture.get_path_name(),
        'texture_srgb': texture.texture.srgb,
        'texture_size': [texture.texture.blueprint_get_size_x(), texture.texture.blueprint_get_size_y()],
        'clamp_inputs': list(L.get_material_expression_input_names(clamp)),
        'desaturation_inputs': list(L.get_material_expression_input_names(mono)),
        'two_sided': two_sided, 'albedo_exponent': exponent.r,
        'albedo_tint': [1.05, 1.035, .98], 'saved': True})
    (OUT / 'saved.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
u.log('HILLS_LIMESTONE_MATERIALS_SAVED')
