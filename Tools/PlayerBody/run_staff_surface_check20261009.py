"""Evaluate the built native correction and newly saved equipment meshes."""
import unreal as u
world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
u.SystemLibrary.execute_console_command(world,'fps.body.DiagnoseStaffPose D:/FPS3D/FPSGAME/SourceAssets/ThirdPersonStaffSurfaceRepair20261009/FinalCheck')
