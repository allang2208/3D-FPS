"""Author Meshy receptionist on the intact Nurse skeleton. Background production only."""
import bpy,bmesh,json,math,sys
import numpy as np
from pathlib import Path
from mathutils import Vector,Matrix,Quaternion
from mathutils.bvhtree import BVHTree
from mathutils.geometry import barycentric_transform
ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/FacelessResearcher20261009/V01')
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'Authoring/Inputs.blend'))
body=bpy.data.objects['Researcher_SourceBody']
rig=next(o for o in bpy.context.scene.objects if o.type=='ARMATURE')
donor=next(o for o in bpy.context.scene.objects if o.type=='MESH' and o!=body)
rig.animation_data_clear();donor.shape_key_clear()
for p in rig.pose.bones:p.matrix_basis.identity()
REST={b.name:rig.matrix_world@b.matrix_local for b in rig.data.bones}
HEAD={n:m.translation for n,m in REST.items()}
def similarity(a,b,c,d):
 a,b,c,d=map(Vector,(a,b,c,d));u=b-a;v=d-c
 rot=u.rotation_difference(v).to_matrix().to_4x4()
 return Matrix.Translation(c)@rot@Matrix.Scale(v.length/u.length,4)@Matrix.Translation(-a)
def turn(a,target,angle=0,scale=1):
 return Matrix.Translation(Vector(target))@Matrix.Rotation(angle,4,'Y')@Matrix.Scale(scale,4)@Matrix.Translation(-a)
def major(n):
 if n.startswith(('thumb','index','middle','ring','pinky','wrist')):return 'hand_'+n[-1]
 for p in ['upperarm','lowerarm','hand','thigh','calf','foot','ball']:
  if n.startswith(p):return p+'_'+n[-1]
 if n.startswith('clavicle'):return n
 if n in ['pelvis','head','neck_01','neck_02'] or n.startswith('spine_'):return n
 b=rig.data.bones[n]
 return major(b.parent.name) if b.parent else 'pelvis'
MAP={}
for n in REST:
 z=HEAD[n].z
 shift=float(np.interp(z,[0,.1,.55,.987,1.135,1.33,1.453,1.515,1.626,1.83],[0,.108,.60,1.023,1.15,1.37,1.546,1.617,1.714,1.88]))-z
 MAP[n]=Matrix.Translation((0,0,shift))
TARGET={}
for side,sign in [('l',1),('r',-1)]:
 shoulder=Vector((sign*.186,.044,1.546));elbow=Vector((sign*.272,.025,1.272));wrist=Vector((sign*.374,-.030,1.040))
 hip=Vector((sign*.102,.020,1.023));knee=Vector((sign*.116,.032,.600));ankle=Vector((sign*.153,.069,.108));toe=Vector((sign*.154,-.085,.027))
 for part,a,b in [('upperarm',shoulder,elbow),('lowerarm',elbow,wrist),('thigh',hip,knee),('calf',knee,ankle),('foot',ankle,toe)]:
  child={'upperarm':'lowerarm','lowerarm':'hand','thigh':'calf','calf':'foot','foot':'ball'}[part]
  MAP[part+'_'+side]=similarity(HEAD[part+'_'+side],HEAD[child+'_'+side],a,b)
 MAP['ball_'+side]=turn(HEAD['ball_'+side],toe)
 # Fit the real donor middle fingertip surface to the source fingertip.
 hand_tip=[]
 for v in donor.data.vertices:
  if any(donor.vertex_groups[g.group].name=='middle_03_'+side and g.weight>.25 for g in v.groups):
   hand_tip.append(donor.matrix_world@v.co)
 hand_tip.sort(key=lambda p:(p-HEAD['hand_'+side]).length,reverse=True)
 donor_tip=sum(hand_tip[:max(1,len(hand_tip)//5)],Vector())/max(1,len(hand_tip)//5)
 src_tip=[v.co.copy() for v in body.data.vertices if sign*v.co.x>.35 and .78<v.co.z<.92]
 src_tip.sort(key=lambda p:p.z)
 source_tip=sum(src_tip[:max(1,len(src_tip)//10)],Vector())/max(1,len(src_tip)//10)
 MAP['hand_'+side]=similarity(HEAD['hand_'+side],donor_tip,wrist,source_tip)
 MAP['clavicle_'+side]=similarity(HEAD['clavicle_'+side],HEAD['upperarm_'+side],(sign*.012,.031,1.576),shoulder)
 TARGET[side]=dict(shoulder=list(shoulder),elbow=list(elbow),wrist=list(wrist),hip=list(hip),knee=list(knee),ankle=list(ankle),toe=list(toe))
for n in REST:
 m=major(n)
 if m!=n:MAP[n]=MAP[m].copy()
def vertex_weights(o,v):
 return {o.vertex_groups[g.group].name:g.weight for g in v.groups if g.weight>1e-7 and o.vertex_groups[g.group].name in REST}
def norm(ws):
 ws={n:w for n,w in sorted(ws.items(),key=lambda kv:-kv[1])[:8] if w>1e-5};t=sum(ws.values())
 return {n:w/t for n,w in ws.items()} if t else {'pelvis':1.}
def matrix(ws):
 a=Matrix(((0,0,0,0),)*4)
 for n,w in ws.items():
  m=MAP[n]
  for r in range(4):
   for c in range(4):a[r][c]+=m[r][c]*w
 return a
# Build the posed anatomical donor surface, excluding nurse clothing, hair and eyes.
dw=[norm(vertex_weights(donor,v)) for v in donor.data.vertices]
dp=[matrix(ws)@(donor.matrix_world@v.co) for v,ws in zip(donor.data.vertices,dw)]
donor.data.calc_loop_triangles()
tri=[tuple(t.vertices) for t in donor.data.loop_triangles if donor.data.polygons[t.polygon_index].material_index in (0,3)]
bvh=BVHTree.FromPolygons(dp,tri,all_triangles=True)
def sample(point,tree,verts,tris,weights):
 hit=tree.find_nearest(point)
 if hit[0] is None:raise RuntimeError('No donor surface at '+str(point))
 ids=tris[hit[2]]
 b=barycentric_transform(hit[0],*(verts[i] for i in ids),Vector((1,0,0)),Vector((0,1,0)),Vector((0,0,1)))
 b=[max(0.,float(x)) for x in b];total=sum(b);result={}
 for i,f in zip(ids,b):
  for n,w in weights[i].items():result[n]=result.get(n,0)+w*f/total
 return norm(result)
# The donor's upper legs/hips are absent below its dress. Do not transfer
# those vertices against an unrestricted nearest-surface tree (hands were nearest).
# Torso and leg skin use anatomical joints; fingers alone use side-restricted
# donor surfaces after fitting the hand.
points=[v.co.copy() for v in body.data.vertices]
hand_trees={}
for side in ['l','r']:
 allowed=lambda n:n.endswith('_'+side) and n.startswith(('hand','thumb','index','middle','ring','pinky'))
 wh=[norm({n:w for n,w in ws.items() if allowed(n)}) for ws in dw]
 handtris=[t for t in tri if all(sum(w for n,w in dw[i].items() if allowed(n))>.35 for i in t)]
 hand_trees[side]=(BVHTree.FromPolygons(dp,handtris,all_triangles=True),handtris,wh)
def smooth(a,b,x):
 t=max(0.,min(1.,(x-a)/(b-a)));return t*t*(3-2*t)
spine_names=['pelvis']+sorted(n for n in REST if n.startswith('spine_') and len(n)==8)+['neck_01','neck_02','head']
spine_z=[(MAP[n]@HEAD[n]).z for n in spine_names]
def torso_weights(p):
 if p.z<=spine_z[0]:return {'pelvis':1.}
 for i in range(len(spine_z)-1):
  if p.z<=spine_z[i+1]:
   t=smooth(spine_z[i],spine_z[i+1],p.z)
   return norm({spine_names[i]:1-t,spine_names[i+1]:t})
 return {'head':1.}
def mixweights(a,b,t):
 result={n:w*(1-t) for n,w in a.items()}
 for n,w in b.items():result[n]=result.get(n,0)+w*t
 return norm(result)
def anatomical_weights(p):
 side='l' if p.x>=0 else 'r'
 sign=1 if p.x>=0 else -1
 # Compare anatomical surface envelopes, including the front/back distance.
 # A height/x-only blend erroneously mixed inner sleeves with the torso.
 shoulder,elbow,wrist=(Vector(TARGET[side][key]) for key in ['shoulder','elbow','wrist'])
 def seg_distance(a,b):
  t=max(0.,min(1.,(p-a).dot(b-a)/(b-a).length_squared))
  return (p-a.lerp(b,t)).length
 arm_metric=min(seg_distance(shoulder,elbow)/.056,seg_distance(elbow,wrist)/.040,
                (p-wrist).length/.16 if p.z<wrist.z else 1e6)
 rx=float(np.interp(p.z,[.8,1.02,1.20,1.28,1.44,1.55,1.64],[.19,.20,.14,.118,.15,.15,.055]))
 ry=float(np.interp(p.z,[.8,1.02,1.20,1.28,1.44,1.55,1.64],[.09,.115,.10,.095,.125,.083,.054]))
 torso_metric=math.sqrt((p.x/rx)**2+((p.y-.020)/ry)**2)
 arm_blend=smooth(-.35,.35,torso_metric-arm_metric)
 if p.z<1.22 and abs(p.x)<.215:arm_blend=0.
 if p.z>1.625:arm_blend=0.
 if arm_blend>0:
  shoulder,elbow,wrist=(Vector(TARGET[side][key]) for key in ['shoulder','elbow','wrist'])
  elbow_blend=smooth(-.05,.05,(p-elbow).dot((wrist-shoulder).normalized()))
  arm=mixweights({'upperarm_'+side:1.},{'lowerarm_'+side:1.},elbow_blend)
  wrist_blend=smooth(-.035,.020,(p-wrist).dot((wrist-elbow).normalized()))
  if wrist_blend>0:
   tree,ht,hw=hand_trees[side]
   hand=sample(p,tree,dp,ht,hw)
   hand={n:w for n,w in hand.items() if n!='pelvis'} or {'hand_'+side:1.}
   arm=mixweights(arm,norm(hand),wrist_blend)
  if arm_blend>=.999:return arm
 else:arm={}
 if p.z>=1.06:core=torso_weights(p)
 else:
  hip=smooth(1.06,.87,p.z)
  knee=smooth(.665,.535,p.z)
  ankle=smooth(.175,.070,p.z)
  ball=smooth(-.008,-.095,p.y)*(1-smooth(.06,.105,p.z))
  core=mixweights({'pelvis':1.},{'thigh_'+side:1.},hip)
  core=mixweights(core,{'calf_'+side:1.},knee)
  foot=mixweights({'foot_'+side:1.},{'ball_'+side:1.},ball)
  core=mixweights(core,foot,ankle)
 return mixweights(core,arm,arm_blend) if arm_blend else core
body_weights=[anatomical_weights(p) for p in points]
body.data.calc_loop_triangles();bodytris=[tuple(t.vertices) for t in body.data.loop_triangles]
body_bvh=BVHTree.FromPolygons(points,bodytris,all_triangles=True)
def body_sample(p):return sample(p,body_bvh,points,bodytris,body_weights)
