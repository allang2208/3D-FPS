from pathlib import Path
import base64
import unreal as u
OUT=Path(__file__).resolve().parent
s=u.get_default_object(u.SlateInspectorToolset)
print('WINDOWS '+s.call_method('Windows',('list',-1)))
observer=s.call_method('Observe',('',24))
print('OBSERVER '+observer)
snapshot=s.call_method('Snapshot',('',80,False))
(OUT/'slate_snapshot.txt').write_text(snapshot,encoding='utf-8')
print('SLATE '+snapshot[:5000])
shot=s.call_method('Screenshot',('w1',))
(OUT/'live_screen.png').write_bytes(base64.b64decode(shot.data))
s.call_method('Unobserve',(observer,))
print('SCREEN_SAVED '+str(OUT/'live_screen.png'))
