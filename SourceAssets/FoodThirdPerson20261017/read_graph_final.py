from pathlib import Path
import unreal as u
out=Path('D:/FPS3D/FPSGAME/SourceAssets/FoodThirdPerson20261017/graph_final.json')
if out.exists():raise RuntimeError('Preserve final diagnostic output')
u.SystemLibrary.execute_console_command(None,'fps.body.DiagnoseFood '+str(out))
if not out.exists():raise RuntimeError('Food graph diagnostic did not produce its receipt')
print('FOOD_GRAPH_FINAL_SAVED',out.stat().st_size)
