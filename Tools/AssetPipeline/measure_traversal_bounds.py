"""Measure deformed native geometry, in the FBX/UE axes, for traversal culling."""
import bpy,json
from pathlib import Path
from mathutils import Vector
out=Path('D:/FPS3D/FPSGAME/SourceAssets/GASPTraversal20260910/Native')
bpy.ops.wm.open_mainfile(filepath=str(out/'TraversalArms_Editable.blend'))
r=bpy.data.objects['SK_M4_Infima'];o=bpy.data.objects['SK_Manny_Arms_Export'];s=bpy.context.scene
lo=[float('inf')]*3;hi=[-float('inf')]*3
for name in ['Vault','Mantle','Climb']:
 a=bpy.data.actions['Traversal_'+name];r.animation_data.action=a;r.animation_data.action_slot=a.slots[0]
 for f in range(int(a.frame_range[0]),int(a.frame_range[1])+1,2):
  s.frame_set(f);bpy.context.view_layer.update();ev=o.evaluated_get(bpy.context.evaluated_depsgraph_get());m=ev.to_mesh()
  for v in m.vertices:
   p=ev.matrix_world@v.co;u=(p.x*100,-p.y*100,p.z*100)
   for i in range(3):lo[i]=min(lo[i],u[i]);hi[i]=max(hi[i],u[i])
  ev.to_mesh_clear()
(out/'bounds.json').write_text(json.dumps({'min':[v-10 for v in lo],'max':[v+10 for v in hi],'margin_cm':10},indent=2))
print('TRAVERSAL_BOUNDS',lo,hi)
