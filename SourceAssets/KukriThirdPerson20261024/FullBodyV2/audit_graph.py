"""Explicitly requested, headless native graph diagnosis; no PIE or rendering."""
import json
from pathlib import Path
import unreal as u
OUT=Path('D:/FPS3D/FPSGAME/SourceAssets/KukriThirdPerson20261024/FullBodyV2')
world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
report=OUT/'native-graph-after.json'
u.SystemLibrary.execute_console_command(world,'fps.body.DiagnoseKukriMotion "'+str(report)+'"')
if not report.exists():raise RuntimeError('Native diagnosis did not produce its report; rebuild Editor first')
data=json.loads(report.read_text(encoding='utf-8-sig'))
if data['errors']:raise RuntimeError(str(data['errors']))
if len(data['rows'])!=156:raise RuntimeError('Incomplete matrix: '+str(len(data['rows'])))
print('KUKRI_NATIVE_GRAPH_COMPLETE '+str(len(data['rows'])),flush=True)
