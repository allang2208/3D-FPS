"""Replace only the hills hazel wind graph; no map, play or rendering."""
import importlib.util
import json
from datetime import datetime
from pathlib import Path
import unreal as u

PROJECT=Path('D:/FPS3D/FPSGAME')
ROOT=PROJECT/'SourceAssets/TemperateShrubWindFix20261110'
BASE='/Game/WorldGeneration/TemperateHills'
owned={BASE+'/Atmosphere20261110/M_ForestShrubWind',
       BASE+'/ForestSpecies20261110/Materials/MI_Common_Hazel_Bark_01',
       BASE+'/ForestSpecies20261110/Materials/MI_Common_Hazel_Foliage_01'}
if Path(u.Paths.project_dir()).resolve()!=PROJECT.resolve():raise RuntimeError('Wrong project')
if u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world():
    raise RuntimeError('Preserve the running play world; save the shrub fix outside PIE')
dirty=[p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages() if p.get_name() in owned]
if dirty:raise RuntimeError('Preserve unsaved shrub assets: '+repr(dirty))
spec=importlib.util.spec_from_file_location('hills_shrub_wind_author',PROJECT/'Tools/WorldGeneration/build_temperate_forest_atmosphere.py')
author=importlib.util.module_from_spec(spec)
spec.loader.exec_module(author)
author.ROOT=ROOT
author.shrub_material(author.load(BASE+'/Atmosphere20261110/MPC_ForestWind'))
author.REPORT['finished_at']=datetime.now().astimezone().isoformat()
(ROOT/'Receipts/assets.json').write_text(json.dumps(author.REPORT,indent=2),encoding='utf-8')
u.log('HILLS_SHRUB_WIND_SAVED '+str(len(author.REPORT['saved'])))
