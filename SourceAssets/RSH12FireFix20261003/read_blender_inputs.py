import bpy,json
from pathlib import Path
O=Path(__file__).parent;SA=O.parent/'RSH12SingleAction20261003'
def summary(r):
 result=dict(matrix_world=[list(v) for v in r.matrix_world],pose_position=r.data.pose_position,bones=len(r.data.bones),frames=[])
 for f in (0,3,8,36,72,120):
  bpy.context.scene.frame_set(f);bpy.context.view_layer.update()
  result['frames'].append(dict(frame=f,bones={n:dict(scale=list(r.pose.bones[n].scale),matrix=[list(v) for v in r.pose.bones[n].matrix],rest=[list(v) for v in r.data.bones[n].matrix_local]) for n in ('root','hand_r','hand_l','WPN_root') if n in r.data.bones}))
 return result
out={}
for family in ('single','r','l'):
 file='A_RSH12_'+('' if family=='single' else family+'_')+'fire'
 bpy.ops.wm.open_mainfile(filepath=str(SA/family/(file+'_Editable.blend')))
 r=next(o for o in bpy.data.objects if o.type=='ARMATURE');author=summary(r)
 bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.fbx(filepath=str(SA/family/(file+'.fbx')))
 r=next(o for o in bpy.data.objects if o.type=='ARMATURE');imported=summary(r)
 out[family]=dict(authored=author,fbx_reimport=imported)
(O/'blender_before.json').write_text(json.dumps(out,indent=2))
for family,data in out.items():
 print(family)
 for stage,rig in data.items():
  print(stage,'pose_position',rig['pose_position'],'matrix_world',rig['matrix_world'])
  print('frame0',[(n,b['scale'],[b['matrix'][i][3] for i in range(3)]) for n,b in rig['frames'][0]['bones'].items()])
