"""Bounded 201 surface finish. Native rig, interfaces and unrelated parts survive.
All dimensions below are Blender bind-root metres, derived from the current FBX.
"""
import bpy, bmesh, json, math, hashlib
import numpy as np
from pathlib import Path
from mathutils import Vector, Matrix
from mathutils.geometry import delaunay_2d_cdt

O=Path(__file__).parent
D=json.loads((O/'Inputs/assets.json').read_text())
BODY='/Game/Weapons/LMG201/Cover10/SK_LMG201_Cover10'
slots=D['meshes'][BODY]['slots']
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.context.preferences.filepaths.save_version=0
bpy.ops.import_scene.fbx(filepath=str(O/'Inputs/Body.fbx'),use_anim=False)
rig=next(o for o in bpy.data.objects if o.type=='ARMATURE')
rig.animation_data_clear();rig.data.pose_position='REST'
root=rig.matrix_world@rig.data.bones['WPN_root'].matrix_local
source=max((o for o in bpy.data.objects if o.type=='MESH'),key=lambda o:len(o.data.polygons))
me=source.data;me.calc_loop_triangles()
xf=root.inverted()@source.matrix_world
coords=np.array([(xf@v.co)[:] for v in me.vertices])
nxf=xf.to_3x3().inverted().transposed()
normals=[(nxf@n.vector).normalized() for n in me.corner_normals]
parts=[];roles={};operations={}

def select(obs):
 bpy.ops.object.select_all(action='DESELECT')
 for ob in obs:ob.hide_set(False);ob.select_set(True)
 bpy.context.view_layer.objects.active=obs[-1]

def material(name,role):
 m=bpy.data.materials.get(name) or bpy.data.materials.new(name)
 roles[name]=role
 return m

def extract(name,ids,role,tri_filter=None):
 ts=[t for t in me.loop_triangles if t.material_index in ids and (tri_filter is None or tri_filter(t))]
 keys=sorted({i for t in ts for i in t.vertices});mapping={v:i for i,v in enumerate(keys)}
 mesh=bpy.data.meshes.new(name);mesh.from_pydata([coords[i] for i in keys],[],[[mapping[i] for i in t.vertices] for t in ts]);mesh.update()
 ob=bpy.data.objects.new(name,mesh);bpy.context.collection.objects.link(ob)
 mesh.materials.append(material(name,role))
 for p,t in zip(mesh.polygons,ts):p.use_smooth=me.polygons[t.polygon_index].use_smooth
 for uv in me.uv_layers:
  dst=mesh.uv_layers.new(name=uv.name)
  for p,t in zip(mesh.polygons,ts):
   for li,src in zip(p.loop_indices,t.loops):dst.data[li].uv=uv.data[src].uv
 for attr in me.color_attributes:
  if attr.domain!='CORNER':continue
  dst=mesh.color_attributes.new(attr.name,'FLOAT_COLOR','CORNER')
  for p,t in zip(mesh.polygons,ts):
   for li,src in zip(p.loop_indices,t.loops):dst.data[li].color=attr.data[src].color
 mesh.normals_split_custom_set([normals[li] for t in ts for li in t.loops])
 groups={}
 for i in keys:
  for g in me.vertices[i].groups:
   name=source.vertex_groups[g.group].name
   if name not in groups:groups[name]=ob.vertex_groups.new(name=name)
   groups[name].add([mapping[i]],g.weight,'REPLACE')
 return ob

def slice_ob(ob,point,normal,keep_positive=True):
 # Keep corner normals and UV through the bounded cut; cap only new cut rings.
 mesh=ob.data;ns=[n.vector.copy() for n in mesh.corner_normals]
 bm=bmesh.new();bm.from_mesh(mesh);bm.faces.ensure_lookup_table()
 layers=[bm.loops.layers.float.new('F50Normal'+a) for a in 'xyz']
 for f in bm.faces:
  for l,li in zip(f.loops,mesh.polygons[f.index].loop_indices):
   for k,layer in enumerate(layers):l[layer]=ns[li][k]
 bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=1e-7)
 result=bmesh.ops.bisect_plane(bm,geom=list(bm.verts)+list(bm.edges)+list(bm.faces),dist=1e-8,plane_co=point,plane_no=normal,clear_inner=keep_positive,clear_outer=not keep_positive)
 cut=[e for e in result['geom_cut'] if isinstance(e,bmesh.types.BMEdge) and e.is_boundary]
 if cut:
  filled=bmesh.ops.holes_fill(bm,edges=cut,sides=0)['faces']
  bm.normal_update()
  for f in filled:
   f.smooth=False
   for l in f.loops:
    for k,layer in enumerate(layers):l[layer]=f.normal[k]
    for uv in bm.loops.layers.uv.values():l[uv].uv=(l.vert.co.y/.06,l.vert.co.z/.06)
 ns=[Vector([l[a] for a in layers]).normalized() for f in bm.faces for l in f.loops]
 bm.to_mesh(mesh);bm.free();mesh.update();mesh.normals_split_custom_set(ns)
 return ob

def rounded(poly,r=.001,steps=8):
 p=[Vector(q) for q in poly];out=[]
 for i,c in enumerate(p):
  a=p[i-1]-c;b=p[(i+1)%len(p)]-c;d=min(r,a.length*.24,b.length*.24)
  a=c+a.normalized()*d;b=c+b.normalized()*d
  out.extend(tuple((1-t)**2*a+2*(1-t)*t*c+t*t*b) for t in np.linspace(0,1,steps,endpoint=False))
 return out

def rect(y0,y1,z0,z1,r=.002):return rounded([(y0,z0),(y1,z0),(y1,z1),(y0,z1)],r,8)

def contains(p,poly):
 x,y=p;inside=False
 for a,b in zip(poly,poly[1:]+poly[:1]):
  if (a[1]>y)!=(b[1]>y) and x<(b[0]-a[0])*(y-a[1])/(b[1]-a[1])+a[0]:inside=not inside
 return inside

def triangulate_region(outer,holes):
 points=[];edges=[]
 for ring in [outer]+holes:
  off=len(points);points.extend(Vector(p) for p in ring);edges.extend((off+i,off+(i+1)%len(ring)) for i in range(len(ring)))
 v,e,f,_,_,_=delaunay_2d_cdt(points,edges,[],0,1e-9,False)
 fs=[t for t in f if contains(sum((v[i] for i in t),Vector((0,0)))/len(t),outer) and not any(contains(sum((v[i] for i in t),Vector((0,0)))/len(t),h) for h in holes)]
 return v,fs

def finish(mesh,name,role,bone='WPN_root',bevel=0):
 ob=bpy.data.objects.new(name,mesh);bpy.context.collection.objects.link(ob);mesh.materials.append(material(name,role))
 bm=bmesh.new();bm.from_mesh(mesh);bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=1e-8);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(mesh);bm.free()
 select([ob])
 if bevel:
  b=ob.modifiers.new('Manufactured edge radii','BEVEL');b.width=bevel;b.segments=3;b.limit_method='ANGLE';b.angle_limit=math.radians(28);b.use_clamp_overlap=True;b.harden_normals=True
  bpy.ops.object.modifier_apply(modifier=b.name)
 for p in ob.data.polygons:p.use_smooth=True
 bm=bmesh.new();bm.from_mesh(ob.data)
 for e in bm.edges:e.smooth=len(e.link_faces)==2 and e.calc_face_angle(0)<math.radians(44)
 bm.to_mesh(ob.data);bm.free()
 wn=ob.modifiers.new('Planar weighted normals','WEIGHTED_NORMAL');wn.keep_sharp=True;wn.weight=60
 bpy.ops.object.modifier_apply(modifier=wn.name)
 # New geometry owns its atlas. Structural normal maps from the old model are not reused.
 bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT');bpy.ops.uv.smart_project(angle_limit=math.radians(58),island_margin=.015);bpy.ops.object.mode_set(mode='OBJECT')
 ob.vertex_groups.new(name=bone).add(list(range(len(ob.data.vertices))),1.,'REPLACE')
 return ob

def solid(name,outer,x0,x1,role='coat',pockets=None,through=None,bevel=.00035,bone='WPN_root'):
 """Explicit constrained triangles, never an n-gon spanning a blind pocket."""
 pockets=pockets or {};through=through or [];vs=[];fs=[]
 def plane(x,boundary,holes):
  v,f=triangulate_region(boundary,holes);off=len(vs);vs.extend((x,p.x,p.y) for p in v);fs.extend(tuple(off+i for i in t) for t in f)
 def wall(ring,a,b):
  off=len(vs);n=len(ring);vs.extend((a,*p) for p in ring);vs.extend((b,*p) for p in ring)
  fs.extend((off+i,off+(i+1)%n,off+n+(i+1)%n,off+n+i) for i in range(n))
 for side,x in [(-1,x0),(1,x1)]:
  ps=pockets.get(side,[]);plane(x,outer,through+[p[0] for p in ps])
  for ring,depth in ps:
   floor=x-side*depth;plane(floor,ring,[]);wall(ring,x,floor)
 wall(outer,x0,x1)
 for ring in through:wall(ring,x0,x1)
 mesh=bpy.data.meshes.new(name);mesh.from_pydata(vs,[],fs);mesh.update()
 return finish(mesh,name,role,bone,bevel)

def cylinder(name,center,radius,length,role='satin',axis='X',bone='WPN_root'):
 vs=[];fs=[];n=48;ax={'X':0,'Y':1,'Z':2}[axis];u=(ax+1)%3;v=(ax+2)%3
 for a in [-.5,.5]:
  for i in range(n):
   p=list(center);p[ax]+=a*length;p[u]+=radius*math.cos(i*math.tau/n);p[v]+=radius*math.sin(i*math.tau/n);vs.append(p)
 fs.extend((i,(i+1)%n,n+(i+1)%n,n+i) for i in range(n));fs.extend([tuple(range(n-1,-1,-1)),tuple(range(n,2*n))])
 mesh=bpy.data.meshes.new(name);mesh.from_pydata(vs,[],fs);mesh.update();return finish(mesh,name,role,bone,.00012)

# Identify connected receiver plates by welded position, retaining front shoulders,
# the feed interface and the trigger guard which share this material slot.
ts=[t for t in me.loop_triangles if t.material_index==67]
parents={}
def find(k):
 parents.setdefault(k,k)
 while parents[k]!=k:parents[k]=parents[parents[k]];k=parents[k]
 return k
for t in ts:
 keys=[tuple(np.round(coords[i],7)) for i in t.vertices];a=find(keys[0])
 for k in keys[1:]:parents[find(k)]=a
groups={}
for t in ts:groups.setdefault(find(tuple(np.round(coords[t.vertices[0]],7))),[]).append(t)
removed=set();component_notes=[]
for group in groups.values():
 v=coords[list({i for t in group for i in t.vertices})];lo=v.min(0);hi=v.max(0)
 replace=lo[1]<-.110 and hi[1]>.063 and lo[2]>.000 and hi[2]>.073
 component_notes.append({'triangles':len(group),'lo':lo.tolist(),'hi':hi.tolist(),'replace':bool(replace)})
 if replace:removed.update(t.index for t in group)
if not removed:raise RuntimeError('Current receiver plate components were not located')
retained=extract(slots[67]['name'],[67],'coat',lambda t:t.index not in removed);parts.append(retained)
outer=rounded([(-.1125,.0015),(.057,.0015),(.066,.008),(.066,.059),(.057,.0748),(-.1125,.0748)],.0022)
top=[(rect(a,b,.051,.068,.0032),.002) for a,b in [(-.094,-.037),(-.031,.0285)]]
left=top+[(rounded([(-.108,.0375),(-.053,.0375),(-.050,.033),(-.087,.0095),(-.108,.0095)],.0027),.002),
 (rounded([(-.063,.012),(-.031,.0375),(-.006,.0375),(.038,.0145),(.038,.0105),(-.060,.0105)],.003),.002),
 (rounded([(.028,.039),(.048,.039),(.048,.018)],.0018),.0016)]
for side in [-1,1]:
 x0,x1=(-.0217,-.0138) if side<0 else (.0138,.0213)
 ob=solid('M_LMG201_F50_Receiver',outer,x0,x1,pockets={side:top if side<0 else left},bevel=.00028);parts.append(ob)
operations['receiver']={'removed_triangles':len(removed),'components':component_notes,'front_feed_and_guard_retained':True,'construction':'constrained face triangulation; blind floors and welded pocket walls'}

# Lower handguard panels are rebuilt; the original upper vents, front band,
# rear joint and their texture coordinates retain their own surface slot.
front=extract(slots[58]['name'],[58],'coat');slice_ob(front,(0,-.390,0),(0,1,0),False);parts.append(front)
upper=extract(slots[58]['name'],[58],'coat');slice_ob(upper,(0,-.390,0),(0,1,0),True);slice_ob(upper,(0,0,.0495),(0,0,1),True);parts.append(upper)
hg=rounded([(-.391,.012),(-.379,.0085),(-.248,.0085),(-.224,.020),(-.224,.052),(-.391,.052)],.0014)
recess=rounded([(-.380,.031),(-.257,.031),(-.244,.045),(-.380,.045)],.0015)
parts.append(solid('M_LMG201_F50_Handguard',hg,-.0275,.0291,pockets={-1:[(recess,.0011)],1:[(recess,.0011)]},bevel=.00065))
for side in [-1,1]:
 face=.0291 if side>0 else -.0275
 for i,y in enumerate(np.linspace(-.377,-.253,21)):
  rib=rounded([(y-.00135,.0115),(y+.00135,.0115),(y+.0060,.0292),(y+.0033,.0292)],.00055,6)
  a,b=sorted([face-side*.00025,face+side*.00085]);parts.append(solid('M_LMG201_F50_Handguard',rib,a,b,bevel=.00030))
 for y in [-.378,-.252]:parts.append(cylinder('M_LMG201_F50_HandguardFastener',(face+side*.00030,y,.040),.00235,.0011,'satin'))
operations['handguard']={'upper_vents_preserved':True,'new_lower_side_ribs':42,'shared_joint_overlap_mm':2.5}

# Magazine upper engagement surfaces stay in the original bind frame. A swept
# rounded shell replaces only the visible lower body; grid beads are continuous
# surface displacement rather than intersecting strips.
neck=extract(slots[14]['name'],[14],'magazine_neck');slice_ob(neck,(0,0,-.046),(0,0,1),True);parts.append(neck)
control=np.array([[-.059,-.038],[-.069,-.082],[-.102,-.129],[-.135,-.164]])
N=128;K=73;vs=[];fs=[]
def bez(t):return (1-t)**3*control[0]+3*(1-t)**2*t*control[1]+3*(1-t)*t*t*control[2]+t**3*control[3]
def cross(theta,half_x,half_y,rad):
 # Rounded rectangle ray intersection, evaluated without superellipse bulges.
 d=np.array([math.cos(theta),math.sin(theta)]);low,high=0.,.08
 for _ in range(28):
  mid=(low+high)/2;q=np.abs(d*mid)-(np.array([half_x,half_y])-rad);sd=np.linalg.norm(np.maximum(q,0))+min(max(q),0)-rad
  if sd>0:high=mid
  else:low=mid
 return d*((low+high)/2)
for j,t in enumerate(np.linspace(0,1,K)):
 c=bez(t);tangent=bez(min(1,t+.001))-bez(max(0,t-.001));tangent/=np.linalg.norm(tangent);wide=np.array([-tangent[1],tangent[0]])
 half=float(np.interp(t,[0,.4,1],[.040,.038,.0345]));band=math.exp(-((t-.965)/.020)**6)
 for i in range(N):
  x,w=cross(i*math.tau/N,.0168+band*.0015,half+band*.0007,.0025)
  side=abs(x)/(.0168+band*.0015);s=w/half
  row=sum(math.exp(-((t-a)/.013)**4) for a in [.18,.39,.61,.81])
  col=sum(math.exp(-((s-a)/.06)**4) for a in [-.58,.58])
  bead=.00085*min(1.,row+col)*(max(0,side-.82)/.18)**2
  x+=math.copysign(bead,x);p=c+wide*w;vs.append((x-.0003,p[0],p[1]))
for j in range(K-1):fs.extend((j*N+i,j*N+(i+1)%N,(j+1)*N+(i+1)%N,(j+1)*N+i) for i in range(N))
fs.extend([tuple(range(N-1,-1,-1)),tuple((K-1)*N+i for i in range(N))])
mesh=bpy.data.meshes.new('MagazineF50');mesh.from_pydata(vs,[],fs);mesh.update();parts.append(finish(mesh,'M_LMG201_Magazine_F50','coat','WPN_SOCKET_Magazine',0))
operations['magazine']={'original_bone':'WPN_SOCKET_Magazine','upper_source_neck_retained_above_m':-.046,'lower_shell':'closed swept shell with continuous grid beads','animation_tracks_changed':False}

# Retain native stock mount/rods. Rebuild the polymer shell with the actual
# reference opening, closed inner walls, cheek recess and separate recoil pad.
mount=extract(slots[34]['name'],[34,35],'stock_mount');slice_ob(mount,(0,.115,0),(0,1,0),False);parts.append(mount)
outline=rounded([(.111,.0580),(.325,.0580),(.329,.052),(.315,-.0730),(.303,-.0730),(.211,-.032),(.164,-.018),(.139,.009),(.111,.017)],.0030,10)
window=rounded([(.191,.006),(.302,.006),(.298,-.050),(.289,-.052),(.215,-.025),(.187,-.003)],.004,12)
cheek=rect(.174,.308,.019,.044,.0045)
parts.append(solid('M_LMG201_FactoryStock_F50',outline,-.0113,.0129,'polymer',pockets={-1:[(cheek,.0013)],1:[(cheek,.0013)]},through=[window],bevel=.00085))
pad=rounded([(.324,.058),(.334,.056),(.336,.050),(.322,-.071),(.316,-.074),(.307,-.073)],.0022,10)
parts.append(solid('M_LMG201_FactoryStock_F50_Pad',pad,-.0125,.0141,'rubber',bevel=.00055))
for side in [-1,1]:
 parts.append(cylinder('M_LMG201_FactoryStock_F50_Fastener',(side*.0126+.0008,.142,.034),.0041,.0010,'satin'))
operations['stock']={'original_mount_retained_before_y_m':.115,'opening':'through volume with explicit inner walls','closed_cheek_recess':True}

# Bounded grip fairing: shared-position neighbours avoid FBX seam splits.
# Keep the mounting top and the accepted lower hand-contact surface in place.
grip=extract(slots[69]['name'],[69],'grip');gm=grip.data
old=np.array([v.co[:] for v in gm.vertices]);keys={};vi=[]
for p in old:
 k=tuple(np.round(p,7))
 if k not in keys:keys[k]=len(keys)
 vi.append(keys[k])
unique=np.array(list(keys));vi=np.array(vi);adj=[set() for _ in unique]
for edge in gm.edges:
 a,b=[vi[i] for i in edge.vertices]
 if a!=b:adj[a].add(b);adj[b].add(a)
z=unique[:,2];weight=np.clip((z+.028)/.011,0,1)*np.clip((.0045-z)/.012,0,1);pos=unique.copy()
for _ in range(14):
 delta=np.array([pos[list(ns)].mean(0)-p if ns else np.zeros(3) for p,ns in zip(pos,adj)])*.40*weight[:,None]
 pos+=delta;off=pos-unique;length=np.linalg.norm(off,axis=1);pos=unique+off*np.minimum(1,.00055/np.maximum(length,1e-12))[:,None]
for v,p in zip(gm.vertices,pos[vi]):v.co=p
gm.update();smooth=np.zeros_like(pos)
for p in gm.polygons:
 for v in p.vertices:smooth[vi[v]]+=np.array(p.normal)*p.area
smooth/=np.maximum(np.linalg.norm(smooth,axis=1)[:,None],1e-12)
ns=[]
for p in gm.polygons:
 for li in p.loop_indices:
  v=gm.loops[li].vertex_index;k=vi[v];w=min(1,weight[k]*2.5)
  n=np.array(gm.corner_normals[li].vector);n=n*(1-w)+smooth[k]*w
  ns.append(Vector(n).normalized())
gm.normals_split_custom_set(ns);parts.append(grip)
operations['grip']={'fairing_max_displacement_mm':float(np.linalg.norm(pos-unique,axis=1).max()*1000),'mount_top_frozen_z_m':.0045,'lower_hand_contact_preserved_below_z_m':-.028,'UV_and_mask_retained':True}

# Bind every authored part to the original native armature, preserving groups.
for ob in parts:
 ns=[(root.to_3x3().inverted().transposed()@n.vector).normalized() for n in ob.data.corner_normals]
 ob.data.transform(root);ob.data.normals_split_custom_set(ns)
 ob.parent=rig;ob.matrix_parent_inverse=rig.matrix_world.inverted();ob.matrix_basis=Matrix.Identity(4)
 ob.modifiers.new('Native201Rig','ARMATURE').object=rig
source.hide_set(True);source.hide_render=True
select(parts+[rig]);fbx=O/'Exports/SK_LMG201_F50_Parts.fbx'
bpy.ops.export_scene.fbx(filepath=str(fbx),use_selection=True,object_types={'MESH','ARMATURE'},axis_forward='-Y',axis_up='Z',add_leaf_bones=False,bake_anim=False,mesh_smooth_type='FACE',colors_type='LINEAR')
bpy.ops.wm.save_as_mainfile(filepath=str(O/'LMG201_SurfaceFinish50.blend'))
report={'body':BODY,'source_body_sha256':D['meshes'][BODY]['sha256'],'fbx':str(fbx),'replace_slots':[slots[i]['name'] for i in [14,19,34,35,58,67,69]],'roles':roles,'operations':operations,'parts':[o.name for o in parts],'no_animations_authored':True,'rendered_acceptance':False}
(O/'model.json').write_text(json.dumps(report,indent=2))
print('F50_SOURCE_EXPORTED',str(fbx),flush=True)
