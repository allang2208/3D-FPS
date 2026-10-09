"""Author V03 clothing weights and motion clearance from the three UE clips."""
import bpy,bmesh,json,shutil,math
import numpy as np
from pathlib import Path
from mathutils import Vector,Matrix
from mathutils.bvhtree import BVHTree
BASE=Path(r'D:\FPS3D\FPSGAME\SourceAssets\FacelessReceptionist20261007')
ROOT=BASE/'V03'
for d in ['Authoring','Delivery','Textures','Logs']:(ROOT/d).mkdir(parents=True,exist_ok=True)
for f in (BASE/'V02/Textures').glob('*.png'):shutil.copy2(f,ROOT/'Textures'/f.name)
bpy.ops.wm.open_mainfile(filepath=str(BASE/'V02/Authoring/FacelessReceptionist_V02.blend'))
s=bpy.context.scene;body=bpy.data.objects['Receptionist_CompleteBody'];rig=body.parent
rig.animation_data.action=None
for tr in rig.animation_data.nla_tracks:tr.mute=True
s.frame_set(0)
for p in rig.pose.bones:p.matrix_basis=Matrix.Identity(4)
raw=list(rig['source_world_matrix']);rest_world=Matrix([raw[i:i+4] for i in range(0,16,4)]);rig.matrix_world=rest_world
for im in bpy.data.images:
 name=Path(bpy.path.abspath(im.filepath)).name
 if (ROOT/'Textures'/name).exists():im.filepath=str(ROOT/'Textures'/name)
def smooth(a,b,x):
 t=max(0.,min(1.,(x-a)/(b-a)));return t*t*(3-2*t)
def normalise(ws):
 ws={n:w for n,w in sorted(ws.items(),key=lambda kv:-kv[1])[:8] if w>1e-5}
 total=sum(ws.values())
 return {n:w/total for n,w in ws.items()} if total else {'pelvis':1.}
def weights(o,v):return {o.vertex_groups[g.group].name:g.weight for g in v.groups if g.weight>1e-5}
def set_weights(o,values):
 o.vertex_groups.clear()
 for n in sorted({n for w in values for n in w}):o.vertex_groups.new(name=n)
 for v,w in zip(o.data.vertices,values):
  for n,f in w.items():o.vertex_groups[n].add([v.index],f,'REPLACE')
def skirt_skin(p):
 u=smooth(1.062,.493,p.z)
 # Front/back centers retain more pelvis support; side panels follow one thigh.
 side_strength=min(1.,abs(p.x)/.21)
 leg=.72*u*(.65+.35*side_strength)
 left=.5+.5*math.tanh(p.x/.095)
 return normalise({'pelvis':1-leg,'thigh_l':leg*left,'thigh_r':leg*(1-left)})
for o in s.objects:
 if o.type!='MESH' or o==body:continue
 values=[]
 for v in o.data.vertices:
  w=weights(o,v);p=v.co
  if o.name=='Receptionist_Skirt_Waistband':w={'pelvis':1.}
  elif o.name.startswith(('Receptionist_Skirt','Receptionist_Skirt_BackVent')):w=skirt_skin(p)
  elif o.name.startswith(('Receptionist_Blazer','Receptionist_Shirt_Continuous')) and p.z<1.105 and abs(p.x)<.27:
   moved=sum(f for n,f in w.items() if n.startswith(('thigh','calf','foot','ball')))
   w={n:f for n,f in w.items() if not n.startswith(('thigh','calf','foot','ball'))}
   w['pelvis']=w.get('pelvis',0)+moved
  elif 'Collar' in o.name:
   # A shirt collar is supported at the neck base, independent of the head tilt.
   w={'spine_05':1-smooth(1.515,1.556,p.z),'neck_01':smooth(1.515,1.556,p.z)}
  values.append(normalise(w))
 set_weights(o,values)
# Smooth sharp spatial weight changes within the two continuous garment shells.
for name in ['Receptionist_Blazer_Continuous','Receptionist_Shirt_Continuous']:
 o=bpy.data.objects[name];vals=[weights(o,v) for v in o.data.vertices]
 links=[[] for v in o.data.vertices]
 for e in o.data.edges:a,b=e.vertices;links[a].append(b);links[b].append(a)
 for iteration in range(3):
  nv=[]
  for i,ws in enumerate(vals):
   out={n:w*.65 for n,w in ws.items()}
   for j in links[i]:
    for n,w in vals[j].items():out[n]=out.get(n,0)+w*.35/max(1,len(links[i]))
   nv.append(normalise(out))
  vals=nv
 set_weights(o,vals)
body.data.calc_loop_triangles();tri=[tuple(t.vertices) for t in body.data.loop_triangles]
bp=np.asarray([v.co[:] for v in body.data.vertices],np.float64)
bw=[weights(body,v) for v in body.data.vertices]
rest_bvh=BVHTree.FromPolygons([Vector(p) for p in bp],tri,all_triangles=True)
# Relax muscle-shaped sleeve bulges into a tapered woven sleeve with body ease.
jacket=bpy.data.objects['Receptionist_Blazer_Continuous']
N=len(jacket.data.vertices)//2
for i in range(N):
 p=jacket.data.vertices[i].co.copy();side='l' if p.x>=0 else 'r'
 a,b,c=[rest_world@rig.data.bones[n+'_'+side].head_local for n in ['upperarm','lowerarm','hand']]
 best=None
 for seg,(q,r) in enumerate([(a,b),(b,c)]):
  t=max(0.,min(1.,(p-q).dot(r-q)/(r-q).length_squared));center=q.lerp(r,t)
  dist=(p-center).length
  if best is None or dist<best[0]:best=(dist,center,(seg+t)/2)
 distance,center,t=best
 if abs(p.x)<.215 or distance>.13:continue
 target=float(np.interp(t,[0,.18,.48,1],[.080,.074,.055,.039]))
 amount=.42*smooth(.03,.18,t)*(1-smooth(.91,1.,t))
 changed=p+(p-center).normalized()*max(-.010,min(.010,(target-distance)*amount))
 hit=rest_bvh.find_nearest(changed)
 if hit[0] is not None:
  d=(changed-hit[0]).dot(hit[1])
  if d<.012:changed+=hit[1]*(.012-d)
 delta=changed-p
 jacket.data.vertices[i].co+=delta;jacket.data.vertices[i+N].co+=delta
# Cache exact deformation matrices from the current game clips. This is an
# authoring input, not a gameplay/pose acceptance test.
owned=set(bpy.data.objects);bone_names=sorted({n for ws in bw for n in ws}|{n for o in s.objects if o.type=='MESH' for v in o.data.vertices for n in weights(o,v)})
motion=[]
for role,count in [('idle',5),('walk',13),('attack',15)]:
 before=set(bpy.data.objects)
 bpy.ops.import_scene.fbx(filepath=str(ROOT/'MotionSources'/('A_Receptionist_'+role+'.fbx')),use_anim=True)
 imported=set(bpy.data.objects)-before
 donor=next(o for o in imported if o.type=='ARMATURE')
 action=donor.animation_data.action
 first,last=map(float,action.frame_range)
 base_world=donor.matrix_world.copy()
 inv_ref={n:(base_world@donor.data.bones[n].matrix_local).inverted() for n in bone_names}
 frames=sorted(set(int(round(f)) for f in np.linspace(first,last,count)))
 for f in frames:
  s.frame_set(f);bpy.context.view_layer.update()
  mats={n:np.array(donor.matrix_world@donor.pose.bones[n].matrix@inv_ref[n],dtype=np.float64) for n in bone_names}
  motion.append((role,f,mats))
 for o in imported:bpy.data.objects.remove(o,do_unlink=True)
 print('MOTION_INPUT '+role+' '+str(len(frames))+' source frames',flush=True)
# Restore author source's exact bind frame before writing clothing.
rig.animation_data.action=None
s.frame_set(0)
for p in rig.pose.bones:p.matrix_basis=Matrix.Identity(4)
rig.matrix_world=rest_world;bpy.context.view_layer.update()
def packed(ws):
 out={}
 for i,w in enumerate(ws):
  for n,f in w.items():
   entry=out.setdefault(n,([],[]));entry[0].append(i);entry[1].append(f)
 return {n:(np.array(ids,dtype=np.int32),np.array(w,dtype=np.float64)) for n,(ids,w) in out.items()}
body_groups=packed(bw)
def deform(points,groups,mats):
 result=np.zeros_like(points)
 for n,(ids,ws) in groups.items():
  m=mats[n];result[ids]+=((points[ids]@m[:3,:3].T)+m[:3,3])*ws[:,None]
 return result
targets=[]
for name,clearance,cap in [('Receptionist_Blazer_Continuous',.007,.017),('Receptionist_Shirt_Continuous',.0025,.008),('Receptionist_Skirt',.012,.040),('Receptionist_Skirt_BackVentUnderlap',.009,.040)]:
 o=bpy.data.objects[name];count=len(o.data.vertices)//2
 points=np.array([v.co[:] for v in o.data.vertices[:count]])
 ws=[weights(o,v) for v in o.data.vertices[:count]]
 normals=[]
 for p in points:
  if 'Skirt' in name:n=Vector((p[0],p[1]-.027,0)).normalized()
  else:
   n=o.data.vertices[len(normals)].normal.copy()
   reference=rest_bvh.find_nearest(Vector(p))[1]
   if n.dot(reference)<0:n=-n
   n.normalize()
  normals.append(tuple(n))
 targets.append({'object':o,'count':count,'points':points,'groups':packed(ws),'normals':np.array(normals),'padding':np.zeros(count),'clearance':clearance,'cap':cap})
for pose_index,(role,frame,mats) in enumerate(motion):
 posed_body=deform(bp,body_groups,mats)
 posed_bvh=BVHTree.FromPolygons([Vector(p) for p in posed_body],tri,all_triangles=True)
 for data in targets:
  p=data['points'];posed=deform(p,data['groups'],mats)
  directions=np.zeros_like(p)
  for n,(ids,w) in data['groups'].items():directions[ids]+=(data['normals'][ids]@mats[n][:3,:3].T)*w[:,None]
  for i,q in enumerate(posed):
   h=posed_bvh.find_nearest(Vector(q))
   if h[0] is None:continue
   signed=(Vector(q)-h[0]).dot(h[1])
   if signed>=data['clearance']:continue
   alignment=float(np.dot(directions[i],h[1]))
   if alignment>.22:
    needed=(data['clearance']-signed)/alignment
    data['padding'][i]=max(data['padding'][i],min(data['cap'],needed))
 if pose_index%8==0:print('CLOTHING_AUTHOR_FIT '+str(pose_index+1)+'/'+str(len(motion)),flush=True)
for data in targets:
 o=data['object'];count=data['count'];padding=data['padding']
 links=[set() for i in range(count)]
 for e in o.data.edges:
  a,b=(int(x)%count for x in e.vertices)
  if a!=b:links[a].add(b);links[b].add(a)
 # Spread motion ease to nearby cloth instead of making point-sized bulges.
 for iteration in range(10):
  padding=np.array([max(padding[i]*.88,(sum(padding[j] for j in links[i])/len(links[i]) if links[i] else padding[i])) for i in range(count)])
 # Filter ease over physical cloth regions, rather than only a few dense edges.
 raw_points=data['points'];keys=[]
 for p in raw_points:
  if 'Skirt' in o.name:
   part=0;u=(p[2]-.48)/.65;theta=math.atan2(p[0],-(p[1]-.027))
  else:
   side='l' if p[0]>=0 else 'r'
   a,b,c=[rest_world@rig.data.bones[n+'_'+side].head_local for n in ['upperarm','lowerarm','hand']]
   if abs(p[0])>.225:
    best=None;vp=Vector(p)
    for seg,(q,r) in enumerate([(a,b),(b,c)]):
     t=max(0,min(1,(vp-q).dot(r-q)/(r-q).length_squared));center=q.lerp(r,t)
     if best is None or (vp-center).length<best[0]:best=((vp-center).length,center,(seg+t)/2,(r-q).normalized())
    _,center,u,tangent=best
    axis=Vector((0,1,0));axis=(axis-tangent*axis.dot(tangent)).normalized();cross=tangent.cross(axis)
    d=vp-center;theta=math.atan2(d.dot(cross),d.dot(axis));part=1 if side=='l' else 2
   else:
    part=0;u=(p[2]-.97)/.62;theta=math.atan2(p[0],-(p[1]-.015))
  keys.append((part,max(0,min(39,int(u*39))),int((theta+math.pi)/(2*math.pi)*64)%64))
 grids=np.zeros((3,40,64));counts=np.zeros_like(grids)
 for k,pad in zip(keys,padding):grids[k]+=pad;counts[k]+=1
 grids=np.divide(grids,counts,out=np.zeros_like(grids),where=counts>0)
 mask=(counts>0).astype(float)
 # Gaussian-like periodic angular diffusion spreads the same ease continuously.
 for _ in range(35):
  numerator=grids*mask*2;denominator=mask*2
  for axis in [1,2]:
   for step in [-1,1]:
    numerator+=np.roll(grids*mask,step,axis);denominator+=np.roll(mask,step,axis)
  grids=np.divide(numerator,denominator,out=grids.copy(),where=denominator>0)
  mask=np.clip(denominator,0,1)
 padding=np.array([grids[k] for k in keys])
 for i,pad in enumerate(padding):
  # The waistband remains an anchored seam; ease increases below it.
  if 'Skirt' in o.name:pad*=smooth(1.06,.93,data['points'][i,2])
  if 'Blazer' in o.name and data['points'][i,2]>1.38:pad=min(pad,.006)
  d=Vector(data['normals'][i]*pad)
  o.data.vertices[i].co+=d;o.data.vertices[i+count].co+=d
 o.data.update();o.data.normals_split_custom_set([(0,0,0)]*len(o.data.loops))
for o in s.objects:
 if o.type=='MESH':o.data.update()
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'Authoring/FacelessReceptionist_V03_Fit.blend'))
report={'version':'V03','stage':'clothing_motion_authored','input':'V02/Authoring/FacelessReceptionist_V02.blend','source_motion_frames':len(motion),'source_motion_assets':'MotionSources/sources.json','body_mesh_changed':False,'body_weights_changed':False,'animation_curves_changed':False,'runtime_tested':False,'cloth_simulation':False,'changes':['Pelvis-anchored skirt waist, side thigh follow, reduced bilateral pull at front/back center.','Jacket hem isolated from thigh weights; collar limited to neck base.','Sleeve shape eased and clothing weights smoothed.','Motion-dependent ease authored offline from the three currently assigned UE clips.']}
(ROOT/'motion_authoring.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('V03_CLOTHING_MOTION_AUTHORED',flush=True)
