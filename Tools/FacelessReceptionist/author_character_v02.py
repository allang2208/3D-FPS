"""Author Meshy receptionist on the intact Nurse skeleton. Background production only."""
import bpy,bmesh,json,math,sys
import numpy as np
from pathlib import Path
from mathutils import Vector,Matrix,Quaternion
from mathutils.bvhtree import BVHTree
from mathutils.geometry import barycentric_transform
BASE=Path('D:/FPS3D/FPSGAME/SourceAssets/FacelessReceptionist20261007')
ROOT=BASE/'V02'
for folder in ['Authoring','Delivery','Textures','Logs']: (ROOT/folder).mkdir(parents=True,exist_ok=True)
import shutil
for f in (BASE/'Textures').glob('Source_*.png'): shutil.copy2(f,ROOT/'Textures'/f.name)
bpy.ops.wm.open_mainfile(filepath=str(BASE/'Authoring/Inputs.blend'))
body=bpy.data.objects['Receptionist_SourceBody']
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
 shift=float(np.interp(z,[0,.1,.55,.987,1.135,1.33,1.453,1.515,1.626,1.83],[0,.1,.54,1.003,1.16,1.36,1.47,1.57,1.652,1.82]))-z
 MAP[n]=Matrix.Translation((0,0,shift))
TARGET={}
for side,sign in [('l',1),('r',-1)]:
 shoulder=Vector((sign*.184,.045,1.47));elbow=Vector((sign*.282,.031,1.218));wrist=Vector((sign*.411,-.023,.960))
 hip=Vector((sign*.105,.025,.995));knee=Vector((sign*.113,.048,.535));ankle=Vector((sign*.132,.066,.089));toe=Vector((sign*.134,-.084,.024))
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
 src_tip=[v.co.copy() for v in body.data.vertices if sign*v.co.x>.37 and v.co.z<.88]
 src_tip.sort(key=lambda p:p.z)
 source_tip=sum(src_tip[:max(1,len(src_tip)//10)],Vector())/max(1,len(src_tip)//10)
 MAP['hand_'+side]=similarity(HEAD['hand_'+side],donor_tip,wrist,source_tip)
 MAP['clavicle_'+side]=similarity(HEAD['clavicle_'+side],HEAD['upperarm_'+side],(sign*.012,.025,1.48),shoulder)
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
 arm_metric=min(seg_distance(shoulder,elbow)/.070,seg_distance(elbow,wrist)/.052,
                (p-wrist).length/.16 if p.z<wrist.z else 1e6)
 rx=float(np.interp(p.z,[.8,1.02,1.18,1.34,1.48,1.57],[.205,.18,.143,.16,.13,.055]))
 ry=float(np.interp(p.z,[.8,1.02,1.18,1.34,1.48,1.57],[.14,.14,.11,.14,.10,.055]))
 torso_metric=math.sqrt((p.x/rx)**2+((p.y-.020)/ry)**2)
 arm_blend=smooth(-.35,.35,torso_metric-arm_metric)
 if p.z<1.16 and abs(p.x)<.215:arm_blend=0.
 if p.z>1.58:arm_blend=0.
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
 if p.z>=1.03:core=torso_weights(p)
 else:
  hip=smooth(1.035,.855,p.z)
  knee=smooth(.602,.477,p.z)
  ankle=smooth(.145,.065,p.z)
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
parts=[];kinds={}
def active(o):
 bpy.ops.object.select_all(action='DESELECT');o.select_set(True);bpy.context.view_layer.objects.active=o
def mesh(name,verts,faces,material,uv=None):
 me=bpy.data.meshes.new(name);me.from_pydata(verts,[],faces);me.update()
 o=bpy.data.objects.new(name,me);bpy.context.collection.objects.link(o)
 if material:me.materials.append(material)
 for p in me.polygons:p.use_smooth=True
 layer=me.uv_layers.new(name='UVMap')
 for poly in me.polygons:
  for li in poly.loop_indices:
   v=me.loops[li].vertex_index
   layer.data[li].uv=uv[v] if uv else (verts[v][0]*2.5,verts[v][2]*2.5)
 parts.append(o);return o
def apply(o,mod):
 active(o);bpy.ops.object.modifier_apply(modifier=mod.name)
def shell(o,thick=.002):
 m=o.modifiers.new('TailoredThickness','SOLIDIFY');m.thickness=thick;m.offset=0
 apply(o,m)
def image_from(name,rgb):
 h,w=rgb.shape[:2];im=bpy.data.images.new(name,width=w,height=h,alpha=False)
 if name.endswith(('_Normal','_ORM')):im.colorspace_settings.name='Non-Color'
 rgba=np.ones((h,w,4),np.float32);rgba[:,:,:3]=rgb
 im.pixels.foreach_set(rgba.ravel());im.filepath_raw=str(ROOT/'Textures'/(name+'.png'));im.file_format='PNG';im.save();return im
def textile(name,color,rough=.78,metal=0,leather=False):
 size=1024;y,x=np.mgrid[0:size,0:size];rng=np.random.default_rng(607)
 height=(np.sin(x*np.pi/3)*np.sin(y*np.pi/3)*.45+np.sin((x+y)*np.pi/12)*.16)
 if leather:height=rng.normal(0,.16,(size,size))
 dy,dx=np.gradient(height);v=np.stack([-dx*.18,-dy*.18,np.ones_like(height)],axis=-1);v/=np.linalg.norm(v,axis=-1)[...,None]
 noise=rng.normal(0,.012,(size,size))
 base=np.clip(np.array(color)[None,None,:]*(1+(height*.07+noise)[:,:,None]),0,1).astype(np.float32)
 orm=np.empty_like(base);orm[:,:,0]=1;orm[:,:,1]=np.clip(rough+height*.025,0,1);orm[:,:,2]=metal
 imgs=[image_from(name+'_BaseColor',base),image_from(name+'_Normal',v*.5+.5),image_from(name+'_ORM',orm)]
 mat=bpy.data.materials.new(name);mat.use_nodes=True;n=mat.node_tree.nodes;l=mat.node_tree.links;bs=next((v for v in n if v.type=='BSDF_PRINCIPLED'),None) or n.new('ShaderNodeBsdfPrincipled');out=next((v for v in n if v.type=='OUTPUT_MATERIAL'),None) or n.new('ShaderNodeOutputMaterial');l.new(bs.outputs['BSDF'],out.inputs['Surface'])
 for im,kind in zip(imgs,['color','normal','orm']):
  t=n.new('ShaderNodeTexImage');t.image=im
  if kind=='color':l.new(t.outputs['Color'],bs.inputs['Base Color'])
  elif kind=='normal':
   im.colorspace_settings.name='Non-Color';nm=n.new('ShaderNodeNormalMap');l.new(t.outputs['Color'],nm.inputs['Color']);l.new(nm.outputs['Normal'],bs.inputs['Normal'])
  else:
   im.colorspace_settings.name='Non-Color';sep=n.new('ShaderNodeSeparateColor');l.new(t.outputs['Color'],sep.inputs['Color'])
   l.new(sep.outputs['Green'],bs.inputs['Roughness']);l.new(sep.outputs['Blue'],bs.inputs['Metallic'])
 return mat
suit=textile('Receptionist_Suit',(.058,.077,.100))
shirt=textile('Receptionist_Shirt',(.69,.685,.625),.84)
leather=textile('Receptionist_Shoes',(.035,.043,.052),.47,leather=True)
metal=textile('Receptionist_Badge',(.45,.41,.31),.43,.75)
lining=textile('Receptionist_Trim',(.135,.16,.18),.76)
def radial(z,t,offset=.01,cy=.025,limit=.30):
 direction=Vector((math.sin(t),-math.cos(t),0));origin=Vector((0,cy,z))
 hit=body_bvh.ray_cast(origin,direction,limit)
 radius=(hit[0]-origin).length if hit[0] is not None else .14
 return origin+direction*(radius+offset)
def garment_rings(name,levels,count,fn,mat,wrap=True):
 vs=[];uv=[]
 for j,z in enumerate(levels):
  for i in range(count+1):
   t=i/count;vs.append(tuple(fn(z,t)));uv.append((t*2,j/(len(levels)-1)*2))
 faces=[]
 for j in range(len(levels)-1):
  for i in range(count):
   a=j*(count+1)+i;faces.append((a,a+1,a+count+2,a+count+1))
 return mesh(name,vs,faces,mat,uv)
def gap(z):
 return float(np.interp(z,[.98,1.08,1.19,1.32,1.44,1.51,1.55],[.04,.03,.055,.38,.59,.84,1.05]))
# A continuous shoulder-to-sleeve shell follows the source body. The V02
# disconnected radial torso/yoke/sleeves had overlapping shoulder boundaries.
def opening(z):
 return float(np.interp(z,[1.005,1.16,1.30,1.42,1.49,1.55],[.001,.002,.038,.072,.080,.058]))
def clothing_surface(name,kind,mat,offset):
 o=body.copy();o.data=body.data.copy();bpy.context.collection.objects.link(o);o.name=name
 o.data.materials.clear();o.data.materials.append(mat)
 # The generated unitard and exposed arms have separate surface seams.
 # Union their volume before cutting the garment, keeping the source untouched.
 active(o)
 rem=o.modifiers.new('ContinuousFabricVolume','REMESH');rem.mode='VOXEL';rem.voxel_size=.005;rem.use_smooth_shade=True;apply(o,rem)
 bm=bmesh.new();bm.from_mesh(o.data)
 def keep(p):
  if kind=='jacket':
   bottom=1.005-.023*smooth(.26,.36,abs(p.x))
   if p.z<bottom or p.z>1.62:return False
   if p.z>1.54 and math.hypot(p.x,p.y-.005)<.058+(p.z-1.54)*2.:return False
   if p.y<-.008 and abs(p.x)<opening(p.z):return False
   return True
  return p.z>1.024 and p.z<1.567 and abs(p.x)<.205
 bmesh.ops.delete(bm,geom=[f for f in bm.faces if not all(keep(v.co) for v in f.verts)],context='FACES')
 bmesh.ops.delete(bm,geom=[v for v in bm.verts if not v.link_faces],context='VERTS')
 bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=.00008)
 bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
 bm.to_mesh(o.data);bm.free();active(o)
 dec=o.modifiers.new('TailoredSurfaceTopology','DECIMATE');dec.ratio=.33 if kind=='jacket' else .25;apply(o,dec)
 sm=o.modifiers.new('FabricRelaxation','SMOOTH');sm.factor=.6;sm.iterations=10;apply(o,sm)
 # Project the relaxed fabric back outside the intact source, then add ease.
 for v in o.data.vertices:
  hit=body_bvh.find_nearest(v.co)
  if hit[0] is not None:v.co=hit[0]+hit[1]*offset
 for poly in o.data.polygons:poly.use_smooth=True;poly.material_index=0
 o.data.update()
 sm=o.modifiers.new('TailoredBoundary','SMOOTH');sm.factor=.35;sm.iterations=3;apply(o,sm)
 if kind=='jacket':
  bm=bmesh.new();bm.from_mesh(o.data)
  for v in bm.verts:
   if v.is_boundary and v.co.z<1.025 and abs(v.co.x)<.26:v.co.z=1.005
  bm.to_mesh(o.data);bm.free()
 shell(o,.0028 if kind=='jacket' else .0015)
 parts.append(o);return o
jacket=clothing_surface('Receptionist_Blazer_Continuous','jacket',suit,.017)
clothing_surface('Receptionist_Shirt_Continuous','shirt',shirt,.006)
o=garment_rings('Receptionist_Shirt_CollarStand',np.linspace(1.548,1.579,5),64,lambda z,t:(.052*math.sin(2*math.pi*t),.005-.046*math.cos(2*math.pi*t),z),shirt);shell(o,.002)
for side,sign in [('l',1),('r',-1)]:
 a,e,w=(Vector(TARGET[side][n]) for n in ['shoulder','elbow','wrist'])
 # Shirt cuffs occupy the final wrist interval.
 c0=e.lerp(w,.90);c1=e.lerp(w,1.04);axis=(c1-c0).normalized()
 u=Vector((0,1,0));u=(u-axis*u.dot(axis)).normalized();v=axis.cross(u).normalized()
 def cuff(z,t,c0=c0,c1=c1,u=u,v=v):
  return c0.lerp(c1,z)+(u*math.cos(t*2*math.pi)*.037+v*math.sin(t*2*math.pi)*.034)
 o=garment_rings('Receptionist_Shirt_Cuff_'+side,np.linspace(0,1,5),48,cuff,shirt);shell(o,.002)
# Flared knee-length skirt; an overlapping back vent leaves stride allowance.
skirt_levels=np.linspace(.475,1.13,40)
skirt_ease=[]
for z in skirt_levels:
 rx=float(np.interp(z,[.475,.65,.85,.96,1.03,1.13],[.27,.255,.245,.23,.195,.160]))
 ry=float(np.interp(z,[.475,.65,.85,.96,1.03,1.13],[.180,.176,.179,.185,.162,.140]))
 max_x=float(np.interp(z,[.475,.9,1.01,1.13],[.24,.24,.225,.182]))
 region=[p for p in points if abs(p.z-z)<.018 and abs(p.x)<max_x]
 cover=max([math.sqrt((p.x/rx)**2+((p.y-.027)/ry)**2) for p in region] or [1.])
 scale=max(1.,cover+.09)
 skirt_ease.append((rx*scale,ry*scale))
def skirtpoint(z,t):
 theta=t*2*math.pi;f=(1.13-z)/.655
 rx=float(np.interp(z,skirt_levels,[v[0] for v in skirt_ease]))
 ry=float(np.interp(z,skirt_levels,[v[1] for v in skirt_ease]))
 radiuspleat=.0025*math.sin(theta*8)*max(0,(f-.3)/.7)
 return Vector(((rx+radiuspleat)*math.sin(theta),.027-(ry+radiuspleat)*math.cos(theta),z))
skirt=garment_rings('Receptionist_Skirt',skirt_levels,112,skirtpoint,suit)
# Separate the back vent below the knee-side opening, leave overlap flap geometry.
bm=bmesh.new();bm.from_mesh(skirt.data)
cut=[]
for f in bm.faces:
 c=f.calc_center_median()
 if c.z<.68 and c.y>.13 and abs(c.x)<.009:cut.append(f)
bmesh.ops.delete(bm,geom=cut,context='FACES');bm.to_mesh(skirt.data);bm.free()
shell(skirt,.0026);kinds[skirt.name]='skirt'
o=garment_rings('Receptionist_Skirt_BackVentUnderlap',np.linspace(.473,.70,14),12,lambda z,t:skirtpoint(z,.479+t*.061)+Vector((0,-.004,0)),suit,False);shell(o,.002);kinds[o.name]='skirt'
o=garment_rings('Receptionist_Skirt_Waistband',np.linspace(1.092,1.13,5),96,lambda z,t:Vector(skirtpoint(z,t))+Vector((math.sin(t*2*math.pi)*.003,-math.cos(t*2*math.pi)*.003,0)),suit);shell(o,.003);kinds[o.name]='skirt'
# Lapels are real folded strips, not painted onto the jacket.
def frontpoint(x,z,offset):
 hit=body_bvh.ray_cast(Vector((x,-.5,z)),Vector((0,1,0)),.8)
 return Vector((x,(hit[0].y if hit[0] is not None else -.050)-offset,z))
for sign in [-1,1]:
 vs=[];uv=[]
 for j,z in enumerate(np.linspace(1.158,1.534,34)):
  x=opening(z)
  width=float(np.interp(z,[1.158,1.3,1.44,1.466,1.534],[.003,.035,.043,.027,.024]))
  for i in range(7):
   f=i/6;v=frontpoint(sign*(x+width*f),z,.025+.005*math.sin(f*math.pi))
   vs.append(tuple(v));uv.append((f,j/33*2))
 faces=[(j*7+i,j*7+i+1,(j+1)*7+i+1,(j+1)*7+i) for j in range(33) for i in range(6)]
 o=mesh('Receptionist_Lapel_'+str(sign),vs,faces,suit,uv);shell(o,.0025)
 vs=[(sign*.016,-.046,1.577),(sign*.050,-.048,1.569),(sign*.068,-.075,1.516),(sign*.033,-.081,1.536)]
 o=mesh('Receptionist_Shirt_CollarTip_'+str(sign),vs,[(0,1,2,3)],shirt);shell(o,.002)

def block(name,center,size,mat,bevel=.001):
 bpy.ops.mesh.primitive_cube_add(size=1,location=center);o=bpy.context.object;o.name=name;o.dimensions=size
 bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
 if bevel:
  m=o.modifiers.new('EdgeRadius','BEVEL');m.width=bevel;m.segments=3;apply(o,m)
 world=o.matrix_world.copy()
 for v in o.data.vertices:v.co=world@v.co
 o.matrix_world=Matrix.Identity(4);o.data.materials.append(mat)
 if not o.data.uv_layers:o.data.uv_layers.new()
 parts.append(o);return o
for z in [1.18,1.107,1.04]:
 p=radial(z,0,.022)
 block('Receptionist_Blazer_Button',p,(.011,.004,.011),metal,.003)
for z in [1.43,1.365,1.3,1.235]:
 p=radial(z,0,.008)
 block('Receptionist_Shirt_Button',p,(.006,.002,.006),shirt,.002)
for sign in [-1,1]:
 p=radial(1.112,sign*.78,.022)
 block('Receptionist_PocketWelt_'+str(sign),p,(.064,.003,.010),lining,.001)
badge=radial(1.394,.58,.026)
block('Receptionist_NameBadge',badge,(.060,.0035,.023),metal,.002)
# Tiny relief lettering is an independent object following the same chest weights.
cu=bpy.data.curves.new('BadgeType','FONT');cu.body='M / RECEPTION';cu.align_x='CENTER';cu.size=.006;cu.extrude=.00015
txt=bpy.data.objects.new('Receptionist_BadgeLettering',cu);bpy.context.collection.objects.link(txt)
txt.location=badge+Vector((0,-.0025,-.0015));txt.rotation_euler=(math.pi/2,0,0);active(txt);bpy.ops.object.convert(target='MESH')
world=txt.matrix_world.copy()
for v in txt.data.vertices:v.co=world@v.co
txt.matrix_world=Matrix.Identity(4);txt.data.materials.append(lining);parts.append(txt)
# Closed-toe flats, authored as smooth envelopes over feet; original feet remain intact.
for sign,side in [(1,'l'),(-1,'r')]:
 o=body.copy();o.data=body.data.copy();bpy.context.collection.objects.link(o);o.name='Receptionist_FlatShoe_'+side
 bm=bmesh.new();bm.from_mesh(o.data)
 bmesh.ops.delete(bm,geom=[f for f in bm.faces if any(v.co.z>.126 or sign*v.co.x<.035 for v in f.verts)],context='FACES')
 bmesh.ops.delete(bm,geom=[v for v in bm.verts if not v.link_faces],context='VERTS')
 bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=.00003)
 bmesh.ops.holes_fill(bm,edges=[e for e in bm.edges if e.is_boundary],sides=0)
 bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.normal_update()
 for v in bm.verts:
  # Envelope expands forefoot and merges the toe grooves visually.
  v.co+=v.normal*.006
  if v.co.z<.012:v.co.z=.004
 bm.to_mesh(o.data);bm.free()
 active(o)
 rem=o.modifiers.new('SmoothShoeEnvelope','REMESH');rem.mode='VOXEL';rem.voxel_size=.0045;rem.use_smooth_shade=True;apply(o,rem)
 dec=o.modifiers.new('ShoeSurfaceTopology','DECIMATE');dec.ratio=.23;apply(o,dec)
 sm=o.modifiers.new('LeatherSurface','SMOOTH');sm.factor=.8;sm.iterations=7;apply(o,sm)
 sub=o.modifiers.new('UpperFinish','SUBSURF');sub.levels=1;apply(o,sub)
 for v in o.data.vertices:
  v.co.x=sign*.134+(v.co.x-sign*.134)*1.08
  v.co.y=-.005+(v.co.y+.005)*1.045
  v.co.z=-.008+(v.co.z+.008)*1.05
 # Reopen the ankle after voxelizing a closed volume.
 bm=bmesh.new();bm.from_mesh(o.data)
 bmesh.ops.delete(bm,geom=[f for f in bm.faces if all(v.co.z>.120 for v in f.verts)],context='FACES')
 bmesh.ops.delete(bm,geom=[v for v in bm.verts if not v.link_faces],context='VERTS')
 bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(o.data);bm.free()
 o.data.materials.clear();o.data.materials.append(leather)
 for f in o.data.polygons:f.material_index=0
 shell(o,.003)
 active(o);bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT');bpy.ops.uv.smart_project(island_margin=.025);bpy.ops.object.mode_set(mode='OBJECT')
 parts.append(o);kinds[o.name]='shoe'
# Skin every independently editable garment in source A-pose, then invert the
# blended donor-fit transform so the saved rig keeps the exact Nurse rest frame.
def bind(o,allweights):
 old_normals=[v.vector.copy() for v in o.data.corner_normals]
 normal_maps=[matrix(ws).to_3x3().transposed() for ws in allweights]
 mapped_normals=[(normal_maps[loop.vertex_index]@normal).normalized() for loop,normal in zip(o.data.loops,old_normals)]
 o.vertex_groups.clear()
 for n in sorted({n for w in allweights for n in w}):o.vertex_groups.new(name=n)
 for v,ws in zip(o.data.vertices,allweights):
  v.co=matrix(ws).inverted_safe()@v.co
  for n,w in ws.items():o.vertex_groups[n].add([v.index],w,'REPLACE')
 o.data.update();o.data.normals_split_custom_set(mapped_normals)
 o.parent=rig;o.matrix_parent_inverse=rig.matrix_world.inverted()
 mod=o.modifiers.new('NurseNativeSkin','ARMATURE');mod.object=rig
def skirt_weights(p):
 k=max(0,min(.74,(1.12-p.z)/.58))
 side=max(.05,min(.95,.5+p.x/.42))
 return norm({'pelvis':1-k,'thigh_l':k*side,'thigh_r':k*(1-side)})
for o in parts:
 ws=[skirt_weights(v.co) if kinds.get(o.name)=='skirt' else body_sample(v.co) for v in o.data.vertices]
 bind(o,ws)
body.name='Receptionist_CompleteBody';body.data.materials[0].name='Receptionist_Skin'
bind(body,body_weights)
body.data.calc_loop_triangles()
rest_points=[v.co.copy() for v in body.data.vertices]
rest_tris=[tuple(t.vertices) for t in body.data.loop_triangles]
rest_bvh=BVHTree.FromPolygons(rest_points,rest_tris,all_triangles=True)
for o in parts:
 if o.name not in ['Receptionist_Blazer_Continuous','Receptionist_Shirt_Continuous']:continue
 count=len(o.data.vertices)//2
 clearance=.009 if 'Blazer' in o.name else .003
 for i in range(count):
  v=o.data.vertices[i];h=rest_bvh.find_nearest(v.co)
  if h[0] is None:continue
  signed=(v.co-h[0]).dot(h[1])
  if signed<clearance:
   delta=h[1]*(clearance-signed)
   v.co+=delta;o.data.vertices[i+count].co+=delta
 o.data.update();o.data.normals_split_custom_set([(0,0,0)]*len(o.data.loops))
# Retain authored independent objects; donor geometry is not in delivered character.
bpy.data.objects.remove(donor,do_unlink=True)
for o in list(bpy.context.scene.objects):
 if o not in parts+[body,rig]:bpy.data.objects.remove(o,do_unlink=True)
rig.name='root'
rig['source_world_matrix']=[v for row in rig.matrix_world for v in row]
rig.show_in_front=True
for m in list(bpy.data.materials):
 if not m.users:bpy.data.materials.remove(m)
for im in list(bpy.data.images):
 if not im.users:bpy.data.images.remove(im)
bpy.context.scene.unit_settings.system='METRIC';bpy.context.scene.unit_settings.scale_length=1.
bpy.ops.object.select_all(action='SELECT');bpy.context.view_layer.objects.active=body
# Source contains complete body and separate clothing, with original Meshy UVs.
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'Authoring/FacelessReceptionist_V02.blend'))
receipt={'stage':'authored_v02','source':'../Source/Meshy_AI_Faceless_Mannequin_in_1007155702_texture.glb','source_triangles':len(bodytris),'skeleton_source':'/Game/ZombieFemale/Asset/Meshes/SK_ZombieFemale','rig_bones':len(rig.data.bones),'rig_object_matrix':[list(x) for x in rig.matrix_world],'fit_targets':TARGET,'body_vertices':len(body.data.vertices),'parts':[{'name':o.name,'vertices':len(o.data.vertices),'triangles':sum(len(p.vertices)-2 for p in o.data.polygons),'materials':[m.name for m in o.data.materials]} for o in parts],'runtime_tested':False,'rendered':False,'notes':['Full original Meshy body preserved. Anatomical trunk/legs, side-restricted hand transfer, continuous jacket shell.','Clothing uses skin deformation; no runtime cloth simulation has been authored.','No visual or gameplay acceptance performed.']}
(ROOT/'authoring_receipt.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
print('RECEPTIONIST_AUTHORING_SAVED '+json.dumps({'body_triangles':len(bodytris),'parts':len(parts),'garment_triangles':sum(x['triangles'] for x in receipt['parts']),'bones':len(rig.data.bones)}),flush=True)
