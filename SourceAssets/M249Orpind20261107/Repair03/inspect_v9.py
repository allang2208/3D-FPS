from pathlib import Path
import bpy,json,numpy as np
r=Path(__file__).resolve().parent
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=str(r/'PKM_V9_Arms.fbx'))
report=[]
for o in bpy.context.scene.objects:
 d=dict(name=o.name,type=o.type,matrix=[list(a) for a in o.matrix_world])
 if o.type=='MESH':
  v=np.array([o.matrix_world@x.co for x in o.data.vertices]);d.update(vertices=len(v),bounds=[v.min(0).tolist(),v.max(0).tolist()],morphs=[k.name for k in o.data.shape_keys.key_blocks] if o.data.shape_keys else [],materials=[m.name for m in o.data.materials])
 if o.type=='ARMATURE':
  d['bones']={n:list(o.matrix_world@o.data.bones[n].head_local) for n in ['upperarm_l','lowerarm_l','hand_l','upperarm_r','lowerarm_r','hand_r']}
 report.append(d)
(r/'v9_fbx_inspection.json').write_text(json.dumps(report,indent=2))
