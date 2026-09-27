"""Repair only the footstep decal named by the runtime domain warning.

Use the shared bridge if the editor is open; otherwise use a rendering commandlet.
Does not start PIE, modify a map, or rebuild the puff/config/grass material family.
"""
import datetime
import importlib
import json
from pathlib import Path
import shutil
import sys
import unreal as u

ROOT = Path(u.Paths.project_dir())
OUT = ROOT / 'SourceAssets/GrassFootstepRepair20260926'
PATH = '/Game/WorldGeneration/GrassDeform/M_GrassTrampleDecal'
L, E = u.MaterialEditingLibrary, u.EditorAssetLibrary


def run():
    # End the existing play session before changing the material domain. The next user-started
    # play session recreates the pooled MIDs and decal render states from the corrected asset.
    editor = u.get_editor_subsystem(u.UnrealEditorSubsystem)
    if editor and editor.get_game_world() is not None:
        u.get_editor_subsystem(u.LevelEditorSubsystem).editor_request_end_play()
        print('FOOTSTEP_DECAL_END_PLAY_REQUESTED; no assets modified; rerun after PIE ends', flush=True)
        return
    if PATH in {str(p.get_path_name()) for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}:
        raise RuntimeError('Preserving unsaved footstep decal edits')
    OUT.mkdir(parents=True, exist_ok=True)
    backup = OUT / 'BeforeRepair/M_GrassTrampleDecal.uasset'
    if not backup.exists():
        backup.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / 'Content/WorldGeneration/GrassDeform/M_GrassTrampleDecal.uasset', backup)
    before = u.load_asset(PATH)
    old_domain = str(before.get_editor_property('material_domain'))
    old_front = str(L.get_material_property_input_node(before, u.MaterialProperty.MP_FRONT_MATERIAL))
    sys.path.insert(0, str(ROOT / 'Tools/GrassDeform'))
    import setup_assets_m3
    importlib.reload(setup_assets_m3)
    m = setup_assets_m3.build_decal_material()
    front = L.get_material_property_input_node(m, u.MaterialProperty.MP_FRONT_MATERIAL)
    alpha = L.get_material_property_input_node(m, u.MaterialProperty.MP_OPACITY)
    if m.get_editor_property('material_domain') != u.MaterialDomain.MD_DEFERRED_DECAL:
        raise RuntimeError('Footstep material still has the wrong domain')
    if not isinstance(front, u.MaterialExpressionSubstrateConvertToDecal) or alpha is None:
        raise RuntimeError('Missing explicit Substrate decal/coverage graph')
    decal_inputs = dict(zip(
        [str(name) for name in L.get_material_expression_input_names(front)],
        L.get_inputs_for_material_expression(m, front)))
    if decal_inputs.get('Coverage') != alpha:
        raise RuntimeError('The footprint alpha is not connected to actual decal Coverage')
    receipt = {
        'saved': m.get_path_name(), 'before_domain': old_domain, 'before_front_material': old_front,
        'after_domain': str(m.get_editor_property('material_domain')),
        'front_material': front.get_class().get_name(),
        'coverage_expression': alpha.get_path_name(),
        'coverage_connected': True,
        'fade_parameter': 'Fade', 'version': setup_assets_m3.version_tag(m),
        'runtime_tested': False, 'visually_tested': False,
    }
    stamp = datetime.datetime.now().strftime('%Y%m%d-%H%M%S')
    (OUT / ('decal-receipt-' + stamp + '.json')).write_text(json.dumps(receipt, indent=2), encoding='utf8')
    print('FOOTSTEP_DECAL_REPAIRED ' + json.dumps(receipt), flush=True)


if __name__ == '__main__':
    run()
