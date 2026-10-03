from pathlib import Path
M07_REQUESTED_STAGE='mesh_source'
script=Path('D:/FPS3D/FPSGAME/Tools/BlindSupplicantM07/run_editor_stage.py')
exec(compile(script.read_text(encoding='utf-8'),str(script),'exec'),globals())
