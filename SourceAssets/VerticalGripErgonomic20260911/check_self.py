import bpy,json,itertools,sys
from pathlib import Path
from mathutils.bvhtree import BVHTree
O=Path(__file__).parent
for variant in sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else ['vertical','prism']:
 d=O/variant;title=variant.title();report={}
 for clip,end in [('idle',180),('reload',126),('reload_empty',162),('drum_reload',126),('drum_reload_empty',148)]:
  bpy.ops.wm.open_mainfile(filepath=str(d/f'A_M4_{title}_{clip}.blend'));s=bpy.context.scene;ob=bpy.data.objects['SK_Manny_Arms_Export'];groups={g.index:g.name for g in ob.vertex_groups};ob.data.calc_loop_triangles();faces={}
  for digit in ['index','middle','ring','pinky','thumb']:
   ids={v.index for v in ob.data.vertices if sum(g.weight for g in v.groups if groups[g.group].startswith(digit+'_') and groups[g.group].endswith('_l'))>.85};faces[digit]=[tuple(t.vertices) for t in ob.data.loop_triangles if all(i in ids for i in t.vertices)]
  frames=[0,90,180] if clip=='idle' else [k/2 for k in range(57 if clip.startswith('drum') else 33)]+[k/2 for k in range((end-24)*2,end*2+1)]
  for f in frames:
   s.frame_set(int(f),subframe=f%1);e=ob.evaluated_get(bpy.context.evaluated_depsgraph_get());m=e.to_mesh();v=[e.matrix_world@x.co for x in m.vertices];trees={d:BVHTree.FromPolygons(v,fs,all_triangles=True) for d,fs in faces.items()};report[f'{clip}_{f}']={a+'-'+b:len(trees[a].overlap(trees[b])) for a,b in itertools.combinations(trees,2)};e.to_mesh_clear()
  print('SELF_CLIP_DONE',variant,clip,flush=True)
 (d/'self_contact.json').write_text(json.dumps(report,indent=2));bad={k:v for k,v in report.items() if any(v.values())};print('SELF_RESULT',variant,'samples',len(report),'bad',len(bad),str(bad)[:4000],flush=True)
