"""Repair the existing charge-bar shader without reimporting its artwork."""
from pathlib import Path
import json
import unreal as u

P = Path(__file__).resolve().parent
package = '/Game/Weapons/FrostCrystalSword20260915/StarMarrowChargeHUD20261103/M_StarMarrowChargeHUD'
if '-run=' not in u.SystemLibrary.get_command_line().lower():
    editor = u.get_editor_subsystem(u.LevelEditorSubsystem)
    if editor and editor.is_in_play_in_editor():
        raise RuntimeError('End PIE before repairing the charge HUD material')
if any(p.get_name() == package for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()):
    raise RuntimeError('Preserve unsaved charge HUD material changes')

mat = u.EditorAssetLibrary.load_asset(package)
if not mat:
    raise RuntimeError('Charge HUD material is missing')
nodes = [n for n in u.MaterialEditingLibrary.get_material_expressions(mat)
         if isinstance(n, u.MaterialExpressionCustom)]
if len(nodes) != 1:
    raise RuntimeError('Charge HUD custom shader changed; preserve the current graph')
shader = nodes[0]
before = str(shader.get_editor_property('code'))
after = (P.parent / 'charge_bar.hlsl').read_text(encoding='utf8')
if before != after and before.replace('float2 point=', 'float2 sparkPosition=').replace('(UV-point)', '(UV-sparkPosition)') != after:
    raise RuntimeError('Charge HUD has other shader edits; preserve them')
(P / 'Before' / 'material-shader.hlsl').write_text(before, encoding='utf8')
shader.set_editor_property('code', after)
errors = u.MaterialEditingLibrary.recompile_material(mat)
if errors:
    raise RuntimeError('Charge HUD shader compile failed: ' + str(errors))
# RecompileMaterial queues DXC work. Finish that work before reporting the asset as compiled.
u.SystemLibrary.execute_console_command(None, 'Editor.AsyncAssetCompilationFinishAll')
if not u.EditorAssetLibrary.save_loaded_asset(mat, False):
    raise RuntimeError('Cannot save the repaired charge HUD material')
(P / 'delivery.json').write_text(json.dumps(dict(
    saved_asset=mat.get_path_name(), fixed='HLSL reserved keyword point renamed to sparkPosition',
    shader_compilation_waited=True, artwork_changed=False, native_code_changed=False,
    gameplay_tested=False, visual_tested=False), indent=2), encoding='utf8')
print('STAR_MARROW_CHARGE_HUD_SHADER_REPAIRED', mat.get_path_name())
