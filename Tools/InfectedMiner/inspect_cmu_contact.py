import bpy,json,math
from pathlib import Path
from mathutils import Vector
R=Path('D:/FPS3D/FPSGAME/SourceAssets/InfectedMiner20260912');O=R/'Candidates/CMU02_07'
bpy.ops.wm.open_mainfile(filepath=str(O/'InfectedMiner_Editable.blend'));s=bpy.context.scene;r=bpy.data.objects['MinerRig'];a=bpy.data.actions['A_Miner_Attack'];r.animation_data.action=a;r.animation_data.action_slot=a.slots[0];head=bpy.data.objects['Pickaxe_ForgedHead'];rows=[]
for f in range(1,74):
    s.frame_set(f);bpy.context.view_layer.update();e=head.evaluated_get(bpy.context.evaluated_depsgraph_get());m=e.to_mesh();p=[e.matrix_world@v.co for v in m.vertices];e.to_mesh_clear();front=min(p,key=lambda p:p.y);w=(r.matrix_world@r.pose.bones['hand_l'].matrix).translation
    rows.append({'frame':f,'time':(f-1)/30,'head_front':list(front),'head_center':list(sum(p,Vector())/len(p)),'wrist':list(w)})
(O/'tool-contact-analysis.json').write_text(json.dumps(rows,indent=2));print('CMU_TOOL_CONTACT '+json.dumps([x for x in rows if x['frame']%3==1]))
