import bpy,json
from pathlib import Path
from mathutils.bvhtree import BVHTree
O=Path(__file__).parent/'Native';bpy.ops.wm.open_mainfile(filepath=str(O/'AKM_MannyNative_Editable.blend'))
r=bpy.data.objects['SK_M4_Infima'];hand=bpy.data.objects['SK_Manny_Arms_Export'];mag=bpy.data.objects['AKMR_Magazine_Native']
ids={v.index for v in hand.data.vertices if sum(g.weight for g in v.groups if hand.vertex_groups[g.group].name.endswith('_l') and hand.vertex_groups[g.group].name.startswith(('hand','thumb','index','middle','ring','pinky')))>0.7}
report={}
for clip in ['idle','reload','reload_empty','equip']:
 a=bpy.data.actions['AKM_Native_'+clip];r.animation_data.action=a;r.animation_data.action_slot=a.slots[0];rows=[]
 for f in ([0] if clip=='idle' else range(0,{'reload':401,'reload_empty':516,'equip':328}[clip],6)):
  bpy.context.scene.frame_set(f);bpy.context.view_layer.update();dg=bpy.context.evaluated_depsgraph_get();trees=[];vertices=[]
  for obj in [hand,mag]:
   ev=obj.evaluated_get(dg);me=ev.to_mesh();vs=[ev.matrix_world@v.co for v in me.vertices];fs=[list(p.vertices) for p in me.polygons if obj!=hand or any(i in ids for i in p.vertices)];trees.append(BVHTree.FromPolygons(vs,fs));vertices.append(vs);ev.to_mesh_clear()
  distances=sorted(trees[1].find_nearest(vertices[0][i])[3] for i in ids)
  rows.append({'frame':f,'triangle_pairs':len(trees[0].overlap(trees[1])),'minimum_glove_to_mag_mm':distances[0]*1000,'nearest_20_mean_mm':sum(distances[:20])*50})
 report[clip]=rows
(O/'contact_probe.json').write_text(json.dumps(report,indent=2));print(json.dumps(report))
