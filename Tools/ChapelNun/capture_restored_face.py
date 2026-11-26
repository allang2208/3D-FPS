from pathlib import Path
P=Path('D:/FPS3D/FPSGAME')
scope={'OUTPUT_DIR':P/'SourceAssets/ChapelNun20261115/FaceOriginalRestoreR6/EngineReadback'}
script=P/'Tools/ChapelNun/capture_face_diagnosis.py'
exec(compile(script.read_text(encoding='utf-8'),str(script),'exec'),scope)
