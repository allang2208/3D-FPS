"""Apply the persisted M4 default to an already-running editor, without starting play."""
import json
from pathlib import Path
import unreal as u

editor=u.get_editor_subsystem(u.UnrealEditorSubsystem)
world=editor.get_game_world() or editor.get_editor_world()
if not world:raise RuntimeError('No current world for applying the M4 appearance setting')
u.SystemLibrary.execute_console_command(world,'fps.Outfit.BareArmsCandidate 1')
value=u.SystemLibrary.get_console_variable_int_value('fps.Outfit.BareArmsCandidate')
if value!=1:raise RuntimeError('The running editor did not accept the M4 candidate setting')
receipt={'console_variable':'fps.Outfit.BareArmsCandidate','applied_value':value,
    'persistent_config':'Config/DefaultEngine.ini [ConsoleVariables]',
    'scope':'Local M4 first-person viewmodel, modular shirt and gloves unequipped',
    'started_play':False,'runtime_tested':False}
path=Path('D:/FPS3D/FPSGAME/SourceAssets/ModularOutfit20260924/RealisticM4Candidate/activation.json')
path.write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('M4_BARE_ARMS_DEFAULT_APPLIED',json.dumps(receipt))
