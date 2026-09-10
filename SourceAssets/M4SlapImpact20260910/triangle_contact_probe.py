import bpy,json
from pathlib import Path
from mathutils.bvhtree import BVHTree
O=Path(__file__).parent
bpy.ops.wm.open_mainfile(filepath=str(O/'M4_Hand_MAT_Editable.blend'));r=bpy.data.objects['SK_M4_Infima'];hand=bpy.data.objects['SK_Manny_Arms_Export'];mag=next(o for o in r.children if o.type=='MESH' and 'Magazine' in o.name)
ids={v.index for v in hand.data.vertices if sum(g.weight for g in v.groups if hand.vertex_groups[g.group].name.endswith('_l') and hand.vertex_groups[g.group].name.startswith(('hand','thumb','index','middle','ring','pinky')))>0.7}
report={}
for clip,frames in [('reload_empty',[k/2 for k in range(222,287)])]:
 a=(bpy.data.actions.get('M4_MAT_'+clip+'.001') or bpy.data.actions['M4_MAT_'+clip]);r.animation_data.action=a;r.animation_data.action_slot=a.slots[0];rows=[]
 for f in frames:
  bpy.context.scene.frame_set(int(f),subframe=f-int(f));bpy.context.view_layer.update();dg=bpy.context.evaluated_depsgraph_get();trees=[];polys=[];verts=[]
  for obj in [hand,mag]:
   ev=obj.evaluated_get(dg);m=ev.to_mesh();vs=[ev.matrix_world@v.co for v in m.vertices];fs=[list(p.vertices) for p in m.polygons if obj!=hand or any(i in ids for i in p.vertices)];trees.append(BVHTree.FromPolygons(vs,fs));verts.append(vs);polys.append(fs);ev.to_mesh_clear()
  overlaps=trees[0].overlap(trees[1]);counts={}
  for face,_ in overlaps:
   for vi in polys[0][face]:
    g=max(hand.data.vertices[vi].groups,key=lambda g:g.weight);n=hand.vertex_groups[g.group].name;counts[n]=counts.get(n,0)+1
  print(clip,f,counts)
  rows.append({'frame':f,'triangle_pairs':len(overlaps)})
 report[clip]=rows
(O/'triangle_contact_probe.json').write_text(json.dumps(report,indent=2));print(report)
