"""Install the two prepared cloth layers and revised carry clips under one bridge lock."""
from pathlib import Path
import unreal as u
folder=Path(__file__).parent
if u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world():raise RuntimeError('PIE active; import deferred')
def run(stage,**flags):
    path=folder/'import_assets.py'
    exec(compile(path.read_text(encoding='utf-8'),str(path),'exec'),{'__file__':str(path),'__name__':'__main__','WITCH_REBUILT_STAGE':stage,**flags})
run('mesh',WITCH_REBUILT_GARMENT_REFRESH=True)
run('cloth')
run('animations_a',WITCH_REBUILT_ROLES=('Idle','Walk','CastPoison','ThrowPoisonBottle'))
run('animations_b',WITCH_REBUILT_ROLES=('Hit','TurnLeft','TurnRight'))
receipt=folder/'record_drape04.py'
exec(compile(receipt.read_text(encoding='utf-8'),str(receipt),'exec'),{'__file__':str(receipt),'__name__':'__main__'})
print('Current Drape05 and Carry04 assets imported and saved; no gameplay run')
