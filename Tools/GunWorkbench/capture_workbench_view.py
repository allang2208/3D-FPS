import unreal as u,datetime
from pathlib import Path
filename='view-'+datetime.datetime.now().strftime('%H%M%S')+'.png'
root=Path('D:/FPS3D/FPSGAME/SourceAssets/GunWorkbenchVisibleFix20260928')
world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world()
if not world:raise RuntimeError('Reported game scene is no longer running')
u.SystemLibrary.execute_console_command(world,'Shot filename="'+str(root/filename)+'" nosuffix')
print('WORKBENCH_SCREENSHOT_REQUESTED '+str(root/filename))
