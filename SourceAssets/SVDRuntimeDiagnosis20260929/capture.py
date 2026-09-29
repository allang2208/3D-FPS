import unreal as u
w=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world()
u.SystemLibrary.execute_console_command(w,'HighResShot 1 filename="D:/FPS3D/FPSGAME/SourceAssets/SVDRuntimeDiagnosis20260929/live.png"')
