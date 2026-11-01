"""Author bounded anatomical right-hand contacts against saved M24 surfaces."""
import sys,ast,copy
from pathlib import Path
FIX=Path(__file__).resolve().parent;CHECK=FIX.parent/'M24RightGripCheck20261031'
__file__=str(CHECK/'corrected.py')
exec(compile((CHECK/'corrected.py').read_text().split("\nreport={'morph_count'")[0],'corrective_setup','exec'))
sys.path.insert(0,str(FIX/'Vendor'))
from scipy.optimize import least_squares
from scipy.spatial import ConvexHull
__file__=str(FIX/'fit.py')
tree=ast.parse((FIX.parent/'M24ReceiverGripRebuild20261031/author_grasp.py').read_text())
for n in tree.body:
 if isinstance(n,ast.FunctionDef) and n.name=='solve':exec(compile(ast.Module(body=[n],type_ignores=[]),'arm_solver','exec'))
role='right_grip_fit';time=0.
row0,local0=compose(entry('skeleton_base','idle'),0.);gm=row0['WPN_root']@rest['WPN_root'].inverted();inv=gm.inverted();hand0=inv@row0['hand_r']
X0=(np.c_[skin(row0),np.ones(len(P))]@np.array(inv).T)[:,:3]
finger_bones=[f+'_%02d_r'%j for f in ('index','middle','ring','pinky','thumb') for j in (1,2,3)]
axes={}
for f in ('index','middle','ring','pinky','thumb'):
 d1=row0[f+'_02_r'].translation-row0[f+'_01_r'].translation;d2=row0[f+'_03_r'].translation-row0[f+'_02_r'].translation
 axis=d1.cross(d2).normalized()
 for j in (1,2,3):axes[f+'_%02d_r'%j]=row0[f+'_%02d_r'%j].to_quaternion().inverted()@axis
palm_normal=(row0['index_metacarpal_r'].translation-row0['pinky_metacarpal_r'].translation).cross(row0['middle_01_r'].translation-row0['hand_r'].translation).normalized()
spread_axis=row0['index_01_r'].to_quaternion().inverted()@palm_normal
thumb_abduct_axis=row0['thumb_01_r'].to_quaternion().inverted()@d1.normalized()
def pose(x,base=row0,local=local0):
 src=Matrix.LocRotScale(hand0.translation+Vector(x[:3])*.001,(Quaternion((1,0,0),math.radians(x[3]))@Quaternion((0,1,0),math.radians(x[4]))@Quaternion((0,0,1),math.radians(x[5])))@hand0.to_quaternion(),hand0.to_scale())
 result=solve(base,gm@src)
 for n in names:
  if not under(n,'hand_r') or n=='hand_r':continue
  p,q,s=local[n].decompose()
  if n in finger_bones:q=q@Quaternion(axes[n],math.radians(x[6+finger_bones.index(n)]))
  if n=='index_01_r':q=q@Quaternion(spread_axis,math.radians(x[21]))
  if n=='thumb_01_r':q=q@Quaternion(thumb_abduct_axis,math.radians(x[22]))
  result[n]=result[parents[n]]@Matrix.LocRotScale(p,q,s)
 return result
def source_skin(row,ids=None):
 delta=np.zeros_like(P);ws=weights(row)
 for n,w in ws.items():
  if n in shapes:delta+=shapes[n]*w
 if ids is None:ids=np.arange(len(P))
 x=skin(row,P=(P+delta)[ids],W=W[ids]);return (np.c_[x,np.ones(len(x))]@np.array(inv).T)[:,:3]
def signed(bvh,p):
 point=Vector(p);loc,n,j,d=bvh.find_nearest(point)
 if id(bvh) in hull_ids:return -d if (point-loc).dot(n)<0 else d
 return -d if (point-loc).dot(n)<0 and inside(bvh,point) else d

# Use a continuous outer envelope for fitting. Imported grip meshes include
# overlapping decorative shells; their parity can jump inside the solid grip.
# The production mesh stays untouched and remains the reporting surface.
hull_ids=set();grip_hulls={}
for key in ('Default','balanced','phantom','stable'):
 hp,_=geo(key);h=ConvexHull(hp);faces=[]
 for f,e in zip(h.simplices,h.equations):
  f=f.tolist()
  if np.cross(hp[f[1]]-hp[f[0]],hp[f[2]]-hp[f[0]])@e[:3]<0:f.reverse()
  faces.append(f)
 b=BVHTree.FromPolygons(hp,faces,all_triangles=True);grip_hulls[key]=b;hull_ids.add(id(b))
src=FIX.parent/'M24ReceiverContinuityV220261031/M24_ReceiverContinuityV2_Editable.blend'
with bpy.data.libraries.load(str(src),link=False) as (a,b):b.objects=['M24_trigger']
trigger=b.objects[0];tv=[v.co[:] for v in trigger.data.vertices];tf=[list(p.vertices) for p in trigger.data.polygons];trigger_tree=BVHTree.FromPolygons(tv,tf)
del trigger
# Broad point sampling protects finger flanks and the web, not just the tips.
ids=np.flatnonzero(hand)[::5];tipids=np.flatnonzero(W[:,indices['index_03_r']]>.6)
tipids=sorted(tipids,key=lambda i:trigger_tree.find_nearest(Vector(X0[i]))[3])[:12]
lo=np.array([-12,-8,-18,-16,-16,-16]+[-65,-55,-40]+[-30,-25,-22]*3+[-35,-35,-30]+[-24,-24],float)
hi=np.array([15,26,10,16,16,16]+[30,25,25]+[30,25,22]*3+[35,35,30]+[24,24],float)
lo[8]=-16;hi[8]=18;hi[15]=8;lo[21]=-12;hi[21]=12
previous=json.loads((FIX/'fit_parameters.json').read_text()) if (FIX/'fit_parameters.json').exists() else None
report={'variants':{},'finger_bones':finger_bones,'axes':{n:list(a) for n,a in axes.items()},'index_spread_axis':list(spread_axis),'thumb_abduct_axis':list(thumb_abduct_axis),'hand0_source':list(map(list,hand0)),'old_idle_hand_ue':list((K@row0['hand_r']@K).translation)}
if previous:report['variants']=copy.deepcopy(previous['variants'])
targets=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []
for variant in ('Default','balanced','phantom','stable'):
 if targets and variant not in targets:continue
 bvh=grip_hulls[variant];contacts=[]
 for label in ('palm','middle','ring','pinky','thumb'):
  group=np.flatnonzero(hand&(labels==label));group=sorted(group,key=lambda i:abs(signed(bvh,X0[i])))[:16]
  contacts+=group
 start=np.array(previous['variants'][variant]['parameters']) if previous else np.zeros(23)
 if variant in ('balanced','stable') and previous:
  start=np.array(previous['variants']['phantom']['parameters'])
  if variant=='stable':start[1]+=6
 start=np.clip(start,lo+1e-6,hi-1e-6)
 # Include every currently contacting or penetrating vertex, plus the whole
 # thumb web. Sparse sampling alone missed small areas under the receiver.
 initial=source_skin(pose(start));dense=[]
 for i in np.flatnonzero(hand):
  if labels[i]=='thumb' or signed(bvh,initial[i])<.001 or signed(trees['receiver'],initial[i])<.001:dense.append(int(i))
 ids=np.array(sorted(set(np.flatnonzero(hand)[::4].tolist()+dense)))
 allids=np.array(sorted(set(ids.tolist()+contacts+tipids)));lookup={int(i):j for j,i in enumerate(allids)}
 collision=np.array([lookup[int(i)] for i in ids]);ci=np.array([lookup[int(i)] for i in contacts]);ti=np.array([lookup[int(i)] for i in tipids]);evaluations=[0]
 def objective(x):
  row=pose(x);X=source_skin(row,allids)
  grip=np.array([signed(bvh,p) for p in X])*1000;body=np.array([signed(trees['receiver'],p) for p in X])*1000
  trg=np.array([trigger_tree.find_nearest(Vector(X[i]))[3]*1000 for i in ti])
  # Negative distances are penetration. Keep a thin skin/metal clearance;
  # contact constraints tolerate a small gap instead of crushing the whole pad.
  reg=np.r_[x[:3]*.05,x[3:6]*.07,x[6:21]*.035,x[21:]*.045]
  residual=np.r_[np.minimum(grip[collision]-.45,0)*5.,np.minimum(body[collision]-.65,0)*6.,np.maximum(np.abs(grip[ci])-1.2,0)*.25,np.maximum(trg-.8,0)*2.,reg]
  evaluations[0]+=1
  if evaluations[0]%300==0:print('FIT_PROGRESS',variant,evaluations[0],round(float(np.linalg.norm(residual)),3),flush=True)
  return residual
 def jacobian(x):
  # Blender matrices are float32: a relative step at a zero parameter would
  # vanish. Use finite authoring increments in mm/degrees for every channel.
  base=objective(x);columns=[]
  for j in range(len(x)):
   step=.04 if j<3 else .08
   if x[j]+step>hi[j]:step=-step
   y=x.copy();y[j]+=step;columns.append((objective(y)-base)/step)
  return np.array(columns).T
 result=least_squares(objective,start,bounds=(lo,hi),jac=jacobian,x_scale='jac',xtol=1e-5,ftol=1e-5,gtol=1e-4,max_nfev=130,verbose=0)
 row=pose(result.x);X=source_skin(row)
 measures={key:metric(X,key) for key in (variant,'receiver')};trg=[trigger_tree.find_nearest(Vector(X[i]))[3]*1000 for i in tipids]
 # Outside the convex envelope is necessarily outside the imported grip.
 # The donor's open decorative seams otherwise yield false odd-ray counts.
 valid=np.array([i for i in np.flatnonzero(hand) if signed(bvh,X[i])<0],dtype=int)
 measures[variant]=metric(X,variant,ids=valid)
 measures[variant]['envelope_max_penetration_mm']=max([0.]+[-signed(bvh,X[i])*1000 for i in valid])
 report['variants'][variant]={'parameters':result.x.tolist(),'cost':result.cost,'evaluations':evaluations[0],'measurements':measures,'index_pad_min_gap_mm':min(trg),'index_pad_max_gap_mm':max(trg),'hand_target_source':list(map(list,inv@row['hand_r'])),'finger_local_quaternions':{n:list((row[parents[n]].inverted()@row[n]).to_quaternion()) for n in finger_bones}}
 print('FIT_RESULT',variant,json.dumps({'parameters':result.x.tolist(),'penetration':{k:v['max_penetration_mm'] for k,v in measures.items()},'index_gap':[min(trg),max(trg)]}),flush=True)
 (FIX/'fit_parameters.json').write_text(json.dumps(report,indent=2))
 np.save(FIX/(variant+'_fit_skin.npy'),X)
 oldO=O;O=FIX
 render(X,variant+'_back',variant=variant,view='back');render(X,variant+'_trigger',variant=variant,view='trigger')
 O=oldO
print('M24_RIGHT_GRASP_FIT_DONE',flush=True)
