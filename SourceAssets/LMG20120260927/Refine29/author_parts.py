"""Refine29: source-face preserving component authoring and textile baking.

Art asset only. Seam locations are inferred from the supplied screenshots; no
internal mechanical construction is claimed. Raw Meshy28 and active UE remain
untouched. Glove StitchWear / companion methods inform the sewn surface fields.
"""
import bpy,bmesh,json,math,sys
import numpy as np
from pathlib import Path
from mathutils import Vector
from mathutils.geometry import delaunay_2d_cdt
R=Path(__file__).resolve().parent
SRC=R.parent/'MeshyRetry28/Meshy/lmg201_new_reference_smooth_v01/downloads'
for folder in ['Textures','Exports','Parts','Authoring']:(R/folder).mkdir(exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
scene=bpy.context.scene;scene.unit_settings.system='METRIC';scene.unit_settings.scale_length=1
scene.render.engine='CYCLES';scene.cycles.device='CPU';scene.cycles.samples=8
scene.render.bake.margin=12;scene.render.bake.use_clear=True
GAME=bpy.data.collections.new('GAME - split components');scene.collection.children.link(GAME)
HIGH=bpy.data.collections.new('HIGH - pouch baking source');scene.collection.children.link(HIGH)
AUTHOR=bpy.data.collections.new('AUTHOR - seam guides');scene.collection.children.link(AUTHOR)
parts=[];records=[]

def active(o):
 bpy.ops.object.select_all(action='DESELECT');o.hide_set(False);o.select_set(True);bpy.context.view_layer.objects.active=o

class Nodes:
 def __init__(self,mat):self.n=mat.node_tree.nodes;self.l=mat.node_tree.links
 def node(self,kind,**kw):
  n=self.n.new(kind)
  for k,v in kw.items():setattr(n,k,v)
  return n
 def put(self,n,key,v):
  if isinstance(v,(float,int,list,tuple)):n.inputs[key].default_value=v
  else:self.l.new(v,n.inputs[key])
 def op(self,op,a,b=None):
  n=self.node('ShaderNodeMath',operation=op);self.put(n,0,a)
  if b is not None:self.put(n,1,b)
  return n.outputs[0]
 def mix(self,a,b,f):
  n=self.node('ShaderNodeMixRGB');self.put(n,0,f);self.put(n,1,a);self.put(n,2,b);return n.outputs[0]
 def mul(self,a,b):
  n=self.node('ShaderNodeMixRGB',blend_type='MULTIPLY');self.put(n,0,1.);self.put(n,1,a);self.put(n,2,b);return n.outputs[0]
 def sep(self,value):
  n=self.node('ShaderNodeSeparateXYZ');self.put(n,0,value);return n.outputs
 def combine(self,r,g,b):
  n=self.node('ShaderNodeCombineXYZ');self.put(n,0,r);self.put(n,1,g);self.put(n,2,b);return n.outputs[0]

def image(path,linear=False):
 im=bpy.data.images.load(str(path),check_existing=True)
 im.colorspace_settings.name='Non-Color' if linear else 'sRGB'
 return im

BASE=image(SRC/'texture_urls_0_base_color.png')
NORMAL=image(SRC/'texture_urls_0_normal.png',True)

def constant(name,color,rough=.42,metal=.65):
 m=bpy.data.materials.new(name);m.use_nodes=True
 b=m.node_tree.nodes.get('Principled BSDF');b.inputs['Base Color'].default_value=(*color,1);b.inputs['Roughness'].default_value=rough;b.inputs['Metallic'].default_value=metal
 return m

CAP=constant('M_201_CutInterior',(0.017,.020,.023),.48,.65)
NEW=constant('M_201_RebuiltSteel',(0.022,.026,.031),.37,.78)
POLY=constant('M_201_RebuiltPolymer',(.013,.016,.019),.65,0)

def author_finish(kind):
 m=bpy.data.materials.new('AUTHOR_'+kind);m.use_nodes=True;ns=Nodes(m);op=ns.op
 bs=ns.n.get('Principled BSDF');out=ns.n.get('Material Output')
 uv=ns.node('ShaderNodeUVMap',uv_map='UV0').outputs[0]
 t=ns.node('ShaderNodeTexImage');t.image=BASE;ns.put(t,'Vector',uv)
 normal=ns.node('ShaderNodeTexImage');normal.image=NORMAL;ns.put(normal,'Vector',uv)
 lum=ns.node('ShaderNodeRGBToBW');ns.put(lum,0,t.outputs[0])
 if kind=='Steel':
  # Compress Meshy's broad white edge paint while retaining its fine markings.
  tone=op('ADD',.48,op('MULTIPLY',lum.outputs[0],.62))
  color=ns.mul((.022,.028,.035,1),tone)
  rough=op('ADD',.35,op('MULTIPLY',lum.outputs[0],.065));metal=.78
 elif kind=='Polymer':
  color=ns.mul((.019,.023,.027,1),op('ADD',.65,op('MULTIPLY',lum.outputs[0],.3)))
  rough=op('ADD',.61,op('MULTIPLY',lum.outputs[0],.11));metal=0.
 else:
  color=t.outputs[0];rough=.38;metal=.87
 ns.put(bs,'Base Color',color);ns.put(bs,'Roughness',rough);ns.put(bs,'Metallic',metal)
 ns.put(bs,'Specular IOR Level',.38)
 # Only low-amplitude normal noise on the locally faired panels is attenuated.
 # Strong source grooves / screw features and untouched regions retain strength.
 source=ns.sep(normal.outputs[0]);dx=op('SUBTRACT',source[0],.5);dy=op('SUBTRACT',source[1],.5)
 magnitude=op('SQRT',op('ADD',op('MULTIPLY',dx,dx),op('MULTIPLY',dy,dy)))
 preserve=op('MINIMUM',1.,op('DIVIDE',magnitude,.065))
 fair=ns.node('ShaderNodeAttribute',attribute_name='SurfaceFairing').outputs['Fac']
 local=op('MULTIPLY',op('MULTIPLY',fair,op('SUBTRACT',1.,preserve)),.55)
 clean=ns.mix(normal.outputs[0],(.5,.5,1.,1.),local)
 nm=ns.node('ShaderNodeNormalMap',uv_map='UV0');ns.put(nm,'Color',clean);ns.put(bs,'Normal',nm.outputs[0])
 return m,dict(BaseColor=color,ORM=ns.combine(1.,rough,metal)),bs,out

FINISH={k:author_finish(k) for k in ('Steel','Polymer','Cartridges')}

# Each row stores P(3), source loop normal(3), UV(2), local fairing(1).
d=np.load(R/'faired_surface.npz');v=d['vertices'];f=d['faces']
tri=np.concatenate([v[f],d['normals'],d['uv'],d['fairing'][:,:,None]],axis=2)
sid=np.arange(len(tri),dtype=np.int32)
cap_sequence=0

def cut_plane(t,ids,normal,offset,cap_id):
 """Exact triangle clipping; interpolate every corner attribute on new edges."""
 dist=t[:,:,:3]@np.array(normal)-offset
 inside=np.all(dist<=1e-9,axis=1);outside=np.all(dist>=-1e-9,axis=1)&~inside
 ia=[t[inside]];oa=[t[outside]];ii=[ids[inside]];oi=[ids[outside]];segments=[]
 for idx in np.flatnonzero(~inside&~outside):
  p=t[idx];dd=dist[idx];cross=[]
  for j in range(3):
   k=(j+1)%3
   if (dd[j]<0)!=(dd[k]<0):cross.append(p[j,:3]+(p[k,:3]-p[j,:3])*(dd[j]/(dd[j]-dd[k])))
  if len(cross)==2 and np.linalg.norm(cross[0]-cross[1])>1e-9:segments.append(cross)
  for keep,arr,idxarr in [(True,ia,ii),(False,oa,oi)]:
   poly=[]
   for j in range(3):
    k=(j+1)%3;aj=(dd[j]<=0) if keep else (dd[j]>=0);ak=(dd[k]<=0) if keep else (dd[k]>=0)
    if aj:poly.append(p[j])
    if aj!=ak:poly.append(p[j]+(p[k]-p[j])*(dd[j]/(dd[j]-dd[k])))
   if len(poly)>=3:
    q=np.array([[poly[0],poly[j],poly[j+1]] for j in range(1,len(poly)-1)])
    good=np.linalg.norm(np.cross(q[:,1,:3]-q[:,0,:3],q[:,2,:3]-q[:,0,:3]),axis=1)>1e-13;q=q[good]
    arr.append(q);idxarr.append(np.full(len(q),ids[idx],np.int32))
 if segments:
  caps=planar_caps(np.array(segments),normal,offset,t.shape[2])
  ia.append(caps);ii.append(np.full(len(caps),cap_id,np.int32))
  other=caps[:,::-1].copy();other[:,:,3:6]*=-1;oa.append(other);oi.append(np.full(len(caps),cap_id,np.int32))
 return np.concatenate(ia),np.concatenate(ii),np.concatenate(oa),np.concatenate(oi)

def planar_caps(segments,normal,offset,width):
 """Constrained planar triangulation, even-odd region rule preserves holes."""
 n=np.asarray(normal,float);length=np.linalg.norm(n);n/=length
 helper=np.array((0.,0.,1.)) if abs(n[2])<.8 else np.array((0.,1.,0.))
 u=np.cross(helper,n);u/=np.linalg.norm(u);w=np.cross(n,u);origin=n*(offset/length)
 points,idx=np.unique(np.round(segments.reshape(-1,3),7),axis=0,return_inverse=True)
 edges=idx.reshape(-1,2);edges=np.unique(np.sort(edges,axis=1),axis=0);edges=edges[edges[:,0]!=edges[:,1]]
 coords=np.c_[(points-origin)@u,(points-origin)@w]
 result=delaunay_2d_cdt([Vector(p) for p in coords],edges.tolist(),[],0,1e-8)
 vertices=np.array(result[0]);faces=result[2]
 if not faces:return np.zeros((0,3,width))
 ff=np.array([p for p in faces if len(p)==3],int);c=vertices[ff].mean(1);odd=np.zeros(len(c),bool)
 for a,b in coords[edges]:
  cross=((a[1]>c[:,1])!=(b[1]>c[:,1]))
  if abs(b[1]-a[1])>1e-14:odd^=cross&(c[:,0]<(b[0]-a[0])*(c[:,1]-a[1])/(b[1]-a[1])+a[0])
 ff=ff[odd];q=vertices[ff];area=(q[:,1,0]-q[:,0,0])*(q[:,2,1]-q[:,0,1])-(q[:,1,1]-q[:,0,1])*(q[:,2,0]-q[:,0,0])
 q[area<0]=q[area<0,::-1];out=np.zeros((len(q),3,width));out[:,:,:3]=origin+q[:,:,0,None]*u+q[:,:,1,None]*w;out[:,:,3:6]=n;out[:,:,6:8]=q*3
 return out

def volume(planes):
 global tri,sid,cap_sequence
 keep=tri;kid=sid;outside=[];oid=[];new_caps=[]
 for n,c in planes:
  cap_sequence-=1;new_caps.append(cap_sequence)
  keep,kid,other,otherid=cut_plane(keep,kid,n,c,cap_sequence)
  # Intermediate outside fragments are a partition of one receiver. Their
  # temporary internal caps must not survive when those fragments are reunited.
  original=~np.isin(otherid,new_caps);outside.append(other[original]);oid.append(otherid[original])
 # The only new caps belonging to the remainder are the reverse of the FINAL
 # extracted component's cut surfaces. This avoids overlapping internal sheets.
 capmask=np.isin(kid,new_caps);reverse=keep[capmask,::-1].copy();reverse[:,:,3:6]*=-1
 outside.append(reverse);oid.append(kid[capmask])
 tri=np.concatenate(outside);sid=np.concatenate(oid)
 return keep,kid

def box(x0=None,x1=None,y0=None,y1=None,z0=None,z1=None):
 # Bounds below represent individually authored mating seams, not loose islands.
 result=[]
 for axis,(lo,hi) in enumerate([(x0,x1),(y0,y1),(z0,z1)]):
  if lo is not None:n=[0,0,0];n[axis]=-1;result.append((n,-lo))
  if hi is not None:n=[0,0,0];n[axis]=1;result.append((n,hi))
 return result

def make_part(name,t,ids,pivot,kind,planes=None):
 if len(t)==0:return None
 coords,iv=np.unique(np.round(t[:,:,:3].reshape(-1,3),7),axis=0,return_inverse=True)
 faces=iv.reshape(-1,3)
 # Intersection vertices may coincide after the shared-position weld. Remove
 # collapsed sliver triangles before passing custom normals to Blender.
 keep=(faces[:,0]!=faces[:,1])&(faces[:,1]!=faces[:,2])&(faces[:,0]!=faces[:,2])
 keep &= np.linalg.norm(np.cross(coords[faces[:,1]]-coords[faces[:,0]],coords[faces[:,2]]-coords[faces[:,0]]),axis=1)>1e-13
 faces=faces[keep];t=t[keep];ids=ids[keep]
 _,unique=np.unique(np.sort(faces,axis=1),axis=0,return_index=True);unique.sort()
 faces=faces[unique];t=t[unique];ids=ids[unique]
 me=bpy.data.meshes.new(name);me.from_pydata(coords.tolist(),[],faces.tolist());me.update()
 uv=me.uv_layers.new(name='UV0');uv.data.foreach_set('uv',t[:,:,6:8].astype(np.float32).ravel())
 fair=me.attributes.new('SurfaceFairing','FLOAT','CORNER');fair.data.foreach_set('value',t[:,:,8].astype(np.float32).ravel())
 orig=me.attributes.new('SourceFace','INT','FACE');orig.data.foreach_set('value',ids.astype(np.int32))
 me.materials.append(FINISH[kind][0]);me.materials.append(CAP)
 ob=bpy.data.objects.new(name,me);GAME.objects.link(ob)
 # Every cut was capped in its own plane before any subsequent cut. This avoids
 # filling a multi-plane boundary with a warped fan or blocking intended holes.
 for i,p in enumerate(me.polygons):
  p.material_index=1 if ids[i]<0 else 0;p.use_smooth=bool(ids[i]>=0)
 me.update(calc_edges=True)
 loopnorm=t[:,:,3:6].reshape(-1,3);loopnorm/=np.maximum(np.linalg.norm(loopnorm,axis=1,keepdims=True),1e-12)
 me.normals_split_custom_set(loopnorm.tolist())
 shift=Vector(pivot)
 for p in ob.data.vertices:p.co-=shift
 ob.location=shift;ob['part_id']=name;ob['origin_role']='reference mating interface';ob['source']='MeshyRetry28';ob['candidate_only']=True
 parts.append(ob)
 rec=dict(part=name,finish=kind,pivot=list(pivot),source_faces=int(np.sum(ids>=0)),new_cut_cap_faces=sum(p.material_index==1 for p in me.polygons),seam_planes=planes or [])
 records.append(rec);print('PART_AUTHORED',name,len(me.polygons),flush=True)
 return ob

def extract(name,planes,pivot,kind='Steel'):
 t,ids=volume(planes);return make_part(name,t,ids,pivot,kind,planes)

# Start with local end fittings and the visually exposed hanging components.
extract('FlashHider',box(x1=-.875),(-.875,.005,.104))
extract('FrontSight',box(x0=-.674,x1=-.585,z0=.071),(-.626,.005,.104))
bad,badids=volume(box(x1=-.675,z1=.071))
np.savez_compressed(R/'Authoring/replaced_front_hardware.npz',triangles=bad,source_faces=badids)
extract('GasTube',box(x1=-.454,z1=.071),(-.454,.005,.044))
extract('Barrel',box(x1=-.454),(-.454,.005,.104))
bag=extract('AmmoBag',box(x0=.026,x1=.214,z1=-.008),(.12,0,-.008),'Polymer')
extract('AmmoBelt',box(x0=.015,x1=.212,y1=-.032,z0=-.008,z1=.148),(.118,-.032,.14),'Cartridges')
extract('Stock',box(x0=.528),(.528,.01,.077),'Polymer')
extract('PistolGrip',box(x0=.318,x1=.50,z1=-.010),(.361,.009,-.010),'Polymer')
extract('TriggerGuardAssembly',box(x0=.214,x1=.318,z1=-.009),(.270,.007,-.009))
extract('RearSight',box(x0=.252,x1=.307,z0=.174),(.280,.008,.174))
extract('TopCover',box(x0=-.138,x1=.204)+[((.045,0,-1),-.142)],(-.126,.011,.148))
extract('TopRail',box(x0=.213,x1=.485,z0=.160),(.35,.013,.160))
extract('CarryHandle',box(x0=-.20,x1=.218,y0=.059,z0=.002,z1=.124),(-.147,.059,.101),'Polymer')
# Rear guard mating edge follows the sloping joint visible in the reference.
extract('Handguard',box(x1=-.09)+[((1,0,.48),-.064)],(-.122,.01,.055))
receiver=make_part('Receiver',tri,sid,(0,0,0),'Steel')

def built_mesh(name,verts,faces,pivot,mat=NEW):
 me=bpy.data.meshes.new(name);me.from_pydata(verts,[],faces);me.update();me.materials.append(mat)
 ob=bpy.data.objects.new(name,me);GAME.objects.link(ob)
 for p in me.polygons:p.use_smooth=True
 active(ob);bm=bmesh.new();bm.from_mesh(me);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(me);bm.free()
 # Explicit generated UV for all newly built faces.
 bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT');bpy.ops.uv.smart_project(angle_limit=math.radians(66),island_margin=.02);bpy.ops.object.mode_set(mode='OBJECT')
 bevel=ob.modifiers.new('Machined edge rounding','BEVEL');bevel.width=.00065;bevel.segments=3;bevel.limit_method='ANGLE';bevel.angle_limit=.7
 bpy.ops.object.modifier_apply(modifier=bevel.name)
 normal=ob.modifiers.new('Weighted hard-surface normals','WEIGHTED_NORMAL');normal.keep_sharp=True;normal.weight=35
 bpy.ops.object.modifier_apply(modifier=normal.name)
 shift=Vector(pivot)
 for p in me.vertices:p.co-=shift
 ob.location=shift;ob['part_id']=name;ob['source']='local reference-shape reconstruction';ob['candidate_only']=True
 parts.append(ob);records.append(dict(part=name,finish=mat.name,pivot=list(pivot),locally_rebuilt=True))
 return ob

def lathe(name,profile,center,pivot,segments=64):
 # Cross-section is only the local external art silhouette; blind inner recess.
 verts=[]
 for x,r in profile:
  verts.extend((x,center[0]+r*math.cos(j*2*math.pi/segments),center[1]+r*math.sin(j*2*math.pi/segments)) for j in range(segments))
 faces=[]
 for i in range(len(profile)-1):
  for j in range(segments):a=i*segments+j;b=i*segments+(j+1)%segments;faces.append((a,b,b+segments,a+segments))
 faces.extend([tuple(reversed(range(segments))),tuple((len(profile)-1)*segments+j for j in range(segments))])
 return built_mesh(name,verts,faces,pivot)

lathe('GasFrontPlug',[(-.705,.013),(-.703,.019),(-.697,.019),(-.695,.014),(-.683,.014),(-.680,.017),(-.674,.017)],(.006,.044),(-.675,.006,.044))
# Visible lower eyelet rebuilt as a clean annulus, retaining the intentional hole.
verts=[];steps=64
for y,r in [(-.000,.012),(.012,.012),(.012,.006),(-.000,.006)]:
 for j in range(steps):a=j*2*math.pi/steps;verts.append((-.697+r*math.cos(a),y,.022+r*math.sin(a)))
faces=[]
for k in range(4):
 for j in range(steps):faces.append((k*steps+j,k*steps+(j+1)%steps,((k+1)%4)*steps+(j+1)%steps,((k+1)%4)*steps+j))
built_mesh('GasFrontEyelet',verts,faces,(-.697,.006,.032))
# The sight collar previously shared the monolithic barrel. This hidden sleeve
# completes the barrel's own surface when the sight component is removed.
lathe('BarrelUnderSight',[(-.674,.0177),(-.585,.0177)],(.005,.104),(-.454,.005,.104))

def join_named(names,result):
 objs=[o for o in parts if o.name in names]
 if not objs:return
 active(objs[0])
 for o in objs:o.select_set(True)
 bpy.ops.object.join();joined=bpy.context.object;joined.name=result
 for o in objs[1:]:parts.remove(o)
 return joined

join_named(['Barrel','BarrelUnderSight'],'Barrel')
join_named(['GasFrontPlug','GasFrontEyelet'],'GasFrontHardware')

def baked_material(name,maps,uvname='UV0',cloth=False):
 m=bpy.data.materials.new(name);m.use_nodes=True;ns=Nodes(m);bs=ns.n.get('Principled BSDF');uv=ns.node('ShaderNodeUVMap',uv_map=uvname).outputs[0]
 for kind,im in maps.items():
  t=ns.node('ShaderNodeTexImage');t.image=im;ns.put(t,'Vector',uv)
  if kind=='BaseColor':ns.put(bs,'Base Color',t.outputs[0])
  elif kind=='ORM':
   q=ns.sep(t.outputs[0]);ns.put(bs,'Roughness',q[1]);ns.put(bs,'Metallic',q[2])
  elif kind=='Normal':
   q=ns.node('ShaderNodeNormalMap',uv_map=uvname);ns.put(q,'Color',t.outputs[0]);ns.put(bs,'Normal',q.outputs[0])
  elif kind=='Relief' and cloth:
   q=ns.sep(t.outputs[0]);ns.put(bs,'Sheen Weight',ns.op('MULTIPLY',q[1],.30));ns.put(bs,'Sheen Roughness',.8)
 bs.inputs['Specular IOR Level'].default_value=.35
 return m

def bake_atlas():
 cached={k:R/'Textures'/('T_201_R29_Surface_'+k+'.png') for k in ['BaseColor','ORM','Normal']}
 if all(p.exists() for p in cached.values()):
  maps={k:image(p,k!='BaseColor') for k,p in cached.items()};mat=baked_material('M_201_R29_Surface',maps)
  for ob in parts:
   if ob!=bag and ob.data.attributes.get('SourceFace'):ob.data.materials[0]=mat
  print('SURFACE_BAKES_RESUMED',flush=True);return maps
 # Temporary joined source surfaces: retain UV0 and exclude new closure faces,
 # which have an independent untextured interior material.
 copies=[]
 for ob in parts:
  if ob==bag or not ob.data.attributes.get('SourceFace'):continue
  cp=ob.copy();cp.data=ob.data.copy();scene.collection.objects.link(cp)
  bm=bmesh.new();bm.from_mesh(cp.data);bmesh.ops.delete(bm,geom=[f for f in bm.faces if not cp.data.materials[f.material_index].name.startswith('AUTHOR_')],context='FACES');bm.to_mesh(cp.data);bm.free();copies.append(cp)
 active(copies[0])
 for cp in copies:cp.select_set(True)
 bpy.ops.object.join();low=bpy.context.object;low.name='BAKE_ONLY_OriginalUVSurfaces'
 mats=[m for m in low.data.materials if m and m.name.startswith('AUTHOR_')]
 maps={}
 for label in ['BaseColor','ORM','Normal']:
  im=bpy.data.images.new('T_201_R29_Surface_'+label,width=4096,height=4096,alpha=False)
  im.colorspace_settings.name='sRGB' if label=='BaseColor' else 'Non-Color'
  for kind,(m,fields,bs,out) in FINISH.items():
   ns=Nodes(m);target=ns.node('ShaderNodeTexImage');target.image=im;ns.n.active=target
   if label=='Normal':ns.l.new(bs.outputs[0],out.inputs['Surface'])
   else:
    emit=ns.node('ShaderNodeEmission');ns.put(emit,'Color',fields[label]);ns.l.new(emit.outputs[0],out.inputs['Surface'])
  active(low);scene.render.bake.use_selected_to_active=False;scene.render.bake.use_clear=True
  print('SURFACE_BAKE',label,flush=True);bpy.ops.object.bake(type='NORMAL' if label=='Normal' else 'EMIT',uv_layer='UV0',normal_space='TANGENT')
  im.filepath_raw=str(R/'Textures'/(im.name+'.png'));im.file_format='PNG';im.save();maps[label]=im
 bpy.data.objects.remove(low,do_unlink=True)
 mat=baked_material('M_201_R29_Surface',maps)
 for ob in parts:
  if ob!=bag and ob.data.attributes.get('SourceFace'):ob.data.materials[0]=mat
 return maps

def smooth(a,b,x):
 t=np.clip((x-a)/(b-a),0,1);return t*t*(3-2*t)

def seam_field(u,z,half,center,rounding):
 # Rounded panel path, distance and accumulated arc, matching sewn-panel layout.
 path=[]
 for cx,cz,start in [(half[0]-rounding,half[1]-rounding,0),(-half[0]+rounding,half[1]-rounding,90),(-half[0]+rounding,-half[1]+rounding,180),(half[0]-rounding,-half[1]+rounding,270)]:
  for j in range(13):
   a=math.radians(start+j*90/12);path.append((center[0]+cx+rounding*math.cos(a),center[1]+cz+rounding*math.sin(a)))
 path=np.array(path);best=np.full(len(u),1e3);arc=np.zeros(len(u));acc=0.;p=np.c_[u,z]
 for i in range(len(path)):
  a=path[i];b=path[(i+1)%len(path)];e=b-a;length=np.linalg.norm(e)
  t=np.clip((p-a)@e/max(length*length,1e-15),0,1);delta=p-a-t[:,None]*e;dist=np.linalg.norm(delta,axis=1);use=dist<best
  best[use]=dist[use];arc[use]=acc+t[use]*length;acc+=length
 return best,arc

def cloth_fields(ob):
 me=ob.data;p=np.array([v.co[:] for v in me.vertices])+np.array(ob.location);n=np.array([v.normal[:] for v in me.vertices])
 # Separate front/back and side textile coordinates, fixed in author rest space.
 front=np.abs(n[:,1])/(np.abs(n[:,0])+np.abs(n[:,1])+1e-7)
 fields=[]
 for u,half,center in [(p[:,0],(.073,.091),(.121,-.115)),(p[:,1],(.115,.091),(0.,-.115))]:
  distance,arc=seam_field(u,p[:,2],half,center,.014)
  phase=np.mod(arc,.0046)-.0023;end=1-smooth(.00125,.00165,np.abs(phase))
  thread=np.exp(-(distance/.00038)**2)*end
  holes=np.exp(-(distance/.00043)**2)*np.exp(-((np.abs(phase)-.00165)/.00030)**2)
  groove=np.exp(-(distance/.00105)**2)
  pitch=.0019;warp=np.sin(u*math.tau/pitch);weft=np.sin(p[:,2]*math.tau/pitch)
  weave=(warp*.58+weft*.42)*(0.65+.35*np.sin((u+p[:,2])*math.pi/pitch))
  height=.00012*thread-.000065*holes-.000025*groove+.000017*weave
  fuzz=np.clip(.32+.44*thread+.14*groove,0,1)
  fields.append((height,thread,holes,fuzz,weave))
 mixed=[fields[0][k]*front+fields[1][k]*(1-front) for k in range(5)]
 # Pouch mount / top cut is reinforced hardware, not fabric fuzz.
 fade=1-smooth(-.022,-.012,p[:,2]);mixed=[v*fade for v in mixed]
 return dict(zip(['ClothHeight','ClothThread','ClothHoles','ClothFuzz','ClothWeave'],mixed))

def put_fields(ob,values):
 for key,val in values.items():
  a=ob.data.attributes.get(key) or ob.data.attributes.new(key,'FLOAT','POINT');a.data.foreach_set('value',np.asarray(val,np.float32))

def cloth_material():
 m=bpy.data.materials.new('AUTHOR_WovenAmmoBag');m.use_nodes=True;ns=Nodes(m);op=ns.op;bs=ns.n.get('Principled BSDF');out=ns.n.get('Material Output')
 uv=ns.node('ShaderNodeUVMap',uv_map='UV0').outputs[0];old=ns.node('ShaderNodeTexImage');old.image=BASE;ns.put(old,'Vector',uv)
 attr={k:ns.node('ShaderNodeAttribute',attribute_name=k).outputs['Fac'] for k in ('ClothHeight','ClothThread','ClothHoles','ClothFuzz','ClothWeave')}
 color=ns.mul(old.outputs[0],(.58,.66,.49,1));color=ns.mul(color,op('ADD',.97,op('MULTIPLY',attr['ClothWeave'],.035)))
 color=ns.mix(color,(.083,.094,.052,1),op('MULTIPLY',attr['ClothThread'],.7));color=ns.mul(color,op('SUBTRACT',1.,op('MULTIPLY',attr['ClothHoles'],.32)))
 rough=op('MINIMUM',.92,op('MAXIMUM',.74,op('ADD',.81,op('MULTIPLY',attr['ClothWeave'],.045))))
 ns.put(bs,'Base Color',color);ns.put(bs,'Metallic',0.);ns.put(bs,'Roughness',rough);ns.put(bs,'Sheen Weight',op('MULTIPLY',attr['ClothFuzz'],.30));ns.put(bs,'Sheen Roughness',.8)
 relief=ns.combine(op('ADD',.5,op('DIVIDE',attr['ClothHeight'],.0005)),attr['ClothFuzz'],0.)
 return m,dict(BaseColor=color,ORM=ns.combine(op('SUBTRACT',1.,op('MULTIPLY',attr['ClothHoles'],.15)),rough,0.),Relief=relief),bs,out

def atlas_safety(ob,im):
 size=im.size[0];mask=np.zeros((size,size),bool);layer=ob.data.uv_layers['ClothAtlas'];ob.data.calc_loop_triangles()
 for tri in ob.data.loop_triangles:
  q=np.array([layer.data[i].uv[:] for i in tri.loops])*size
  lo=np.maximum(0,np.floor(q.min(0)).astype(int));hi=np.minimum(size-1,np.ceil(q.max(0)).astype(int))
  if np.any(hi<lo):continue
  xx,yy=np.meshgrid(np.arange(lo[0],hi[0]+1)+.5,np.arange(lo[1],hi[1]+1)+.5)
  den=(q[1,1]-q[2,1])*(q[0,0]-q[2,0])+(q[2,0]-q[1,0])*(q[0,1]-q[2,1])
  if abs(den)<1e-10:continue
  a=((q[1,1]-q[2,1])*(xx-q[2,0])+(q[2,0]-q[1,0])*(yy-q[2,1]))/den
  b=((q[2,1]-q[0,1])*(xx-q[2,0])+(q[0,0]-q[2,0])*(yy-q[2,1]))/den
  mask[lo[1]:hi[1]+1,lo[0]:hi[0]+1]|=(a>=0)&(b>=0)&(a+b<=1)
 distance=np.zeros(mask.shape,np.float32);inner=mask.copy()
 for _ in range(20):
  inner[0]=False;inner[-1]=False;inner[:,0]=False;inner[:,-1]=False
  inner=inner&np.roll(inner,1,0)&np.roll(inner,-1,0)&np.roll(inner,1,1)&np.roll(inner,-1,1);distance+=inner
 pixels=np.empty(size*size*4,np.float32);im.pixels.foreach_get(pixels);pixels=pixels.reshape(size,size,4);pixels[:,:,2]=smooth(3,18,distance)
 im.pixels.foreach_set(pixels.ravel());im.save()

def bake_cloth():
 active(bag);bag.data.uv_layers.new(name='ClothAtlas');bag.data.uv_layers.active=bag.data.uv_layers['ClothAtlas'];bag.data.uv_layers['ClothAtlas'].active_render=True
 bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT');bpy.ops.uv.smart_project(angle_limit=math.radians(65),island_margin=.025);bpy.ops.object.mode_set(mode='OBJECT')
 mat,fields,bs,out=cloth_material();bag.data.materials.clear();bag.data.materials.append(mat)
 for p in bag.data.polygons:p.material_index=0
 put_fields(bag,cloth_fields(bag))
 high=bag.copy();high.data=bag.data.copy();high.name='HIGH_AmmoBag_SewnWeave';HIGH.objects.link(high);active(high)
 sub=high.modifiers.new('Bake detail sampling','SUBSURF');sub.subdivision_type='SIMPLE';sub.levels=2;bpy.ops.object.modifier_apply(modifier=sub.name)
 vals=cloth_fields(high);put_fields(high,vals)
 # Snapshot all normals before changing positions. Reading v.normal after each
 # v.co write forces repeated whole-mesh normal evaluation on a million faces.
 positions=np.empty(len(high.data.vertices)*3,np.float32);normals=positions.copy()
 high.data.vertices.foreach_get('co',positions);high.data.vertices.foreach_get('normal',normals)
 positions=positions.reshape(-1,3)+normals.reshape(-1,3)*vals['ClothHeight'][:,None]
 high.data.vertices.foreach_set('co',positions.astype(np.float32).ravel())
 high.data.update();high.data.normals_split_custom_set_from_vertices([v.normal[:] for v in high.data.vertices]);high['BakeOnly']=True
 print('CLOTH_HIGH_AUTHORED',len(high.data.polygons),flush=True)
 maps={}
 for label in ['BaseColor','ORM','Normal','Relief']:
  size=4096 if label=='Normal' else 2048
  im=bpy.data.images.new('T_201_R29_AmmoBag_'+label,width=size,height=size,alpha=False)
  im.colorspace_settings.name='sRGB' if label=='BaseColor' else 'Non-Color';ns=Nodes(mat);t=ns.node('ShaderNodeTexImage');t.image=im;ns.n.active=t
  if label=='Normal':ns.l.new(bs.outputs[0],out.inputs['Surface'])
  else:emit=ns.node('ShaderNodeEmission');ns.put(emit,'Color',fields[label]);ns.l.new(emit.outputs[0],out.inputs['Surface'])
  active(bag);high.hide_set(False);high.hide_render=False;high.select_set(True)
  scene.render.bake.use_selected_to_active=True;scene.render.bake.use_clear=True;scene.render.bake.cage_extrusion=.00035;scene.render.bake.max_ray_distance=.0007
  print('CLOTH_BAKE',label,flush=True);bpy.ops.object.bake(type='NORMAL' if label=='Normal' else 'EMIT',uv_layer='ClothAtlas',normal_space='TANGENT')
  im.filepath_raw=str(R/'Textures'/(im.name+'.png'));im.file_format='PNG';im.save();maps[label]=im
  if label=='Relief':atlas_safety(bag,im)
 ns.l.new(bs.outputs[0],out.inputs['Surface']);high.select_set(False);high.hide_set(True);high.hide_render=True
 bag.data.materials[0]=baked_material('M_201_R29_WovenAmmoBag',maps,'ClothAtlas',True)
 return maps,high

surface_maps=bake_atlas()
cloth_maps,high=bake_cloth()
# Preserve named pivots and explicit attachment hierarchy in the authored file.
root=bpy.data.objects.new('LMG201_R29_Root',None);GAME.objects.link(root)
for ob in parts:ob.parent=root
parents={'FlashHider':'Barrel','FrontSight':'Barrel','GasFrontHardware':'GasTube','RearSight':'TopRail'}
for child,parent in parents.items():
 a=next((o for o in parts if o.name==child),None);b=next((o for o in parts if o.name==parent),None)
 if a and b:mw=a.matrix_world.copy();a.parent=b;a.matrix_world=mw
for ob in parts:
 ob['assembly_location_art_space']=list(ob.matrix_world.translation)
# Save a packed editable project. HIGH is hidden, never selected for export.
for im in list(bpy.data.images):
 if im.filepath:im.pack()
scene['reference']='MeshyRetry28 from two user screenshots';scene['runtime_tested']=False
scene['notes']='Candidate refinement and split only. No UE import, no gameplay or animation changes.'
bpy.ops.wm.save_as_mainfile(filepath=str(R/'LMG201_R29_Editable.blend'))
active(root)
for ob in parts:ob.hide_set(False);ob.select_set(True)
bpy.ops.export_scene.gltf(filepath=str(R/'Exports/LMG201_R29_Split.glb'),export_format='GLB',use_selection=True,export_apply=False,export_texcoords=True,export_normals=True,export_materials='EXPORT')
bpy.ops.export_scene.fbx(filepath=str(R/'Exports/LMG201_R29_Split.fbx'),use_selection=True,object_types={'MESH','EMPTY'},bake_anim=False,mesh_smooth_type='OFF',use_custom_props=True,path_mode='COPY',embed_textures=True,add_leaf_bones=False)
for ob in parts:
 active(ob)
 # Per-part exports use their own mating origin, with placement in the manifest.
 mw=ob.matrix_world.copy();parent=ob.parent;ob.parent=None;ob.matrix_world=mw;ob.location=(0,0,0)
 bpy.ops.export_scene.fbx(filepath=str(R/'Parts'/('SM_201_R29_'+ob.name+'.fbx')),use_selection=True,object_types={'MESH'},bake_anim=False,mesh_smooth_type='OFF',path_mode='STRIP',add_leaf_bones=False)
 ob.matrix_world=mw;ob.parent=parent;ob.matrix_world=mw
manifest=dict(status='authored_baked_and_exported',source=str(SRC/'model_urls_glb.glb'),editable=str(R/'LMG201_R29_Editable.blend'),assembly=str(R/'Exports/LMG201_R29_Split.glb'),parts=[dict(name=o.name,pivot_world=list(o.matrix_world.translation),parent=o.parent.name if o.parent else None,triangles=sum(len(p.vertices)-2 for p in o.data.polygons),materials=[m.name for m in o.data.materials]) for o in parts],author_seams=records,cloth_high_polygons=len(high.data.polygons),normal_convention='OpenGL tangent-space; UE needs one green-channel conversion',relief_channels=dict(R='same sculpt height mapped around 0.5',G='short-fiber/sheened seam mask',B='actual UV island safety fade'),runtime_tested=False,ue_imported=False,preview_rendered=False)
(R/'delivery.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
print('REFINE29_EXPORTED',len(parts),flush=True)
