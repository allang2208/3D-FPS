from pathlib import Path
P=Path('D:/FPS3D/FPSGAME');script=P/'Tools/ChapelNun/diagnose_original_face.py'
code=script.read_text(encoding='utf-8').replace("O=N/'FaceDiagnosisR1'","O=N/'FaceOriginalRestoreR6/SourceComparison'").replace("N/'RefinementR4/Authored/head.json'","N/'FaceOriginalRestoreR6/Authored/head.json'")
exec(compile(code,str(script),'exec'))
