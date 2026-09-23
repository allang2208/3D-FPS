"""Read motion/skin inputs needed to author the two requested actions."""
import bpy, json
from pathlib import Path
from mathutils import Matrix, Vector
O=Path(__file__).parent;R=O.parent
bpy.ops.wm.open_mainfile(filepath=str(R/'Reload16/PKM_base_Reload_Editable.blend'),use_scripts=False)
r=bpy.data.objects['PKM_Manny_Rig'];s=bpy.context.scene
rest={b.name:b.matrix_local.copy() for b in r.data.bones}
src=json.loads((R/'Reload16/sources.json').read_text())
out={'source':bpy.data.filepath,'fps':s.render.fps,'actions':[a.name for a in bpy.data.actions],
     'charge_parts':[{'name':g['name'],'min':g['min'],'max':g['max']} for g in src['pkm']['charge_geometry']]}
a=bpy.data.actions['PKM16_base_reload_empty'];r.animation_data.action=a;r.animation_data.action_slot=a.slots[0]
out['charge_samples']={}
for t in [4.82,5.0,5.13,5.32,5.50,5.55,5.70,6.26,6.60]:
    s.frame_set(int(t*120),subframe=(t*120)%1);bpy.context.view_layer.update()
    W=r.pose.bones['WPN_root'].matrix
    out['charge_samples'][str(t)]={n:list(map(list,W.inverted()@r.pose.bones[n].matrix)) for n in ['PKM_Charge','hand_r','lowerarm_r','upperarm_r','hand_l']}
H=rest['hand_r'];iv=H.inverted()
forward=(iv@rest['middle_01_r'].translation).normalized()
width=(iv.to_3x3()@(rest['index_01_r'].translation-rest['pinky_01_r'].translation)).normalized()
normal=forward.cross(width).normalized()
out['right_hand_semantics']={'forward':list(forward),'width':list(width),'normal':list(normal)}
out['right_rest_bone_axis']=list(iv.to_3x3()@(rest['hand_r'].translation-rest['lowerarm_r'].translation).normalized())
out['parents']={b.name:b.parent.name if b.parent else None for b in r.data.bones}
(O/'authoring_inputs.json').write_text(json.dumps(out,indent=2))
print('PKM31_AUTHOR_INPUTS',json.dumps({'fps':out['fps'],'charge_parts':out['charge_parts'],'right_hand':out['right_hand_semantics']}),flush=True)
