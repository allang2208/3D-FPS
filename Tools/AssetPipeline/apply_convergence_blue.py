"""Save the convergence material and apply its project settings to the open editor."""
from pathlib import Path
import runpy
import unreal

root = Path(unreal.Paths.project_dir())
runpy.run_path(str(root / 'Tools/AssetPipeline/build_convergence_v2.py'))
world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
unreal.SystemLibrary.execute_console_command(world, 'fps.Tracer.Converged.Tint 0.08,0.35,1.0')
unreal.SystemLibrary.execute_console_command(world, 'fps.Tracer.Trail.Emission 0.75')
unreal.log('CONVERGENCE_BLUE_APPLIED: material saved; current editor and DefaultEngine.ini use blue / 0.75 trail emission')
