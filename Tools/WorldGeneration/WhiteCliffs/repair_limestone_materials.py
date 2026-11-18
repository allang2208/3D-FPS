"""Repair the three owned limestone graphs after SM6 reported missing Clamp inputs."""
import json
import shutil
from pathlib import Path
import unreal as u

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
    def one(cls):
        found = [n for n in nodes if isinstance(n, cls)]
        if len(found) != 1:
            raise RuntimeError(f'{package}: expected one {cls.__name__}, got {len(found)}')
        return found[0]
    texture = next(n for n in nodes if isinstance(n, u.MaterialExpressionTextureSample)
                   and n.texture.get_name().endswith('_BaseColor'))
    mono = one(u.MaterialExpressionDesaturation)
    power = one(u.MaterialExpressionPower)
    multiply = one(u.MaterialExpressionMultiply)
    tint = one(u.MaterialExpressionConstant3Vector)
    clamp = one(u.MaterialExpressionClamp)
    constants = [n for n in nodes if isinstance(n, u.MaterialExpressionConstant)]
    fraction = next(n for n in constants if abs(n.r - 1.) < .001)
    exponent = next(n for n in constants if n != fraction)
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
    if not L.connect_material_property(clamp, '', u.MaterialProperty.MP_BASE_COLOR):
        raise RuntimeError('Cannot connect limestone base color')
    mat.set_editor_property('used_with_instanced_static_meshes', True)
    # Original scans are open faces; the closed R8 replacements use proper
    # outward-facing back geometry and no longer need two-sided rasterization.
    two_sided = not E.does_asset_exist(
        '/Game/WorldGeneration/TemperateHills/WhiteCliffs/Meshes/SM_White' + name + '_Solid')
    mat.set_editor_property('two_sided', two_sided)
    L.recompile_material(mat)
    if not E.save_loaded_asset(mat, False):
        raise RuntimeError('Cannot save ' + package)
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
