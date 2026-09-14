"""Finish the initial V12 editable file; imported heavy actions stay unchanged."""
import bpy,sys,json
from pathlib import Path
P=Path(__file__).parent;sys.path.insert(0,str(P))
from action_timebase import rescale_action
path=P/'AzureRunesword_Manny_Editable.blend'
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.open_mainfile(filepath=str(path))
report=json.loads((P/'authoring.json').read_text(encoding='utf-8'))
if not report.get('retained_actions_at_480hz'):
    for action in bpy.data.actions:
        if action.name not in ['A_RuneSword_HeavyCharge','A_RuneSword_HeavyRelease']:
            rescale_action(action,2.)
    bpy.ops.wm.save_as_mainfile(filepath=str(path))
    report['retained_actions_at_480hz']=True
    (P/'authoring.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('RUNESWORD_V12_SOURCE_FINISHED',flush=True)
