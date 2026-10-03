"""Resume only the unsaved production stages. No tests."""
import unreal as u,json,traceback
from pathlib import Path
base=Path('D:/FPS3D/FPSGAME/Tools/HangingBellM09')
record_root=Path('D:/FPS3D/FPSGAME/SourceAssets/HangingBellM09Meshy20261003/MotionV04/Records')
record=record_root/'finish_commandlet_v04.json'
try:
 assets=json.loads((record_root/'ue_assets_v04.json').read_text(encoding='utf8'))
 # All nine imports saved before the earlier skeleton lock. Close that save boundary.
 mesh=u.load_asset('/Game/Monsters/HangingBellM09/V04/SK_M09')
 if not u.EditorAssetLibrary.save_loaded_asset(mesh.skeleton,False):raise RuntimeError('M09 skeleton save still blocked')
 if 'motion' not in assets['stages']:assets['stages'].append('motion')
 (record_root/'ue_assets_v04.json').write_text(json.dumps(assets,indent=2,ensure_ascii=False),encoding='utf8')
 exec(compile((base/'author_room_v04.py').read_text(encoding='utf8'),'author_room_v04.py','exec'))
 result={'saved_steps':['mesh','materials','motion','fx','physics_and_map'],'complete':True,'tested':False}
except Exception:
 result={'complete':False,'error':traceback.format_exc(),'tested':False}
 record.write_text(json.dumps(result,indent=2),encoding='utf8')
 raise
record.write_text(json.dumps(result,indent=2),encoding='utf8')
print('M09_PRODUCTION_SAVED')
