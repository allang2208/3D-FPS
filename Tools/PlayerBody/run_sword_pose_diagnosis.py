"""Run only when explicitly investigating body contact; no game or asset saves."""
import unreal
world=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
unreal.SystemLibrary.execute_console_command(world,'fps.body.DiagnoseSwordPose D:/FPS3D/FPSGAME/SourceAssets/ThirdPersonTwoHandSword20261003/headless-pose.json')
