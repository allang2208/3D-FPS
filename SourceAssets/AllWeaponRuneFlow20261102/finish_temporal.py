"""Finish compiling the fully connected temporal graph after input migration."""
import json
from pathlib import Path
import unreal as u
ROOT = Path(__file__).resolve().parent
PATH = '/Game/Skills/Whirlwind20260920/ForegroundV3/M_SilverRuneSurfaceV2_478649ff_WhirlwindV3'
L = u.MaterialEditingLibrary
if '-run=' not in u.SystemLibrary.get_command_line().lower():
    editor = u.get_editor_subsystem(u.LevelEditorSubsystem)
    if editor and editor.is_in_play_in_editor(): raise RuntimeError('PIE active; preserve material')
if PATH in {p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}:
    raise RuntimeError('Unsaved temporal material preserved')
mat = u.load_asset(PATH)
node = next(n for n in L.get_material_expressions(mat)
            if isinstance(n, u.MaterialExpressionCustom) and 'RuneTexture' in L.get_material_expression_input_names(n))
names = list(L.get_material_expression_input_names(node))
inputs = list(L.get_inputs_for_material_expression(mat, node))
missing = [name for name, source in zip(names, inputs) if not source]
if missing: raise RuntimeError('Incomplete temporal rune inputs: ' + ', '.join(missing))
errors = list(L.recompile_material(mat) or [])
if errors: raise RuntimeError('Temporal material compile failed: ' + str(errors))
if not u.EditorAssetLibrary.save_loaded_asset(mat, False): raise RuntimeError('Temporal save failed')
result = {'complete': True, 'inputs': {name: source.get_name() for name, source in zip(names, inputs)},
          'compile_errors': [str(e) for e in errors], 'saved_asset': mat.get_path_name(), 'runtime_tested': False}
(ROOT / 'temporal-final-compile.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
print('RUNE_TEMPORAL_FINAL_COMPILED input_count=' + str(len(names)))
