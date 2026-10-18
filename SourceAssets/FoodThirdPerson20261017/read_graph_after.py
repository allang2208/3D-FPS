from pathlib import Path
import unreal as u
out=Path('D:/FPS3D/FPSGAME/SourceAssets/FoodThirdPerson20261017/graph_after.json')
if out.exists():raise RuntimeError('Use a separate revision for a new diagnostic')
u.SystemLibrary.execute_console_command(None,'fps.body.DiagnoseFood '+str(out))
if not out.exists():raise RuntimeError('Food graph diagnostic did not produce its receipt')
print('FOOD_GRAPH_AFTER_SAVED',out.stat().st_size)
