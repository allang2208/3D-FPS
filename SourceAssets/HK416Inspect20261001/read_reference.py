"""Read existing rifle motion and native grip poses for inspect authoring."""
import bpy, json
from pathlib import Path

O = Path(__file__).parent
S = O.parent
report = {}
for key, file, action in (
    ('akm', S/'AKMIntegration20260910/Native/AKM_MannyNative_Editable.blend', 'AKM_Native_inspect'),
    ('m16', S/'M16Gameplay20260919/M16_Manny_Editable.blend', 'M16_inspect'),
    ('hk416', S/'HK416Reworked20260930/HK416_Gameplay_Editable.blend', 'HK416_base_inspect'),
):
    bpy.ops.wm.open_mainfile(filepath=str(file))
    rig = bpy.data.objects['SK_M4_Infima']
    a = bpy.data.actions[action]
    rig.animation_data.action = a
    rig.animation_data.action_slot = a.slots[0]
    rows = []
    start, end = a.frame_range
    for f in (start, start+(end-start)*.2, start+(end-start)*.4, start+(end-start)*.6, start+(end-start)*.8, end):
        bpy.context.scene.frame_set(int(f), subframe=f % 1)
        bpy.context.view_layer.update()
        root = rig.pose.bones['WPN_root'].matrix.copy()
        row = {'frame': f, 'weapon': [list(v) for v in root]}
        for n in ('clavicle_l','upperarm_l','lowerarm_l','hand_l','clavicle_r','upperarm_r','lowerarm_r','hand_r'):
            row[n] = list((root.inverted() @ rig.pose.bones[n].matrix).translation)
        rows.append(row)
    report[key] = {'file':str(file),'action':action,'fps':bpy.context.scene.render.fps,'frames':list(a.frame_range),'poses':rows}
    if key == 'hk416':
        report['native_bones'] = {b.name: b.parent.name if b.parent else None for b in rig.data.bones}
(O/'reference.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('RIFLE_INSPECT_SOURCE_READ', flush=True)
