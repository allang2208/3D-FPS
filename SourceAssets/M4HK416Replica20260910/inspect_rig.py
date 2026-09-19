import bpy,json
from pathlib import Path
from mathutils import Matrix,Vector
OUT=Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath='D:/FPS3D/FPSGAME/SourceAssets/M4FoldingSights20260909/M4_FoldingSights_Editable.blend')
r=bpy.data.objects['SK_M4_Infima'];s=bpy.context.scene
a=bpy.data.actions['M4_idle'];r.animation_data_create();r.animation_data.action=a;r.animation_data.action_slot=a.slots[0];s.frame_set(0);bpy.context.view_layer.update()
def mat(m):return [list(row) for row in m]
report={'actions':[a.name for a in bpy.data.actions],'objects':[(o.name,o.type,o.hide_render) for o in r.children], 'camera':mat(s.camera.matrix_world),'rig':mat(r.matrix_world),'bones':{b.name:{'pose':mat(b.matrix),'rest':mat(b.bone.matrix_local),'parent':b.parent.name if b.parent else None} for b in r.pose.bones}}
(OUT/'target_rig.json').write_text(json.dumps(report,indent=2))
parts=json.loads(Path('D:/FPS3D/FPSGAME/SourceAssets/M4HK416AudioEmpty20260909/body_parts.json').read_text())
print('PARTS',[(p['id'] if 'id' in p else i, len(p['vertices']),{k:v for k,v in p.items() if k!='vertices'}) for i,p in enumerate(parts)])
print('TARGET_RIG_READY',report['objects'],report['actions'])
