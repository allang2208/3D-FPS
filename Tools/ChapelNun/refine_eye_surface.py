from pathlib import Path
code=Path('D:/FPS3D/FPSGAME/Tools/ChapelNun/save_head_quality.py').read_text(encoding='utf-8-sig')
exec(compile(code.split('mats=[face_material')[0],'<head quality materials>','exec'))
face_material('M_Nun_EyeSurface','eye')
print('NUN_EYE_SURFACE_SAVED',flush=True)
