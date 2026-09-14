import bpy,json
from pathlib import Path
p=Path(__file__).parent
bpy.ops.wm.open_mainfile(filepath='D:/FPS3D/FPSGAME/SourceAssets/GASPTraversal20260910/Native/TraversalArms_Editable.blend')
rig=next(o for o in bpy.context.scene.objects if o.type=='ARMATURE')
data={'rig':rig.name,'world':[list(r) for r in rig.matrix_world], 'fps':bpy.context.scene.render.fps,
      'actions':[{ 'name':a.name,'range':list(a.frame_range)} for a in bpy.data.actions],
      'bones':{b.name:{'parent':b.parent.name if b.parent else '', 'matrix':[list(r) for r in b.matrix_local], 'head':list(b.head_local),'tail':list(b.tail_local)} for b in rig.data.bones},
      'meshes':[o.name for o in bpy.context.scene.objects if o.type=='MESH']}
(p/'source_pose.json').write_text(json.dumps(data,indent=2))
print(json.dumps({k:v for k,v in data.items() if k!='bones'},indent=2))
for n in ['clavicle_l','upperarm_l','lowerarm_l','hand_l','index_01_l','middle_01_l','pinky_01_l','thumb_01_l']:
 print(n,json.dumps(data['bones'][n]))
