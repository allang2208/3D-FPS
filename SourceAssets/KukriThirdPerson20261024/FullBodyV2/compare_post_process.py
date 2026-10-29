"""Isolate the actual mesh post-process; does not launch PIE or edit assets."""
import json
from pathlib import Path
import unreal as u
out=Path('C:/Users/allan/AppData/Local/Temp/KukriRuntimeDiagnosis20261024')
out.mkdir(parents=True,exist_ok=True)
world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
cfg='D:/FPS3D/FPSGAME/Content/ColdSteelData/player_body.json'
for name,tail in [('post-process-on',''),('post-process-off',' native-only')]:
    dest=out/(name+'.json')
    u.SystemLibrary.execute_console_command(world,'fps.body.DiagnoseKukriMotion "'+str(dest)+'" "'+cfg+'"'+tail)
    if not dest.exists():raise RuntimeError('No report: '+str(dest))
    data=json.loads(dest.read_text(encoding='utf-8-sig'))
    print(name+' rows='+str(len(data['rows']))+' errors='+str(data['errors']),flush=True)
