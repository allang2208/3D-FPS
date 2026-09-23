from pathlib import Path
O=Path('D:/FPS3D/FPSGAME/SourceAssets/SVDCompletion20260923')
for JOB in ['animations_1','animations_2']:
 exec(compile((O/'import_common.py').read_text(encoding='utf-8-sig'),str(O/'import_common.py'),'exec'))
exec(compile((O/'check_assets.py').read_text(encoding='utf-8-sig'),str(O/'check_assets.py'),'exec'))
