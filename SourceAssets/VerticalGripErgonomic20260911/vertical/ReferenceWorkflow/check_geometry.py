import bpy,json,math,sys
from pathlib import Path
from mathutils.bvhtree import BVHTree
from mathutils import Matrix
O=Path(__file__).parent;report={}
checks=[('idle',[0]),('reload',[0,2,4,6,8,10,12,16,102,110,114,118,122,126]),('equip',[0,18,38])]
if '--full' in sys.argv:
 checks=[('idle',[0,90,180]),('aim',[0,2]),('fire',[0,23,46]),('aim_fire',[0,23,46]),('equip',list(range(39)))]
 for clip,end in [('reload',126),('reload_empty',162),('drum_reload',126),('drum_reload_empty',148)]:checks.append((clip,sorted(set([k/2 for k in range(57 if clip.startswith('drum') else 33)]+[k/2 for k in range((end-24)*2,end*2+1)]+[43,54,76,80,95]))))
for clip,frames in checks:
 bpy.ops.wm.open_mainfile(filepath=str(O/('A_M4_Foregrip_'+clip+'.blend')));r=bpy.data.objects['SK_M4_Infima'];s=bpy.context.scene
 a=bpy.data.actions['A_M4_Foregrip_'+clip];r.animation_data.action=a;r.animation_data.action_slot=a.slots[0]
 ob=bpy.data.objects['SK_Manny_Arms_Export'];groups={g.index:g.name for g in ob.vertex_groups}
 finger={v.index:max([(g.weight,groups[g.group]) for g in v.groups if groups[g.group].endswith('_l')],default=(0,''))[1] for v in ob.data.vertices}
 for f in frames:
  s.frame_set(int(f),subframe=f%1);dg=bpy.context.evaluated_depsgraph_get();ev=ob.evaluated_get(dg);m=ev.to_mesh();m.calc_loop_triangles();v=[ev.matrix_world@x.co for x in m.vertices];faces=[];labels=[]
  for t in m.loop_triangles:
   label=next((finger[i].split('_')[0] for i in t.vertices if finger[i].startswith(('index','middle','ring','pinky','thumb'))),'')
   if label:faces.append(tuple(t.vertices));labels.append(label)
  hand=BVHTree.FromPolygons(v,faces,all_triangles=True);counts={};pairs=set();parts={}
  for grip in [x for x in s.objects if x.name.startswith('FG_')]:
   e=grip.evaluated_get(dg);gm=e.to_mesh();gm.calc_loop_triangles();tree=BVHTree.FromPolygons([e.matrix_world@x.co for x in gm.vertices],[tuple(t.vertices) for t in gm.loop_triangles],all_triangles=True)
   hit=hand.overlap(tree)
   if hit:parts[grip.name]=len(hit)
   for i,j in hit:pairs.add(i);counts[labels[i]]=counts.get(labels[i],0)+1
   e.to_mesh_clear()
  inv=(r.pose.bones['WPN_root'].matrix@Matrix(json.loads((O/'fit_pose.json').read_text())['grip_in_root'])).inverted()
  points=[inv@v[j] for i in pairs for j in faces[i]]
  bbox=[[min(p[k] for p in points),max(p[k] for p in points)] for k in range(3)] if points else None
  report[f'{clip}_{f}']={'crossing_hand_triangles':len(pairs),'pairs_by_digit':counts,'parts':parts,'contact_bbox_grip':bbox}
  ev.to_mesh_clear()
 (O/('geometry_contact_full.json' if '--full' in sys.argv else 'geometry_contact.json')).write_text(json.dumps(report,indent=2))
print('GEOMETRY_CHECK_DONE',report)
