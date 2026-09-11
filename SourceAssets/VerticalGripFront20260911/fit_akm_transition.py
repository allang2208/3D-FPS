"""Fit a small thumb-base swing inside the AKM release blend, preserving frame 42 onward."""
import bpy,json,math,sys,itertools
from pathlib import Path
from mathutils import Quaternion,Vector
from mathutils.bvhtree import BVHTree
O=Path(__file__).parent;variant=sys.argv[sys.argv.index('--')+1];D=O/'akm'/variant
clips=['reload','reload_empty'] if variant=='vertical' else ['reload','reload_empty','drum_reload','drum_reload_empty']
reference=json.loads((O/('before_thumb_gun_'+variant+'.json')).read_text())
start,peak,end=(30,36,42) if variant=='vertical' else (25,31,40)
def smooth(x):x=max(0,min(1,x));return x*x*(3-2*x)
def weight(f):return smooth((f-start)/(peak-start)) if f<=peak else 1-smooth((f-peak)/(end-peak))
def setup(clip):
 bpy.ops.wm.open_mainfile(filepath=str(D/f'A_AKM_{variant}_{clip}.blend'));s=bpy.context.scene;r=bpy.data.objects['SK_M4_Infima'];ob=bpy.data.objects['SK_Manny_Arms_Export'];ob.data.calc_loop_triangles();groups={g.index:g.name for g in ob.vertex_groups};ids={v.index for v in ob.data.vertices if sum(g.weight for g in v.groups if groups[g.group].startswith('thumb_') and groups[g.group].endswith('_l'))>.5};faces=[tuple(t.vertices) for t in ob.data.loop_triangles if any(i in ids for i in t.vertices)];parts=[x for x in s.objects if x.type=='MESH' and x!=ob and not x.hide_render];cache={}
 for f in range(start,end+1):
  s.frame_set(f);q=r.pose.bones['thumb_01_l'].rotation_quaternion.copy();dg=bpy.context.evaluated_depsgraph_get();solids=[]
  for part in parts:
   if part.name.startswith('SM_AKM_drum'):continue
   pe=part.evaluated_get(dg);pm=pe.to_mesh();pm.calc_loop_triangles();solids.append((part.name,BVHTree.FromPolygons([pe.matrix_world@v.co for v in pm.vertices],[tuple(t.vertices) for t in pm.loop_triangles],all_triangles=True)));pe.to_mesh_clear()
  cache[f]=(q,solids)
 return s,r,ob,faces,cache
def check(state,clip,axis,deg,frames):
 s,r,ob,faces,cache=state;bad={}
 for f in frames:
  s.frame_set(f);q,solids=cache[f];r.pose.bones['thumb_01_l'].rotation_quaternion=Quaternion(Vector(axis).normalized(),math.radians(deg)*weight(f))@q;bpy.context.view_layer.update();e=ob.evaluated_get(bpy.context.evaluated_depsgraph_get());m=e.to_mesh();tree=BVHTree.FromPolygons([e.matrix_world@v.co for v in m.vertices],faces,all_triangles=True);hits={}
  for name,solid in solids:
   count=len(tree.overlap(solid))
   if count and name not in reference.get(f'{clip}_{f}',{}):hits[name]=count
  if hits:bad[f]=hits
  e.to_mesh_clear()
 return sum(sum(h.values()) for h in bad.values()),bad
solutions={}
for clip in clips:
 state=setup(clip);best=None
 for axis,deg in itertools.product([(1,0,0),(0,1,0),(0,0,1),(1,0,1),(0,1,1)],[-3,3,-6,6,-10,10,-15,15,-20,20]):
  score,hits=check(state,clip,axis,deg,range(start,end+1))
  if best is None or score<best[0]:best=(score,axis,deg,hits);print('TRANSITION_BEST',variant,clip,best,flush=True)
  if score==0:break
 assert best[0]==0,(variant,clip,best)
 solutions[clip]={'axis':best[1],'degrees':best[2],'start':start,'peak':peak,'end':end,'new_gun_or_grip_hits':best[0]}
(D/'thumb_transition.json').write_text(json.dumps(solutions,indent=2));print('AKM_TRANSITION_FIT_PASS',variant,flush=True)
