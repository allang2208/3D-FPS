import bpy,json
from pathlib import Path
from mathutils import Matrix
p=Path(r'D:\FPS3D\FPSGAME\SourceAssets\FacelessReceptionist20261007')
bpy.ops.wm.open_mainfile(filepath=str(p/'Authoring/FacelessReceptionist_V01.blend'))
s=bpy.context.scene;s.frame_set(0)
dg=bpy.context.evaluated_depsgraph_get()
for o in s.objects:
 if o.type=='MESH':
  v=[o.matrix_world @ x.co for x in o.evaluated_get(dg).data.vertices]
  print('OBJECT_INFO '+json.dumps({'name':o.name,'vertices':len(v),'lo':[min(x[i] for x in v) for i in range(3)],'hi':[max(x[i] for x in v) for i in range(3)],'materials':[m.name for m in o.data.materials],'modifiers':[m.type for m in o.modifiers]}))
 if o.type=='ARMATURE':
  print('RIG_POSE '+json.dumps({'pose_position':o.data.pose_position,'changed_bones':[b.name for b in o.pose.bones if any(abs(b.matrix_basis[r][c]-(1 if r==c else 0))>1e-5 for r in range(4) for c in range(4))]}))
