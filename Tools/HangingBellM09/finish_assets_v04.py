import json,traceback
from pathlib import Path
base=Path('D:/FPS3D/FPSGAME/Tools/HangingBellM09')
record=Path('D:/FPS3D/FPSGAME/SourceAssets/HangingBellM09Meshy20261003/MotionV04/Records/finish_commandlet_v04.json')
result={'saved_steps':[],'tested':False}
try:
 M09_COMMANDLET=True
 for M09_STAGE in ['motion','fx']:
  exec(compile((base/'import_assets_v04.py').read_text(encoding='utf8'),'import_assets_v04.py','exec'))
  result['saved_steps'].append(M09_STAGE)
  record.write_text(json.dumps(result,indent=2),encoding='utf8')
 exec(compile((base/'author_room_v04.py').read_text(encoding='utf8'),'author_room_v04.py','exec'))
 result['saved_steps'].append('physics_and_map');result['complete']=True
except Exception:
 result['error']=traceback.format_exc()
 record.write_text(json.dumps(result,indent=2),encoding='utf8')
 raise
record.write_text(json.dumps(result,indent=2),encoding='utf8')
print('M09_PRODUCTION_SAVED')
