import bpy,json,sys,itertools
from pathlib import Path
from mathutils.bvhtree import BVHTree
O=Path(__file__).parent;args=sys.argv[sys.argv.index('--')+1:];weapon,variant=args[:2];D=O/weapon/variant
build=json.loads((D/('animation_build.json' if weapon=='m4' else 'build.json')).read_text());report={}
for clip,info in build.items():
 if len(args)>2 and clip not in args[2:]:continue
 name=f'A_{weapon.upper()}_{"Canted" if weapon=="m4" else variant}_{clip}';bpy.ops.wm.open_mainfile(filepath=str(D/(name+'.blend')));s=bpy.context.scene;ob=bpy.data.objects['SK_Manny_Arms_Export'];groups={g.index:g.name for g in ob.vertex_groups};ob.data.calc_loop_triangles()
 dominant={v.index:max([(g.weight,groups[g.group]) for g in v.groups],default=(0,''))[1] for v in ob.data.vertices}
 faces=[];labels=[];digits=['index','middle','ring','pinky','thumb'];self_faces={}
 for tri in ob.data.loop_triangles:
  label=next((dominant[i].split('_')[0] for i in tri.vertices if dominant[i].endswith('_l') and dominant[i].startswith(tuple(digits))),'')
  if label:faces.append(tuple(tri.vertices));labels.append(label)
 for digit in digits:
  ids={v.index for v in ob.data.vertices if sum(g.weight for g in v.groups if groups[g.group].startswith(digit+'_') and groups[g.group].endswith('_l'))>.85};self_faces[digit]=[tuple(t.vertices) for t in ob.data.loop_triangles if all(i in ids for i in t.vertices)]
 end=info['frames']
 if 'reload' not in clip:frames=[0,end/2,end] if clip!='equip' else list(range(0,end+1,1 if weapon=='m4' else 4))
 elif weapon=='m4':frames=sorted(set([k/2 for k in range(57 if clip.startswith('drum') else 33)]+[k/2 for k in range((end-24)*2,end*2+1)]+[43,54,76,80,95]))
 else:
  start=380 if 'empty' in clip else 270
  frames=sorted(set([k/2 for k in range(89)]+[k/2 for k in range(start*2,(start+61)*2)]+[60,86,120,200,end]))
 parts=[x for x in s.objects if x.type=='MESH' and (x.name.startswith('CG_') if weapon=='m4' else x.name==f'SM_AKM_{variant}')]
 assert parts,variant
 for f in frames:
  s.frame_set(int(f),subframe=f%1);dg=bpy.context.evaluated_depsgraph_get();e=ob.evaluated_get(dg);m=e.to_mesh();vertices=[e.matrix_world@v.co for v in m.vertices];hand=BVHTree.FromPolygons(vertices,faces,all_triangles=True);hitids=set();bydigit={};hits={}
  for part in parts:
   pe=part.evaluated_get(dg);pm=pe.to_mesh();pm.calc_loop_triangles();tree=BVHTree.FromPolygons([pe.matrix_world@v.co for v in pm.vertices],[tuple(t.vertices) for t in pm.loop_triangles],all_triangles=True);cross=hand.overlap(tree)
   if cross:hits[part.name]=len(cross)
   for i,j in cross:hitids.add(i);bydigit[labels[i]]=bydigit.get(labels[i],0)+1
   pe.to_mesh_clear()
  trees={d:BVHTree.FromPolygons(vertices,fs,all_triangles=True) for d,fs in self_faces.items()};selfhits={a+'-'+b:len(trees[a].overlap(trees[b])) for a,b in itertools.combinations(trees,2)}
  report[f'{clip}_{f}']={'crossing_hand_triangles':len(hitids),'pairs_by_digit':bydigit,'parts':hits,'self':{k:v for k,v in selfhits.items() if v}}
  e.to_mesh_clear()
 (D/'geometry.json').write_text(json.dumps(report,indent=2));print('GEOMETRY_CLIP',weapon,variant,clip,len(frames),flush=True)
bad={k:v for k,v in report.items() if v['crossing_hand_triangles']};selfbad={k:v['self'] for k,v in report.items() if v['self']};print('GEOMETRY_RESULT',weapon,variant,'samples',len(report),'grip_bad',len(bad),'self_bad',len(selfbad),str(bad)[:2000],flush=True)
