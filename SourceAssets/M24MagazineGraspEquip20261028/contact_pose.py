from pathlib import Path
exec(compile((Path(__file__).parent/'library.py').read_text(),'lib','exec'))
from mathutils.bvhtree import BVHTree
import bmesh
setup_render()
def smooth(a,b,x):
 w=max(0,min(1,(x-a)/(b-a)));return w*w*(3-2*w)
node=next(n for n in ast.parse((O.parent/'M24LeftElbowReview20261028/surface_scan.py').read_text()).body if isinstance(n,ast.FunctionDef) and n.name=='morphs_full')
exec(compile(ast.unparse(node),'morphs','exec'));morphs=morphs_full
def frame(f,r):
 f=f.normalized();r=(r-f*r.dot(f)).normalized();return Matrix((f,r,f.cross(r))).transposed()
F=rest['middle_01_l'].translation-rest['hand_l'].translation
R=rest['index_01_l'].translation-rest['pinky_01_l'].translation
palm_rotation=(frame(Vector((0,1,0)),Vector((0,0,1)))@frame(F,R).transposed()).to_quaternion()
digits=[f'{finger}_{j:02d}_l' for finger in ('index','middle','ring','pinky','thumb') for j in (1,2,3)]
def Q(x=0,y=0,z=0):return Quaternion((0,0,1),math.radians(z))@Quaternion((0,1,0),math.radians(y))@Quaternion((1,0,0),math.radians(x))
ids={n:i for i,n in enumerate(names)}
V=np.array([list(v.co)+[1] for v in skin.data.vertices]);weights=np.zeros((len(V),len(names)))
for v in skin.data.vertices:
 for g in v.groups:
  n=skin.vertex_groups[g.group].name
  if n in ids:weights[v.index,ids[n]]=g.weight
dominant=weights.argmax(1)
def hand_chain(h,qs):
 row={n:m.copy() for n,m in rest.items()};row['hand_l']=h
 for n in names:
  if n=='hand_l' or not under(n,'hand_l'):continue
  p,q,sc=local_rest[n].decompose()
  if n in qs:q=q@qs[n]
  row[n]=row[parents[n]]@Matrix.LocRotScale(p,q,sc)
 return row
def arm_to_hand(original,hand):
 out=clone(original);u,l,h='upperarm_l','lowerarm_l','hand_l';S=original[u].translation;H=hand.translation
 A=(rest[l].translation-rest[u].translation).length;B=(rest[h].translation-rest[l].translation).length
 axis=H-S;d=axis.length;axis.normalize()
 if d>A+B-.001:raise ValueError('Hand outside arm reach')
 pole=original[l].translation-S;pole-=axis*pole.dot(axis);pole.normalize()
 along=(A*A-B*B+d*d)/(2*d);E=S+axis*along+pole*math.sqrt(max(0,A*A-along*along))
 beforeU=original[l].translation-S;beforeL=original[h].translation-original[l].translation
 n0=beforeU.cross(beforeL).normalized();n1=(E-S).cross(H-E).normalized()
 uq=(frame(E-S,n1)@frame(beforeU,n0).transposed()).to_quaternion()@original[u].to_quaternion()
 lq=(frame(H-E,n1)@frame(beforeL,n0).transposed()).to_quaternion()@original[l].to_quaternion()
 U=Matrix.LocRotScale(S,uq,Vector((1,1,1)));L=Matrix.LocRotScale(E,lq,Vector((1,1,1)))
 for n in names:
  if under(n,h):out[n]=hand@original[h].inverted()@original[n]
  elif under(n,l):out[n]=L@original[l].inverted()@original[n]
  elif under(n,u):out[n]=U@original[u].inverted()@original[n]
 axis=rest[l].to_quaternion().inverted()@(rest[h].translation-rest[l].translation).normalized()
 relative=lq.inverted()@hand.to_quaternion()@(rest[l].to_quaternion().inverted()@rest[h].to_quaternion()).inverted()
 if relative.w<0:relative=-relative
 roll=2*math.atan2(Vector((relative.x,relative.y,relative.z)).dot(axis),relative.w)
 for i,fraction in ((1,1),(2,.5)):
  n=f'lowerarm_twist_{i:02d}_l';lr=local_rest[n]
  out[n]=L@Matrix.LocRotScale(lr.translation,Quaternion(axis,roll*fraction)@lr.to_quaternion(),Vector((1,1,1)))
 return out
def build(family):
 extended=family=='mag10';mag=bpy.data.objects['M24_Magazine10' if extended else 'M24_clip']
 bm=bmesh.new();bm.from_mesh(mag.data);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bmesh.ops.triangulate(bm,faces=list(bm.faces));bm.verts.ensure_lookup_table();bm.verts.index_update()
 bvh=BVHTree.FromPolygons([list(v.co) for v in bm.verts],[tuple(v.index for v in f.verts) for f in bm.faces],all_triangles=True);bm.free()
 bm=bmesh.new()
 for v in mag.data.vertices:bm.verts.new(v.co)
 bmesh.ops.convex_hull(bm,input=list(bm.verts),use_existing_faces=False);bm.normal_update();center=sum((v.co for v in bm.verts),Vector())/len(bm.verts);planes=[]
 for f in bm.faces:
  n=f.normal.copy()
  if n.dot(f.calc_center_median()-center)<0:n=-n
  planes.append((*n,n.dot(f.verts[0].co)))
 planes=np.array(planes);bm.free()
 target=Vector((-.049,.238,.023 if extended else .033))
 p=target-palm_rotation@(rest['middle_01_l'].translation-rest['hand_l'].translation)
 h=Matrix.LocRotScale(p,palm_rotation@rest['hand_l'].to_quaternion(),Vector((1,1,1)))
 print('THUMB_REST',family,{n:list(m.translation) for n,m in hand_chain(h,{}).items() if n.startswith('thumb') and n.endswith('_l')},flush=True)
 qs={};params={};report={}
 for finger in ('index','middle','ring','pinky','thumb'):
  ns=[f'{finger}_{j:02d}_l' for j in (1,2,3)]
  chosen=[ids[n] for n in ns];selected=np.where(np.isin(dominant,chosen))[0][::2]
  W=np.einsum('vk,kij,vj->kvi',weights[selected],np.array([np.array(rest[n].inverted()) for n in names]),V[selected],optimize=True)
  tipmask=dominant[selected]==chosen[2];midmask=dominant[selected]==chosen[1]
  def pose(params):
   poses={**qs}
   if finger=='thumb':poses.update({ns[0]:Q(*params[:3]),ns[1]:Q(z=params[3]),ns[2]:Q(z=params[4])})
   else:poses.update({ns[0]:Q(y=params[3],z=params[0]),ns[1]:Q(z=params[1]),ns[2]:Q(z=params[2])})
   return hand_chain(h,poses),poses
  def score(params,detail=False):
   row,_=pose(params);X=np.einsum('kij,kvj->vi',np.array([np.array(row[n]) for n in names]),W,optimize=True)[:,:3]
   envelope=np.max(X@planes[:,:3].T-planes[:,3],axis=1);ds=[]
   for x,inside in zip(X,envelope<0):
    hit,normal,_,d=bvh.find_nearest(Vector(x));ds.append(-d if inside and (Vector(x)-hit).dot(normal)<0 else d)
   ds=np.array(ds)*1000;pen=np.maximum(-ds-.35,0);near=np.sort(np.abs(ds[tipmask]))[:8];middle=np.sort(np.abs(ds[midmask]))[:8]
   value=float(np.mean(pen**2)*25+pen.max()**2*12+np.mean((near-1.3)**2)*.9+np.mean((middle-2)**2)*.15)
   if finger!='thumb':value+=.02*(params[2]-.55*params[1])**2+.012*params[3]**2+.008*(params[1]-65)**2
   else:value+=.009*np.sum((np.array(params)-np.array([-20,15,30,20,15]))**2)
   return {'score':value,'penetration_mm':float(max(0,-ds.min())),'tip_gap_mm':float(near.mean()),'middle_gap_mm':float(middle.mean())} if detail else value
  if finger=='thumb':initial=[-20,15,30,20,15];bounds=[(-65,65),(-70,70),(-40,70),(0,32),(0,28)]
  else:initial=[50,70,35,0];bounds=[(10,90),(10,110),(0,70),(-16,16)]
  fitted=initial.copy()
  if finger=='thumb':
   candidates=[]
   for x in (-60,-30,0,30,60):
    for y in (-60,-30,0,30,60):
     for z in (-30,0,30,60):
      trial=[x,y,z,20,12];candidates.append((score(trial),trial))
   fitted=min(candidates,key=lambda x:x[0])[1]
  for step in (18,9,4,2,.75):
   for repeat in range(3):
    for axis in range(len(fitted)):
     candidates=[]
     for offset in (-step,0,step):
      trial=fitted.copy();trial[axis]=max(bounds[axis][0],min(bounds[axis][1],trial[axis]+offset));candidates.append((score(trial),trial))
     fitted=min(candidates,key=lambda x:x[0])[1]
  _,qs=pose(fitted);params[finger]=list(fitted);report[finger]=score(fitted,True);print(family,finger,params[finger],report[finger],flush=True)
 # Thumb pad lies on the near broad face, opposing the four distal pads.
 # Swing native thumb segments toward that face without twisting their roll.
 thumb=hand_chain(h,{})
 for n,child,direction in (('thumb_01_l','thumb_02_l',Vector((.002,.042,.004))),('thumb_02_l','thumb_03_l',Vector((0,.026,-.012)))):
  parent=thumb[parents[n]];native=parent@local_rest[n];v=native.to_quaternion()@local_rest[child].translation
  q=v.rotation_difference(direction)@native.to_quaternion();thumb[n]=Matrix.LocRotScale(native.translation,q,Vector((1,1,1)))
  qs[n]=local_rest[n].to_quaternion().inverted()@parent.to_quaternion().inverted()@q
 qs['thumb_03_l']=Q(z=10)
 params['thumb']={'final_method':'native-segment swing, fixed pad on near face','ip_flex_degrees':10}
 report['thumb']={'final_method':'native-segment swing; preliminary optimizer discarded'}
 row=hand_chain(h,qs);base=clips['reload_mag10' if extended else 'reload'][24];M=base['WPN_Magazine']@rest['WPN_Magazine'].inverted();world=arm_to_hand(base,M@h)
 for n in names:
  if under(n,'hand_l'):world[n]=M@row[n]
 return {'hand':[list(v) for v in h],'rotations':{n:list(q) for n,q in qs.items()},'params':params,'contact':report},world
if __name__=='__main__':
 folder=O/'Fit';folder.mkdir(exist_ok=True);out={}
 for family in ('base','mag10'):
  out[family],row=build(family)
  for v in ('left','right','bottom'):show(row,folder/f'{family}_{v}.png',v,family=='mag10')
 (O/'contact_grips.json').write_text(json.dumps(out,indent=2))
