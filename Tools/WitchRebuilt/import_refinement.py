"""One mutex-protected install of prepared Witch assets; no gameplay test."""
from pathlib import Path
import unreal as u
folder=Path(__file__).parent
if u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world():
    raise RuntimeError('PIE is active; candidate installation deferred without changes')
for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages():
    if p.get_path_name().startswith('/Game/Monsters/WitchRebuilt'):
        raise RuntimeError('Unsaved candidate package retained: '+p.get_path_name())
def run(file,**flags):
    path=folder/file
    exec(compile(path.read_text(encoding='utf-8'),str(path),'exec'),{'__file__':str(path),'__name__':'__main__',**flags})
run('install_refinement_materials.py')
run('import_assets.py',WITCH_REBUILT_STAGE='mesh',WITCH_REBUILT_GARMENT_REFRESH=True)
run('import_assets.py',WITCH_REBUILT_STAGE='cloth')
run('import_assets.py',WITCH_REBUILT_STAGE='animations_a',WITCH_REBUILT_ROLES=('Idle','Walk','CastPoison','ThrowPoisonBottle'))
run('import_assets.py',WITCH_REBUILT_STAGE='animations_b',WITCH_REBUILT_ROLES=('Hit','DeathBackward','TurnLeft','TurnRight'))
print('WITCH REFINEMENT03 INSTALLED AND SAVED; gameplay not started')
