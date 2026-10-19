"""Run the explicitly requested isolated cloth solver diagnosis in a commandlet."""
import json
from pathlib import Path
import unreal as u
R=Path('D:/FPS3D/FPSGAME/SourceAssets/BlueMageRobe20261018/StairRepair20261019')
req=json.loads((R/'simulation-request.json').read_text());out=R/('simulation-'+req['label']+'.json')
if out.exists():raise RuntimeError('Use a fresh simulation label')
u.SystemLibrary.execute_console_command(u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world(),'fps.Robe.SimulateStairs')
if not out.exists():raise RuntimeError('Cloth solver command did not produce its result')
data=json.loads(out.read_text())
if len(data['samples'])<30:raise RuntimeError('Cloth simulation did not run all requested frames')
print('ROBE_STAIRS_SIMULATED',req['label'],len(data['samples']),flush=True)
