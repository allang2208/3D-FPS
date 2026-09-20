import bpy,json
from pathlib import Path
from mathutils import Vector
root=Path(r'D:\FPS3D\FPSGAME');out=root/'SourceAssets/RusticPickaxe20260919'
bpy.ops.wm.open_mainfile(filepath=str(root/'SourceAssets/AxeThumb20260919/Fixed/Axe_ThumbFix_Idle_Equip_Editable.blend'))
scene=bpy.context.scene; rig=bpy.data.objects['SK_Harvest_Axe_Rig'];a=bpy.data.actions['A_Harvest_Axe_Idle'];rig.animation_data.action=a;rig.animation_data.action_slot=a.slots[0];scene.frame_set(0);bpy.context.view_layer.update();wpn=rig.pose.bones['WPN_root'].matrix.copy();tool=bpy.data.objects['Harvest_Axe'];verts=[rig.data.bones['WPN_root'].matrix_local.inverted()@rig.matrix_world.inverted()@tool.matrix_world@v.co for v in tool.data.vertices]
report={'source_fps':scene.render.fps,'ready':[list(row) for row in wpn],'hands':{s:[list(row) for row in (wpn.inverted()@rig.pose.bones['hand_'+s].matrix)] for s in ('l','r')},'tool_bounds':[[min(p[i] for p in verts),max(p[i] for p in verts)] for i in range(3)],'source_clips':{a.name:list(a.frame_range) for a in bpy.data.actions},'sections':[]}
for z in (-.16,-.1,0,.06,.12,.18,.24):
 pts=[v for v in verts if abs(v.z-z)<.02]
 if pts:report['sections'].append({'z':z,'min':[min(p[i] for p in pts) for i in range(3)],'max':[max(p[i] for p in pts) for i in range(3)]})
bpy.ops.wm.open_mainfile(filepath=str(root/'SourceAssets/ProductionToolGrip20260913/Pickaxe_SingleHand_Editable.blend'))
rig=bpy.data.objects['SK_Harvest_Pickaxe_Rig'];scene=bpy.context.scene;report['old_pickaxe']={'fps':scene.render.fps,'clips':{a.name:list(a.frame_range) for a in bpy.data.actions if a.name.startswith('A_Harvest_Pickaxe')}}
(out/'source_dimensions.json').write_text(json.dumps(report,indent=2));print('SOURCE_DIMENSIONS',json.dumps(report),flush=True)
