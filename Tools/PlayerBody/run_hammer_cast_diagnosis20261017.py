"""Explicit arm-direction diagnosis in a headless editor; no game or saves."""
import unreal
world=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
unreal.SystemLibrary.execute_console_command(world,'fps.body.DiagnoseHammerCast D:/FPS3D/FPSGAME/SourceAssets/WarhammerCastArm20261017/DirectionV2/native-graph-diagnosis.json')
