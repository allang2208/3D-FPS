"""Save the woodland ground transitions without recreating the biome or level."""
import json
import runpy
from datetime import datetime
from pathlib import Path
import unreal as u

PROJECT = Path('D:/FPS3D/FPSGAME')
ROOT = PROJECT / 'SourceAssets/TemperateForestComposition20261110'
BASE = '/Game/WorldGeneration/TemperateHills'
if Path(u.Paths.project_dir()).resolve() != PROJECT.resolve():
    raise RuntimeError('Wrong project')
editor = u.get_editor_subsystem(u.UnrealEditorSubsystem)
if editor.get_game_world():
    raise RuntimeError('Do not save woodland materials during PIE')
owned = {BASE + '/M_TemperateGround', BASE + '/PebbleShore/M_PebbleShoreGround',
         BASE + '/DA_TemperateHillsStreaming'}
owned.update(BASE + '/ForestSpecies20261110/Textures/T_ForestFloor_' + name
             for name in ('BaseColor', 'Normal', 'ARH'))
conflicts = [p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()
             if p.get_name() in owned]
if conflicts:
    raise RuntimeError('Preserve unsaved user changes: ' + repr(conflicts))
data = runpy.run_path(str(PROJECT / 'Tools/WorldGeneration/build_hills_ground_v2.py'), run_name='__main__')
report = {'finished_at': datetime.now().astimezone().isoformat(),
          'saved': data['REPORT']['saved'], 'stage': 'composition_materials_saved',
          'ground_material': data['REPORT']['ground_material'],
          'new_models_or_textures': False, 'map_modified': False,
          'game_run': False, 'visual_tested': False, 'performance_tested': False}
(ROOT / 'Receipts/assets.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
u.log('FOREST_COMPOSITION_SAVED ' + json.dumps(report))
