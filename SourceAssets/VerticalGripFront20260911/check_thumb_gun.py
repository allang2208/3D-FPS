import bpy,json,sys
from pathlib import Path
from mathutils.bvhtree import BVHTree
O=Path(__file__).parent;args=sys.argv[sys.argv.index('--')+1:];weapon,variant=args[:2];D=O/weapon/variant;report={}
for clip in ['idle','aim','reload','reload_empty','drum_reload','drum_reload_empty']:
 path=D/f'A_{weapon.upper()}_{variant.title() if weapon=="m4" else variant}_{clip}.blend'
 if not path.exists():continue
 bpy.ops.wm.open_mainfile(filepath=str(path));s=bpy.context.scene;ob=bpy.data.objects['SK_Manny_Arms_Export'];ob.data.calc_loop_triangles();groups={g.index:g.name for g in ob.vertex_groups};ids={v.index for v in ob.data.vertices if sum(g.weight for g in v.groups if groups[g.group].startswith('thumb_') and groups[g.group].endswith('_l'))>.5};faces=[tuple(t.vertices) for t in ob.data.loop_triangles if any(i in ids for i in t.vertices)]
 parts=[x for x in s.objects if x.type=='MESH' and x!=ob and not x.hide_render and not x.name.startswith(('VG_','PH_','SM_AKM_'))]
 end=s.frame_end
 frames=[0] if 'reload' not in clip else (sorted(set([k/2 for k in range(33)]+[k/2 for k in range((end-24)*2,end*2+1)])) if weapon=='m4' else sorted(set(list(range(43))+list(range(380 if 'empty' in clip else 270,(440 if 'empty' in clip else 330)+1)))))
 for f in frames:
  s.frame_set(int(f),subframe=f%1);dg=bpy.context.evaluated_depsgraph_get();e=ob.evaluated_get(dg);m=e.to_mesh();tree=BVHTree.FromPolygons([e.matrix_world@v.co for v in m.vertices],faces,all_triangles=True);hits={}
  for part in parts:
   pe=part.evaluated_get(dg);pm=pe.to_mesh();pm.calc_loop_triangles();gt=BVHTree.FromPolygons([pe.matrix_world@v.co for v in pm.vertices],[tuple(t.vertices) for t in pm.loop_triangles],all_triangles=True);cross=tree.overlap(gt)
   if cross:hits[part.name]=len(cross)
   pe.to_mesh_clear()
  e.to_mesh_clear();report[f'{clip}_{f}']=hits
  if hits:print('THUMB_GUN_HIT',weapon,variant,clip,f,hits,flush=True)
(D/'thumb_gun.json').write_text(json.dumps(report,indent=2));print('THUMB_GUN_RESULT',weapon,variant,len(report),sum(bool(x) for x in report.values()),flush=True)
