from pathlib import Path
O=Path('D:/FPS3D/FPSGAME/SourceAssets/SVDCompletion20260923/UVRepair')
for JOB in ['skeletal','static0','static1']:
 exec(compile((O/'import_fixed_common.py').read_text(encoding='utf-8-sig'),str(O/'import_fixed_common.py'),'exec'))
exec(compile((O/'read_ue.py').read_text(encoding='utf-8-sig'),str(O/'read_ue.py'),'exec'))
print('SVD_UV_IMPORT_COMPLETE')
