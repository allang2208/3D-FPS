"""Save only the newly imported Bracken Fern and its biome binding, without PIE."""
import json
import runpy
from datetime import datetime
from pathlib import Path

import unreal as u

PROJECT = Path('D:/FPS3D/FPSGAME')
ROOT = PROJECT / 'SourceAssets/TemperateForestSpecies20261110'
DEST = '/Game/WorldGeneration/TemperateHills/ForestSpecies20261110'
DA_PATH = '/Game/WorldGeneration/TemperateHills/DA_TemperateHillsStreaming'
if Path(u.Paths.project_dir()).resolve() != PROJECT.resolve():
    raise RuntimeError('Wrong project')
editor = u.get_editor_subsystem(u.UnrealEditorSubsystem)
if editor.get_game_world():
    raise RuntimeError('Cannot save woodland assets during PIE')
owned = {DA_PATH, DEST + '/Materials/MI_Bracken_Fern_01',
         DEST + '/Textures/T_Bracken_Fern_01_CA', DEST + '/Textures/T_Bracken_Fern_01_NT'}
owned.update(DEST + '/Meshes/SK_BrackenFern_' + v for v in 'ABCD')
conflicts = [p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()
             if p.get_name() in owned]
if conflicts:
    raise RuntimeError('Preserve unsaved user packages: ' + repr(conflicts))
if '-run=pythonscript' in u.SystemLibrary.get_command_line().lower():
    u.SystemLibrary.execute_console_command(editor.get_editor_world(), 'Editor.AsyncStaticMeshCompilation 0')
u.AssetRegistryHelpers.get_asset_registry().scan_paths_synchronous(
    ['/Game/Megaplant_Library/Plant_Bracken_Fern'], True)
author = runpy.run_path(str(PROJECT / 'Tools/WorldGeneration/build_temperate_forest_species.py'))
da = author['load'](DA_PATH)
before = [str(x) for x in da.get_editor_property('forest_ferns')]
author['backup'](DA_PATH)
ferns = author['install_ferns'](da)
author['save'](da)
report = author['REPORT']
report.update({'finished_at': datetime.now().astimezone().isoformat(),
               'stage': 'fern_assets_saved', 'forest_ferns_before': before,
               'forest_ferns_after': [m.get_path_name() for m in ferns],
               'data_asset_fields_written': ['forest_ferns'],
               'existing_graph_reused': '/Game/WorldGeneration/TemperateHills/PCG_HillsShrubs',
               'generation_layer': 4, 'height_range_cm': [45, 100],
               'placement': 'Canopy, moisture and understory patches; exclude roads, spawn area, river and steep slopes',
               'texture_max_size': 2048})
(ROOT / 'Receipts/ferns.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
u.log('BRACKEN_FERN_SAVED ' + json.dumps({'count': len(ferns), 'receipt': str(ROOT / 'Receipts/ferns.json')}))
