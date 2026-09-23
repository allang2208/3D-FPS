import unreal as u
from pathlib import Path
import json,datetime
O=Path(__file__).parent
# Reimport only this gun and its private animations, via one bridge mutex batch.
world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world()
if world:
 raise RuntimeError('An active game world is using the editor; end PIE before the PKM asset replacement.')
for name in ['reimport_mesh.py','import_motion.py']:
 path=O/name;scope={'__file__':str(path),'__name__':'__main__'}
 exec(compile(path.read_text(encoding='utf-8'),str(path),'exec'),scope)
(O/'integration_complete.json').write_text(json.dumps({'saved_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'source':'Refinement06/PKM_Gameplay_Editable.blend','source_mtime':(O/'PKM_Gameplay_Editable.blend').stat().st_mtime,'mesh':'/Game/Weapons/PKMLowpoly20260922/SK_PKM_Manny','animation_clips':12,'gameplay_tested':False},indent=2))
print('PKM06 mesh, private skeleton and 12 animation clips saved. No gameplay test run.')
