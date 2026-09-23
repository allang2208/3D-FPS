"""Read PKM's own five accepted grips; no donor shoulder/palm transforms."""
import bpy, json
from pathlib import Path
O=Path(__file__).parent; R=O.parent
result={}
for family in ['base','vertical','canted','prism','angled']:
    source=R/'Feed13/PKM_FiringFeed_Editable.blend' if family=='base' else R/'GripContact15'/f'PKM_{family}_Editable.blend'
    bpy.ops.wm.open_mainfile(filepath=str(source),use_scripts=False)
    r=bpy.data.objects['PKM_Manny_Rig']; s=bpy.context.scene
    name='PKM_Game_idle_Wrist12' if family=='base' else f'A_PKM_{family}_idle_Contact15'
    a=bpy.data.actions[name]; r.animation_data.action=a; r.animation_data.action_slot=a.slots[0]
    r.data.pose_position='POSE'; s.frame_set(0); bpy.context.view_layer.update()
    result[family]={'source':str(source),'idle_action':name,
        'idle':{b.name:list(map(list,b.matrix)) for b in r.pose.bones},
        'rest':{b.name:list(map(list,b.matrix_local)) for b in r.data.bones},
        'parents':{b.name:b.parent.name if b.parent else None for b in r.data.bones}}
(O/'grips.json').write_text(json.dumps(result,indent=2))
print('PKM24_GRIPS_READ',flush=True)
