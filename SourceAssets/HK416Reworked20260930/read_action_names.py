import bpy,json
from pathlib import Path
O=Path(__file__).parent;S=O.parent;files=[
'M4SlapImpact20260910/M4_Hand_MAT_Editable.blend',
'M4WrapGrip20260910/M4_Hand_MAT_Editable.blend',
'MannyGraspDonor20260912/Final/m4/vertical/M4_Vertical_VRE_Editable.blend',
'M4TacticalSprint20260915/Base/M4_TacticalSprint_Base_Editable.blend',
'M4TacticalSprint20260915/Vertical/M4_TacticalSprint_Vertical_Editable.blend',
'M4QuickMeleeReplica20260919/Base/M4_QuickCombat_Base_Editable.blend',
'M4QuickMeleeReplica20260919/Vertical/M4_QuickCombat_Vertical_Editable.blend']
out={}
for file in files:
    with bpy.data.libraries.load(str(S/file),link=False) as (src,dst):out[file]=[n for n in src.actions if n.startswith('M4_') or n.startswith('A_M4_')]
(O/'action_sources.json').write_text(json.dumps(out,indent=2));print(json.dumps(out),flush=True)
