import bpy,json,itertools
from pathlib import Path
from mathutils.bvhtree import BVHTree
O=Path(__file__).parent;report={}
for variant in ['vertical','prism']:
 d=O/variant;f=d/'self_contact.json'
 if not f.exists():continue
 current=json.loads(f.read_text());out={}
 for clip,info in json.loads((d/'animation_build.json').read_text()).items():
  keys=[k for k,row in current.items() if k.rsplit('_',1)[0]==clip and any(row.values())]
  if not keys:continue
  bpy.ops.wm.open_mainfile(filepath=info['source']);s=bpy.context.scene;r=bpy.data.objects['SK_M4_Infima'];a=bpy.data.actions[info['action']];r.animation_data.action=a;r.animation_data.action_slot=a.slots[0];ob=bpy.data.objects['SK_Manny_Arms_Export'];groups={g.index:g.name for g in ob.vertex_groups};ob.data.calc_loop_triangles();faces={}
  for digit in ['index','middle','ring','pinky','thumb']:
   ids={v.index for v in ob.data.vertices if sum(g.weight for g in v.groups if groups[g.group].startswith(digit+'_') and groups[g.group].endswith('_l'))>.85};faces[digit]=[tuple(t.vertices) for t in ob.data.loop_triangles if all(i in ids for i in t.vertices)]
  for k in keys:
   f=float(k.rsplit('_',1)[1]);s.frame_set(int(f),subframe=f%1);e=ob.evaluated_get(bpy.context.evaluated_depsgraph_get());m=e.to_mesh();v=[e.matrix_world@x.co for x in m.vertices];trees={d:BVHTree.FromPolygons(v,fs,all_triangles=True) for d,fs in faces.items()};counts={a+'-'+b:len(trees[a].overlap(trees[b])) for a,b in itertools.combinations(trees,2)};out[k]={'source':counts,'current':current[k]};e.to_mesh_clear()
 report[variant]=out
(O/'preserved_source_self_contacts.json').write_text(json.dumps(report,indent=2));print('SELF_SOURCE_COMPARISON', {v:{'sample_count':len(rows),'source_had_contact':sum(any(r['source'].values()) for r in rows.values()),'new_only':sum(not any(r['source'].values()) for r in rows.values())} for v,rows in report.items()})
