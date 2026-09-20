"""Read existing author geometry needed to fit the recovery paths; no rendering."""
import bpy,json,math
from pathlib import Path
from mathutils import Vector
P=Path(__file__).parent;S=P.parents[1]
def open_file(path):
    try:bpy.ops.wm.open_mainfile(filepath=str(path))
    except RuntimeError as e:
        if 'Missing library override hierarchy root data' not in str(e):raise
report={}
for weapon in ('M1911','DW715'):
    report[weapon]={}
    for side in ('r','l'):
        path=S/'PistolDualWield20260914/NaturalAimV3'/weapon/side/f'{weapon}_{side}_Dual_Editable.blend'
        open_file(path);rig=bpy.data.objects['SK_M1911_Manny' if weapon=='M1911' else 'SK_DW715_Manny']
        rig.animation_data.action=bpy.data.actions[f'Dual_{weapon}_{side}_idle'];rig.animation_data.action_slot=rig.animation_data.action.slots[0]
        bpy.context.scene.frame_set(0);bpy.context.view_layer.update()
        arm=bpy.data.objects['Manny_Dual_'+side];f='lowerarm_'+side;h='hand_'+side
        origin=rig.data.bones[f].matrix_local.translation;axis=rig.data.bones[h].matrix_local.translation-origin
        names=[f,'lowerarm_twist_01_'+side,'lowerarm_twist_02_'+side]
        values={n:[] for n in names};coords=rig.matrix_world.inverted()@arm.matrix_world
        for v in arm.data.vertices:
            if not v.groups:continue
            group=max(v.groups,key=lambda g:g.weight);n=arm.vertex_groups[group.group].name
            if n in values:values[n].append((coords@v.co-origin).dot(axis)/axis.length_squared)
        stations={n:max(0.,min(1.,sorted(v)[len(v)//2])) if v else 0. for n,v in values.items()};stations[f]=0.
        report[weapon][side]={'skin_stations':stations,'idle_positions':{n:list(rig.pose.bones[n].matrix.translation) for n in ['upperarm_'+side,f,h,'index_02_'+side,'WPN_root']}}
(P/'author_geometry.json').write_text(json.dumps(report,indent=2))
print('RECOVERY_AUTHOR_GEOMETRY '+json.dumps(report),flush=True)
