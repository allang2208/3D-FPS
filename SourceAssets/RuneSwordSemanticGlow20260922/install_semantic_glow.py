"""Apply semantic palettes to the installed material graphs via the editor bridge.

No PIE, captures, gameplay changes, C++ hot patches, or unrelated asset saves.
"""
from pathlib import Path
from datetime import datetime
import json
import shutil
import unreal as u

P = Path(__file__).resolve().parent
ROOT = P.parents[1]
E = u.MaterialEditingLibrary
SOURCE = json.loads((P / 'material_sources.json').read_text(encoding='utf-8'))
PALETTE = json.loads((P / 'palette.json').read_text(encoding='utf-8'))
REVISION = 'RuneSwordSemanticGlow20260922'
BACKUP = P / 'Before'
BACKUP.mkdir(exist_ok=True)
assets = {key: u.load_asset(row['asset']) for key, row in SOURCE.items()}
if any(asset is None for asset in assets.values()):
    raise RuntimeError('Required installed rune material missing')
if u.get_editor_subsystem(u.LevelEditorSubsystem).is_in_play_in_editor():
    raise RuntimeError('End PIE before saving rune materials')

# Keep the installed graph intact; reject an actual intervening graph edit.
customs = {}
resume_overlay_save = False
for key in ('overlay', 'native_gold'):
    nodes = list(E.get_material_expressions(assets[key]))
    wanted = next(n for n in nodes if isinstance(n, u.MaterialExpressionCustom)
                  and ('RuneTexture' in n.get_editor_property('code') if key == 'overlay'
                       else n.get_editor_property('desc') == 'NativeRuneGold20260922:GoldEmission'))
    prior = next(n for n in SOURCE[key]['nodes'] if n['type'] == 'MaterialExpressionCustom'
                 and ('RuneTexture' in n['code'] if key == 'overlay'
                      else n['desc'] == 'NativeRuneGold20260922:GoldEmission'))
    if wanted.get_editor_property('code') != prior['code']:
        if key == 'overlay' and wanted.get_editor_property('code') == (P / 'semantic_runes.hlsl').read_text(encoding='utf-8'):
            # First call completed graph authoring/compilation, then PIE blocked
            # SaveLoadedAsset. Resume at that known boundary, not by replaying edits.
            resume_overlay_save = True
        else:
            raise RuntimeError('Material graph changed since authoring read: ' + SOURCE[key]['asset'])
    customs[key] = wanted
for key, row in SOURCE.items():
    source = ROOT / 'Content' / (row['asset'].removeprefix('/Game/') + '.uasset')
    target = BACKUP / source.name
    if not target.exists():
        shutil.copy2(source, target)
shutil.copy2(P / 'material_sources.json', BACKUP / 'material_sources.json')

receipt = {'installed_at': datetime.now().isoformat(timespec='seconds'),
           'palette': PALETTE, 'saved_assets': [], 'runtime_testing': 'not run; user will test'}

def parameter(material, cls, name, value):
    nodes = list(E.get_material_expressions(material))
    expr = next((n for n in nodes if isinstance(n, cls)
                 and str(n.get_editor_property('parameter_name')) == name), None)
    if expr is None:
        expr = E.create_material_expression(material, cls)
        expr.set_editor_property('parameter_name', name)
        expr.set_editor_property('desc', REVISION + ':' + name)
    expr.set_editor_property('default_value', value)
    expr.set_editor_property('group', 'Semantic rune appearance')
    return expr

def compile_save(key, build=True):
    mat = assets[key]
    errors = list(E.recompile_material(mat)) if build else []
    if errors:
        raise RuntimeError('Material build failed: ' + '\n'.join(map(str, errors)))
    u.EditorAssetLibrary.set_metadata_tag(mat, 'RuneAppearanceRevision', REVISION)
    if not u.EditorAssetLibrary.save_loaded_asset(mat, False):
        raise RuntimeError('Could not save material: ' + mat.get_path_name())
    receipt['saved_assets'].append({'asset': mat.get_path_name(), 'shader_compile_errors': errors})
    (P / 'install_receipt.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2), encoding='utf-8')

overlay = assets['overlay']
custom = customs['overlay']
if not resume_overlay_save:
    inputs = list(custom.get_editor_property('inputs'))
    names = {str(pin.get_editor_property('input_name')) for pin in inputs}
    for name in (*PALETTE['overlay_colors_linear'], 'EmissionPeak'):
        if name not in names:
            pin = u.CustomInput()
            pin.set_editor_property('input_name', name)
            inputs.append(pin)
    custom.set_editor_property('inputs', inputs)
    custom.set_editor_property('code', (P / 'semantic_runes.hlsl').read_text(encoding='utf-8'))
    custom.set_editor_property('description', 'Semantic cyan resonance, violet erosion, blue conduction, warm gold recovery')
    for name, value in PALETTE['overlay_colors_linear'].items():
        expr = parameter(overlay, u.MaterialExpressionVectorParameter, name, u.LinearColor(*value))
        if not E.connect_material_expressions(expr, 'RGB', custom, name):
            raise RuntimeError('Could not connect rune color: ' + name)
    for name, value in PALETTE['overlay_scalars'].items():
        expr = parameter(overlay, u.MaterialExpressionScalarParameter, name, value)
        if name == 'EmissionPeak' and not E.connect_material_expressions(expr, '', custom, name):
            raise RuntimeError('Could not connect hue-preserving intensity limit')
compile_save('overlay', build=not resume_overlay_save)

native = assets['native_gold']
customs['native_gold'].set_editor_property('code', (P / 'native_gold_glow.hlsl').read_text(encoding='utf-8'))
for name, value in PALETTE['native_colors_linear'].items():
    parameter(native, u.MaterialExpressionVectorParameter, name, u.LinearColor(*value))
for name, value in PALETTE['native_scalars'].items():
    parameter(native, u.MaterialExpressionScalarParameter, name, value)
compile_save('native_gold')

# Keep the existing native instance and both runtime-selected masks; use
# explicit values here so older editor instance overrides cannot desaturate it.
mi = assets['native_instance']
for name, value in PALETTE['native_colors_linear'].items():
    E.set_material_instance_vector_parameter_value(mi, name, u.LinearColor(*value))
for name, value in PALETTE['native_scalars'].items():
    E.set_material_instance_scalar_parameter_value(mi, name, value)
E.update_material_instance(mi)
if not u.EditorAssetLibrary.save_loaded_asset(mi, False):
    raise RuntimeError('Could not save native gold instance')
receipt['saved_assets'].append({'asset': mi.get_path_name()})
(P / 'install_receipt.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2), encoding='utf-8')
print('RUNE_SEMANTIC_GLOW_SAVED', len(receipt['saved_assets']))
