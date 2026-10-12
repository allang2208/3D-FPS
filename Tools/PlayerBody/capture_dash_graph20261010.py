"""Explicit pose-only diagnosis; no PIE or changes to loaded gameplay actors."""
from pathlib import Path
import unreal as u
out=Path('D:/FPS3D/FPSGAME/SourceAssets/ThirdPersonDashArm20261010')
world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
phase='after' if (out/'assets-published.json').exists() else 'before'
u.SystemLibrary.execute_console_command(world,f'fps.body.DiagnoseSwordPose {out}/graph-{phase}.json dash-arm')
print('DASH_GRAPH_CAPTURE '+str(out/f'graph-{phase}.json'))
