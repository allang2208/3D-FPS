"""Read the saved grip pair through the native graph, without starting gameplay."""
from pathlib import Path
import unreal as u
out=Path('D:/FPS3D/FPSGAME/SourceAssets/ThirdPersonSwordLeftContact20261010')
world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
u.SystemLibrary.execute_console_command(world,f'fps.body.DiagnoseSwordPose {out}/native-contact.json dash-arm')
print('SWORD_PAIR_GRAPH '+str(out/'native-contact.json'))
