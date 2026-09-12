"""Record sampled glove/grip contacts; small handstop overlap is user-authorized."""
import bpy,sys,json,itertools
from pathlib import Path
from mathutils.bvhtree import BVHTree
sys.path.insert(0,str(Path(__file__).parent));from case import *
args=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []
for w,v in FAMILIES:
 if args and [w,v]!=args[:2]:continue
 report={};D=OUT/w/v
 for clip in ['idle','aim','equip','reload','reload_empty']:
  meta=metadata(w,v)[clip];end=meta['frames'];bpy.ops.wm.open_mainfile(filepath=str(D/(prefix(w,v)+clip+'.blend')));s=bpy.context.scene
  ob=bpy.data.objects['SK_Manny_Arms_Export'];groups={g.index:g.name for g in ob.vertex_groups};ob.data.calc_loop_triangles();digits=['thumb','index','middle','ring','pinky']
  dominant={x.index:max([(g.weight,groups[g.group]) for g in x.groups],default=(0,''))[1] for x in ob.data.vertices};faces=[];labels=[];self_faces={}
  for t in ob.data.loop_triangles:
   label=next((dominant[i].split('_')[0] for i in t.vertices if dominant[i].endswith('_l') and dominant[i].startswith(tuple(digits))),'')
   if label:faces.append(tuple(t.vertices));labels.append(label)
  for digit in digits:
   ids={x.index for x in ob.data.vertices if sum(g.weight for g in x.groups if groups[g.group].startswith(digit+'_') and groups[g.group].endswith('_l'))>.85}
   self_faces[digit]=[tuple(t.vertices) for t in ob.data.loop_triangles if all(i in ids for i in t.vertices)]
  parts=[x for x in s.objects if x.type=='MESH' and (x.name.startswith('CG_' if v=='canted' else 'PH_') if w=='m4' else x.name.startswith('SM_AKM_'+v))];assert parts,(w,v)
  if 'reload' in clip:
   start=380 if 'empty' in clip else 270
   frames=sorted(set(list(range(0,17,2))+list(range(end-24,end+1,2)))) if w=='m4' else sorted(set(list(range(0,43,4))+list(range(start,start+61,4))+[end]))
  elif clip=='equip':frames=[k*end/8 for k in range(9)]
  else:frames=[0,end/2,end]
  for f in frames:
   s.frame_set(int(f),subframe=f%1);dg=bpy.context.evaluated_depsgraph_get();e=ob.evaluated_get(dg);m=e.to_mesh();vertices=[e.matrix_world@x.co for x in m.vertices]
   hand=BVHTree.FromPolygons(vertices,faces,all_triangles=True);hitids=set();bydigit={};part_hits={}
   for part in parts:
    pe=part.evaluated_get(dg);pm=pe.to_mesh();pm.calc_loop_triangles();tree=BVHTree.FromPolygons([pe.matrix_world@x.co for x in pm.vertices],[tuple(t.vertices) for t in pm.loop_triangles],all_triangles=True);cross=hand.overlap(tree)
    if cross:part_hits[part.name]=len(cross)
    for i,j in cross:hitids.add(i);bydigit[labels[i]]=bydigit.get(labels[i],0)+1
    pe.to_mesh_clear()
   trees={d:BVHTree.FromPolygons(vertices,fs,all_triangles=True) for d,fs in self_faces.items()};selfhits={a+'-'+b:len(trees[a].overlap(trees[b])) for a,b in itertools.combinations(trees,2)}
   report[f'{clip}_{f}']={'crossing_hand_triangles':len(hitids),'pairs_by_digit':bydigit,'parts':part_hits,'self':{k:n for k,n in selfhits.items() if n}};e.to_mesh_clear()
  (D/'geometry.json').write_text(json.dumps(report,indent=2));print('GEOMETRY_SAMPLED',w,v,clip,len(frames),flush=True)
 print('GEOMETRY_REPORT',w,v,len(report),'grip_contact',sum(bool(x['crossing_hand_triangles']) for x in report.values()),'self_contact',sum(bool(x['self']) for x in report.values()),flush=True)
