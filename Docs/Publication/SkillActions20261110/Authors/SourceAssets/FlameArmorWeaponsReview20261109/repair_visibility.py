import json,sys
from pathlib import Path
import unreal as u
ROOT=Path('D:/FPS3D/FPSGAME');OUT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'SourceAssets/StarMarrowRestore20261108'))
from restore_warm_sword import calibrate_warm_tongues
path='/Game/Skills/FlameArmor20261108/SwordRestoreV11/Materials/M_StarMarrowCampfireBlue_Warm'
if '-run=' not in u.SystemLibrary.get_command_line().lower():
 if u.get_editor_subsystem(u.LevelEditorSubsystem).is_in_play_in_editor():raise RuntimeError('Preserve PIE')
if path in {p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}:raise RuntimeError('Preserve unsaved material')
mat=u.load_asset(path)
if mat is None:raise RuntimeError(path)
calibrate_warm_tongues(mat)
(OUT/'visibility-repair-receipt.json').write_text(json.dumps(dict(saved_assets=[mat.get_path_name()],radiance_before_exposure=3.0,previous_radiance=.12,blue_source_modified=False,atlas_and_alpha_preserved=True),indent=2),encoding='utf-8')
print('WARM_FLAME_VISIBILITY_SAVED',mat.get_path_name())
