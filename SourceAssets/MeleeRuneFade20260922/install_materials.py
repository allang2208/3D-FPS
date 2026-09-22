"""Save only the three authored rune materials using the serialized UE bridge."""
from pathlib import Path
from datetime import datetime
import json
import os
import shutil
import unreal as u

P = Path(__file__).resolve().parent
ROOT = P.parents[1]
E, L = u.MaterialEditingLibrary, u.EditorAssetLibrary
SOURCE = json.loads((P / 'material_sources.json').read_text(encoding='utf-8'))
SPEC = {
    'shared': ('semantic_fade.hlsl', 'Semantic runes: soft coverage and slow offset breathing',
               {'RuneOpacity': .90, 'HaloOpacity': .16, 'HaloRadiusTexels': 2.2}),
    'spirit': ('spirit_fade.hlsl', 'Frost spirit: ice echoes with soft arrival and dissolution',
               {'BurstRate': .27, 'EdgeSoftness': .07}),
    'gold': ('native_gold_fade.hlsl', 'Native gold: fading emission on original blade and guard ink', {}),
}
if u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world() is not None:
    raise RuntimeError('Active play preserved; finish play before saving rune assets.')
BACKUP = P / 'Before'
BACKUP.mkdir(exist_ok=True)
receipt = {'time': datetime.now().isoformat(), 'editor_pid': os.getpid(),
           'saved_assets': [], 'complete': False, 'tested': False}
def record():
    (P / 'install_receipt.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2), encoding='utf-8')

work = []
for key, (filename, description, parameters) in SPEC.items():
    row = SOURCE[key]
    material = u.load_asset(row['asset'])
    if material is None:
        raise RuntimeError('Missing installed material ' + row['asset'])
    nodes = list(E.get_material_expressions(material))
    marker = 'FlowStrength' if key == 'gold' else 'RuneTexture'
    custom = next(n for n in nodes if isinstance(n, u.MaterialExpressionCustom)
                  and marker in n.get_editor_property('code'))
    previous = next(n for n in row['nodes'] if n['type'] == 'custom' and marker in n['code'])
    code = (P / filename).read_text(encoding='utf-8')
    # Preserve real intervening material edits. Known identical authored code can resume a save.
    if custom.get_editor_property('code') not in (previous['code'], code):
        raise RuntimeError('Concurrent rune material edit preserved: ' + row['asset'])
    source_file = ROOT / 'Content' / (row['asset'].removeprefix('/Game/') + '.uasset')
    if not (BACKUP / source_file.name).exists():
        shutil.copy2(source_file, BACKUP / source_file.name)
    work.append((material, nodes, custom, code, description, parameters))
if not (BACKUP / 'material_sources.json').exists():
    shutil.copy2(P / 'material_sources.json', BACKUP / 'material_sources.json')
record()
for material, nodes, custom, code, description, parameters in work:
    custom.set_editor_property('code', code)
    custom.set_editor_property('description', description)
    for name, value in parameters.items():
        param = next(n for n in nodes if isinstance(n, u.MaterialExpressionScalarParameter)
                     and str(n.get_editor_property('parameter_name')) == name)
        param.set_editor_property('default_value', value)
    errors = list(E.recompile_material(material))
    if errors:
        raise RuntimeError('Material compilation failed: ' + str(errors))
    L.set_metadata_tag(material, 'RuneAppearanceRevision', 'MeleeRuneFade20260922')
    if not L.save_loaded_asset(material, False):
        raise RuntimeError('Could not save ' + material.get_path_name())
    receipt['saved_assets'].append({'asset': material.get_path_name(), 'compile_errors': errors})
    record()
receipt['complete'] = True
record()
print('MELEE_RUNE_FADE_MATERIALS_SAVED ' + str(len(receipt['saved_assets'])))
