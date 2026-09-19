import bpy,json
from pathlib import Path
from mathutils.bvhtree import BVHTree
O=Path(__file__).parent
bpy.ops.wm.open_mainfile(filepath=str(O/'M4_DrumContact_Editable.blend'))
r=bpy.data.objects['SK_M4_Infima'];s=bpy.context.scene
body=bpy.data.objects['M4_M4 Body_Export']; drum=bpy.data.objects['SM_M4_LargeDrum']
rows=[]
baseline=set()
for clip,frames in [('reload',[0,*[x/4 for x in range(65*4,101*4)]]),('reload_empty',[0,*[x/4 for x in range(45*4,90*4)]])]:
 a=bpy.data.actions['A_M4_DrumContact_'+clip];r.animation_data.action=a;r.animation_data.action_slot=a.slots[0]
 for f in frames:
  s.frame_set(int(f),subframe=f%1);bpy.context.view_layer.update();dg=bpy.context.evaluated_depsgraph_get();trees=[];meshes=[];evs=[]
  for obj in [drum,body]:
   ev=obj.evaluated_get(dg);m=ev.to_mesh();m.calc_loop_triangles();vs=[ev.matrix_world@v.co for v in m.vertices];fs=[tuple(t.vertices) for t in m.loop_triangles];trees.append(BVHTree.FromPolygons(vs,fs,all_triangles=True));meshes.append((vs,fs));evs.append(ev)
  pairs=trees[0].overlap(trees[1]);ids={j for i,j in pairs}; pts=[meshes[1][0][v] for j in ids for v in meshes[1][1][j]]
  
  if f==0:baseline=ids.copy()
  row={'clip':clip,'frame':f,'triangle_pairs':len(pairs),'new_body_triangles':len(ids-baseline)}
  if pts:row['body_local_bounds']=[[min((body.matrix_world.inverted()@v)[k] for v in pts) for k in range(3)],[max((body.matrix_world.inverted()@v)[k] for v in pts) for k in range(3)]]
  rows.append(row)
  for ev in evs:ev.to_mesh_clear()
(O/'body_drum_intersections.json').write_text(json.dumps(rows,indent=2))
print('MAX_NEW_BODY_TRIANGLES',max(x['new_body_triangles'] for x in rows)); assert max(x['new_body_triangles'] for x in rows)==0
