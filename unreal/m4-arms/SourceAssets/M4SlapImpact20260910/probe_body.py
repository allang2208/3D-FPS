import bpy,json,sys
from pathlib import Path
from mathutils.bvhtree import BVHTree
O=Path(__file__).parent
bpy.ops.wm.open_mainfile(filepath=str(O/'M4_Hand_MAT_Editable.blend'));r=bpy.data.objects['SK_M4_Infima'];s=bpy.context.scene;hand=bpy.data.objects['SK_Manny_Arms_Export'];body=bpy.data.objects['M4_M4 Body_Export'];stock=bpy.data.objects['M4_Stock Classic Unreal_Export']
report={}
for clip,end,side in [('reload_empty',162,'l')]:
 a=(bpy.data.actions.get('M4_MAT_'+clip+'.001') or bpy.data.actions['M4_MAT_'+clip]);r.animation_data.action=a;r.animation_data.action_slot=a.slots[0]
 ids={v.index for v in hand.data.vertices if sum(g.weight for g in v.groups if hand.vertex_groups[g.group].name.endswith('_'+side) and hand.vertex_groups[g.group].name.startswith(('hand','thumb','index','middle','ring','pinky')))>0.7};rows=[]
 for f in [k/2 for k in range(222,287)]:
  s.frame_set(int(f),subframe=f-int(f));bpy.context.view_layer.update();dg=bpy.context.evaluated_depsgraph_get();trees=[];hfaces=None
  for obj in [hand,body,stock]:
   ev=obj.evaluated_get(dg);m=ev.to_mesh();vs=[ev.matrix_world@v.co for v in m.vertices];fs=[list(p.vertices) for p in m.polygons if obj!=hand or any(i in ids for i in p.vertices)];trees.append(BVHTree.FromPolygons(vs,fs));ev.to_mesh_clear()
   if obj==hand:hfaces=fs
  counts={}
  for label,tree in zip(['body','stock'],trees[1:]):
   pairs=trees[0].overlap(tree);bones={}
   for face,_ in pairs:
    for vi in hfaces[face]:
     g=max(hand.data.vertices[vi].groups,key=lambda g:g.weight);n=hand.vertex_groups[g.group].name;bones[n]=bones.get(n,0)+1
   counts[label]={'pairs':len(pairs),'bones':bones}
  rows.append({'frame':f,**counts})
 report[clip]=rows
 (O/'body_contact_probe.json').write_text(json.dumps(report,indent=2));print(clip,'bad',[(v['frame'],v['body']['pairs'],v['stock']['pairs']) for v in rows if v['body']['pairs'] or v['stock']['pairs']],flush=True)
print('BODY_PROBE_DONE')
