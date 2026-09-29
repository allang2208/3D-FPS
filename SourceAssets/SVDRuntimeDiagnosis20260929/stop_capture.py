import unreal as u,gc,types,json
from pathlib import Path
rows=[]
for obj in gc.get_objects():
 if isinstance(obj,types.FunctionType) and obj.__name__=='_svd_tick' and 'SVDRuntimeDiagnosis20260929' in obj.__code__.co_filename:
  state=obj.__globals__;handle=state.get('_svd_capture_handle')
  try:
   if handle is not None:u.unregister_slate_post_tick_callback(handle)
   rows.append({'callback':obj.__code__.co_filename,'unregistered':handle is not None,'counts':state.get('_svd_counts')})
  except Exception as e:rows.append({'error':str(e)})
Path('D:/FPS3D/FPSGAME/SourceAssets/SVDRuntimeDiagnosis20260929/pause-cleanup.json').write_text(json.dumps(rows,indent=2))
print('PAUSE_CALLBACK_CLEANUP',rows)
