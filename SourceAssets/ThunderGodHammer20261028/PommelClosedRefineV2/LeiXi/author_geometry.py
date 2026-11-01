"""Lei Xi: preserve factory mount/collar, build solid faceted pommel and recessed windows."""
import bpy,bmesh,math,json,numpy as np
from mathutils import Vector,Matrix
from pathlib import Path
P=Path(__file__).resolve().parent;T=P/'Textures';E=P/'Export';E.mkdir(exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True);bpy.context.preferences.filepaths.save_version=0
with bpy.data.libraries.load(str(P.parent.parent/'ModulesV1/ThunderGodHammer_Modular_Editable.blend'),link=False) as(a,b):b.objects=['SM_ThunderGodHammer_pommel_factory']
factory=b.objects[0];bpy.context.collection.objects.link(factory)
factory.parent=None;factory.matrix_world=Matrix.Identity(4);bpy.context.view_layer.update()
# Keep the original interface, seam and braid with interpolated UV/custom normals.
src=factory.data;bm=bmesh.new();bm.from_mesh(src);nl=bm.loops.layers.float_vector.new('NativeNormal')
for f,p in zip(bm.faces,src.polygons):
 for l,li in zip(f.loops,p.loop_indices):l[nl]=src.corner_normals[li].vector
bmesh.ops.bisect_plane(bm,geom=list(bm.verts)+list(bm.edges)+list(bm.faces),plane_co=(0,0,-.02465),plane_no=(0,0,1),dist=1e-7,clear_inner=True,clear_outer=False)
bmesh.ops.triangulate(bm,faces=list(bm.faces));normals=[tuple(l[nl].normalized()) for f in bm.faces for l in f.loops]
bm.to_mesh(src);bm.free();src.normals_split_custom_set(normals)
factory.name='Factory_Protected_Mount';parts=[factory]
def image(name,non=False):
 im=bpy.data.images.load(str(T/('T_LeiXi_'+name+'.png')),check_existing=True)
 if non:im.colorspace_settings.name='Non-Color'
 return im
def material(name,tint,metal=1.,rough=1.,core=False):
 m=bpy.data.materials.new(name);m.use_nodes=True;n=m.node_tree.nodes;l=m.node_tree.links;p=n.get('Principled BSDF')
 p.inputs['Metallic'].default_value=.3 if core else .94;p.inputs['Roughness'].default_value=.22 if core else .42
 c=n.new('ShaderNodeTexImage');c.image=image('CoreBaseColor' if core else 'MetalBaseColor');mul=n.new('ShaderNodeMixRGB');mul.blend_type='MULTIPLY';mul.inputs[0].default_value=1;mul.inputs[2].default_value=(*tint,1);l.new(c.outputs['Color'],mul.inputs[1]);l.new(mul.outputs[0],p.inputs['Base Color'])
 if core:
  e=n.new('ShaderNodeTexImage');e.image=image('CoreEmission',True);l.new(e.outputs['Color'],p.inputs['Emission Color']);p.inputs['Emission Strength'].default_value=5
 else:
  norm=n.new('ShaderNodeTexImage');norm.image=image('MetalNormal',True);nm=n.new('ShaderNodeNormalMap');nm.inputs['Strength'].default_value=.75;l.new(norm.outputs['Color'],nm.inputs['Color']);l.new(nm.outputs['Normal'],p.inputs['Normal'])
  orm=n.new('ShaderNodeTexImage');orm.image=image('MetalORM',True);sep=n.new('ShaderNodeSeparateColor');l.new(orm.outputs['Color'],sep.inputs[0]);l.new(sep.outputs['Green'],p.inputs['Roughness'])
 return m
steel=material('M_LeiXi_ForgedSteel',(.42,.49,.60));silver=material('M_LeiXi_SilverInlay',(1.15,1.10,.99));bronze=material('M_LeiXi_AgedSeams',(1.0,.60,.29));coremat=material('M_LeiXi_StormCore',(1,1,1),core=True)
# Restore the retained native material from its current original maps.
m=src.materials[0];m.use_nodes=True;n=m.node_tree.nodes;l=m.node_tree.links;n.clear();out=n.new('ShaderNodeOutputMaterial');bs=n.new('ShaderNodeBsdfPrincipled');l.new(bs.outputs[0],out.inputs[0])
for name in ['BaseColor','MetallicRoughness','Normal']:
 tex=n.new('ShaderNodeTexImage');tex.image=bpy.data.images.load(str(P.parent.parent/'Textures'/(name+'.jpg')),check_existing=True)
 if name!='BaseColor':tex.image.colorspace_settings.name='Non-Color'
 if name=='BaseColor':l.new(tex.outputs['Color'],bs.inputs['Base Color'])
 elif name=='Normal':nn=n.new('ShaderNodeNormalMap');l.new(tex.outputs['Color'],nn.inputs['Color']);l.new(nn.outputs[0],bs.inputs['Normal'])
 else:
  sep=n.new('ShaderNodeSeparateColor');l.new(tex.outputs[0],sep.inputs[0]);l.new(sep.outputs['Green'],bs.inputs['Roughness']);l.new(sep.outputs['Blue'],bs.inputs['Metallic'])
CX=-.0006;CY=-.0010
profile=[(-.0750,.0108),(-.0736,.0130),(-.0688,.0155),(-.0672,.0148),(-.0640,.0180),(-.055,.0275),(-.038,.0272),(-.029,.0160),(-.026,.0147),(-.02435,.0153)]
def radius(z):return float(np.interp(z,[p[0] for p in profile],[p[1] for p in profile]))
def facepoint(i,s,z,depth=0):
 a=(i-.5)*math.pi/4;b=(i+.5)*math.pi/4;r=radius(z);f=(s+1)*.5
 return Vector((CX+r*((1-f)*math.cos(a)+f*math.cos(b))-depth*math.cos(i*math.pi/4),CY+r*((1-f)*math.sin(a)+f*math.sin(b))-depth*math.sin(i*math.pi/4),z))
def make(name,verts,faces,mat,bevel=0,uvs=None):
 me=bpy.data.meshes.new(name);me.from_pydata(verts,[],faces);me.update();o=bpy.data.objects.new(name,me);bpy.context.collection.objects.link(o);me.materials.append(mat);parts.append(o)
 uv=me.uv_layers.new(name=src.uv_layers[0].name)
 for p in me.polygons:
  axis=max(range(3),key=lambda k:abs(p.normal[k]));axes=[k for k in range(3) if k!=axis]
  for li in p.loop_indices:
   vi=me.loops[li].vertex_index;co=me.vertices[vi].co;uv.data[li].uv=uvs[vi] if uvs else (co[axes[0]]*24,co[axes[1]]*24)
 bm=bmesh.new();bm.from_mesh(me);bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=1e-8);bmesh.ops.dissolve_degenerate(bm,edges=list(bm.edges),dist=1e-10)
 bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
 if bm.calc_volume(signed=True)<0:bmesh.ops.reverse_faces(bm,faces=list(bm.faces))
 bm.to_mesh(me);bm.free()
 if bevel:finish_bevel(o,bevel)
 return o
def finish_bevel(o,width):
 bpy.ops.object.select_all(action='DESELECT');o.select_set(True);bpy.context.view_layer.objects.active=o
 mod=o.modifiers.new('Physical machined edge radius','BEVEL');mod.width=width;mod.segments=3;mod.limit_method='ANGLE';mod.angle_limit=math.radians(32);mod.use_clamp_overlap=True
 if o.name.startswith('Continuous structural body'):
  bm=bmesh.new();bm.from_mesh(o.data);bm.normal_update();weights=bm.edges.layers.float.new('bevel_weight_edge')
  for e in bm.edges:e[weights]=1. if len(e.link_faces)==2 and e.calc_face_angle()>math.radians(32) and all(v.co.z<-.0263 for v in e.verts) else 0.
  bm.to_mesh(o.data);bm.free();mod.limit_method='WEIGHT'
 bpy.ops.object.modifier_apply(modifier=mod.name)
 for p in o.data.polygons:p.use_smooth=True
 mod=o.modifiers.new('Preserved flat faces and rounded highlights','WEIGHTED_NORMAL');mod.keep_sharp=True;mod.weight=75;bpy.ops.object.modifier_apply(modifier=mod.name)

def tube(name,coords,r,mat,closed=False,sides=8):
 pts=[Vector(p) for p in coords];verts=[];count=len(pts)
 for j,p in enumerate(pts):
  tangent=(pts[(j+1)%count]-pts[(j-1)%count]) if closed else (pts[min(j+1,count-1)]-pts[max(0,j-1)])
  tangent.normalize();up=Vector((0,0,1))
  if abs(tangent.dot(up))>.9:up=Vector((1,0,0))
  a=tangent.cross(up).normalized();b=tangent.cross(a).normalized()
  for k in range(sides):verts.append(p+r*(a*math.cos(k*2*math.pi/sides)+b*math.sin(k*2*math.pi/sides)))
 faces=[]
 for j in range(count if closed else count-1):
  for k in range(sides):faces.append((j*sides+k,j*sides+(k+1)%sides,((j+1)%count)*sides+(k+1)%sides,((j+1)%count)*sides+k))
 if not closed:faces.extend([tuple(reversed(range(sides))),tuple((count-1)*sides+k for k in range(sides))])
 o=make(name,verts,faces,mat)
 for p in o.data.polygons:p.use_smooth=True
 return o
def ring(z,r,mat,width=.0005):
 coords=[(CX+r*math.cos(a*2*math.pi/64),CY+r*math.sin(a*2*math.pi/64),z) for a in range(64)]
 tube('Continuous inset rim',coords,width,mat,True)
def ribbon(name,coords,normal,width,thickness,mat,closed=False):
 pts=[Vector(p) for p in coords];base_normal=Vector(normal).normalized();verts=[];faces=[];count=len(pts)
 for j,p in enumerate(pts):
  slope=(radius(p.z+.00002)-radius(p.z-.00002))/.00004
  normal=Vector((base_normal.x,base_normal.y,-slope*math.cos(math.pi/8))).normalized()
  tangent=(pts[(j+1)%count]-pts[(j-1)%count]) if closed else (pts[min(j+1,count-1)]-pts[max(0,j-1)])
  side=normal.cross(tangent).normalized()*width*.5
  verts.extend([p-side+normal*thickness*.5,p+side+normal*thickness*.5,p+side-normal*thickness*.5,p-side-normal*thickness*.5])
 for j in range(count if closed else count-1):
  a=j*4;b=((j+1)%count)*4
  for k in range(4):faces.append((a+k,a+(k+1)%4,b+(k+1)%4,b+k))
 if not closed:faces.extend([(3,2,1,0),tuple((count-1)*4+k for k in range(4))])
 return make(name,verts,faces,mat,.000065)

KIND='LeiXi';KEY='lei_xi'
# Replace only the coarse scanned braid strip; retain the native mounting socket and both lips.
bm=bmesh.new();bm.from_mesh(src);nl=bm.loops.layers.float_vector.new('PreservedCollarNormal');tag=bm.faces.layers.int.new('NewBand')
for f,p in zip(bm.faces,src.polygons):
 for l,li in zip(f.loops,p.loop_indices):l[nl]=src.corner_normals[li].vector
bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=1e-8)
upper_z=-.0105;lower_z=-.0175
for z in [upper_z,lower_z]:bmesh.ops.bisect_plane(bm,geom=list(bm.verts)+list(bm.edges)+list(bm.faces),plane_co=(0,0,z),plane_no=(0,0,1),dist=1e-8,clear_inner=False,clear_outer=False)
bmesh.ops.delete(bm,geom=[f for f in bm.faces if lower_z+1e-8<f.calc_center_median().z<upper_z-1e-8],context='FACES')
def az(v):return math.atan2(v.co.y-CY,v.co.x-CX)%(math.pi*2)
def cut_ring(z):
 return sorted(set(v for e in bm.edges if e.is_boundary and all(abs(v.co.z-z)<1e-7 for v in e.verts) for v in e.verts),key=az)
top=cut_ring(upper_z);bottom=cut_ring(lower_z)
if len(top)<8 or len(bottom)<8:raise RuntimeError('Cannot locate collar braid boundaries')
src.materials.append(steel);steel_index=len(src.materials)-1
def join_rings(a,b):
 ia=ib=0;na=len(a);nb=len(b)
 while ia<na or ib<nb:
  aa=az(a[(ia+1)%na])+(2*math.pi if ia+1>=na else 0) if ia<na else float('inf')
  ab=az(b[(ib+1)%nb])+(2*math.pi if ib+1>=nb else 0) if ib<nb else float('inf')
  if aa<ab:f=bm.faces.new((a[ia%na],b[ib%nb],a[(ia+1)%na]));ia+=1
  else:f=bm.faces.new((a[ia%na],b[ib%nb],b[(ib+1)%nb]));ib+=1
  f[tag]=1;f.material_index=steel_index
band_radius=.01755
loops=[]
for z in [upper_z-.00025,lower_z+.00025]:
 loops.append([bm.verts.new((CX+band_radius*math.cos(a*2*math.pi/192),CY+band_radius*math.sin(a*2*math.pi/192),z)) for a in range(192)])
join_rings(top,loops[0]);join_rings(loops[0],loops[1]);join_rings(loops[1],bottom)
bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));uv=bm.loops.layers.uv.active
for f in bm.faces:
 if not f[tag]:continue
 for l in f.loops:
  co=l.vert.co;a=math.atan2(co.y-CY,co.x-CX)
  l[uv].uv=(a/(math.pi*2),co.z*30)
  l[nl]=Vector((math.cos(a),math.sin(a),0)) if abs(f.normal.z)<.25 else f.normal
bmesh.ops.triangulate(bm,faces=list(bm.faces));normals=[tuple(l[nl].normalized()) for f in bm.faces for l in f.loops]
bm.to_mesh(src);bm.free()
for p in src.polygons:p.use_smooth=True
src.normals_split_custom_set(normals)
# Closed flat silver braids over a closed steel bed; they never cover an opening.
for strand in range(2):
 points=[];n=480;verts=[];faces=[]
 for j in range(n):
  a=j*2*math.pi/n;phase=a*12+strand*math.pi
  r=band_radius+.00026+.00013*math.cos(phase*2+strand*math.pi);z=-.014+.00195*math.sin(phase)
  points.append(Vector((CX+r*math.cos(a),CY+r*math.sin(a),z)))
 for j,p in enumerate(points):
  a=j*2*math.pi/n;normal=Vector((math.cos(a),math.sin(a),0));tangent=(points[(j+1)%n]-points[(j-1)%n]).normalized();side=normal.cross(tangent).normalized()*.00058
  verts.extend([p-side+normal*.00012,p+side+normal*.00012,p+side-normal*.00012,p-side-normal*.00012])
 for j in range(n):
  for k in range(4):faces.append((j*4+k,j*4+(k+1)%4,((j+1)%n)*4+(k+1)%4,((j+1)%n)*4+k))
 make('Precision interwoven collar silver band',verts,faces,silver,.000045)

# One sewn structural surface, including every recess, reveal and end cap.
# All new geometry shares vertices before normals/bevel; no isolated single-sided patches.
zcut=-.02465
verts=[];faces=[];mats=[]
def face(points,mat=0):
 idx=len(verts);verts.extend(points);faces.append(tuple(range(idx,idx+len(points))));mats.append(mat)
if KIND=='LeiXi':
 zt=-.032;zc=-.0465;zb=-.0618
 levels=sorted(set([z for z,r in profile if z<=-.0262]+[zt,zc,zb,-.0262]))
 def section(z):
  w=max(0,.64*((z-zb)/(zc-zb) if z<zc else (zt-z)/(zt-zc))) if zb<=z<=zt else 0
  d=.00125*min(1,w/.06)
  return [(-1,0),(-w,0),(-w,d),(0,d),(w,d),(w,0),(1,0)]
else:
 levels=sorted(set([z for z,r in profile if z<=-.0262]+[-.065,-.0644,-.0406,-.040,-.0262]))
 def section(z):
  d=.0008*min(1,max(0,(z+.065)/.0006),max(0,(-.040-z)/.0006))
  return [(-1,0),(-.84,0),(-.84,d),(0,d),(.84,d),(.84,0),(1,0)]
for i in range(8):
 for za,zb_ in zip(levels[:-1],levels[1:]):
  sa=section(za);sb=section(zb_)
  if i%2:sa=[(s,0) for s,d in sa];sb=[(s,0) for s,d in sb]
  for k in range(6):
   pts=[facepoint(i,sa[k][0],za,sa[k][1]),facepoint(i,sa[k+1][0],za,sa[k+1][1]),facepoint(i,sb[k+1][0],zb_,sb[k+1][1]),facepoint(i,sb[k][0],zb_,sb[k][1])]
   mat=2 if i%2==0 and k in [2,3] and KIND=='LeiXi' else 1 if i%2==0 and k in [1,4] else 0
   face(pts,mat)
body=make('Continuous structural body with closed relief wells',verts,faces,steel)
body.data.materials.append(bronze);body.data.materials.append(coremat)
# Assign by geometric face position after degenerate strips have been removed.
for p in body.data.polygons:
 center=p.center;a=math.atan2(center.y-CY,center.x-CX);i=int(round(a/(math.pi/4)))%8
 normal=Vector((math.cos(i*math.pi/4),math.sin(i*math.pi/4),0));depth=radius(center.z)*math.cos(math.pi/8)-(center-Vector((CX,CY,center.z))).dot(normal)
 if KIND=='LeiXi' and i%2==0 and depth>.00065:
  p.material_index=2
  for li in p.loop_indices:
   co=body.data.vertices[body.data.loops[li].vertex_index].co;tangent=Vector((-normal.y,normal.x,0));s=(co-Vector((CX,CY,co.z))).dot(tangent)/(radius(co.z)*math.sin(math.pi/8))
   body.data.uv_layers.active.data[li].uv=(.5+s/1.28,(co.z+ .0618)/(.0618-.032))
# The cut ring comes from real native boundary topology, not samples extrapolated by height.
bm=bmesh.new();bm.from_mesh(src);bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=1e-8)
cut_edges=[e for e in bm.edges if e.is_boundary and all(abs(v.co.z-zcut)<2e-7 for v in e.verts)]
cut_verts=set(v for e in cut_edges for v in e.verts)
native_ring=sorted([v.co.copy() for v in cut_verts],key=lambda p:math.atan2(p.y-CY,p.x-CX)%(math.pi*2));bm.free()
if len(native_ring)<8:raise RuntimeError('Native interface boundary unavailable')
bm=bmesh.new();bm.from_mesh(body.data)
top_verts=set(v for e in bm.edges if e.is_boundary and all(abs(v.co.z+.0262)<2e-7 for v in e.verts) for v in e.verts)
top=sorted(top_verts,key=lambda v:math.atan2(v.co.y-CY,v.co.x-CX)%(math.pi*2))
upper=[bm.verts.new(p) for p in native_ring]
def angle(v):return math.atan2(v.co.y-CY,v.co.x-CX)%(math.pi*2)
# Angular zipper joins arbitrary native triangle cuts to the regular forged profile.
ia=ib=0;na=len(upper);nb=len(top)
while ia<na or ib<nb:
 a=upper[ia%na];b=top[ib%nb]
 an=angle(upper[(ia+1)%na])+(2*math.pi if ia+1>=na else 0) if ia<na else float('inf')
 bn=angle(top[(ib+1)%nb])+(2*math.pi if ib+1>=nb else 0) if ib<nb else float('inf')
 if an<bn:bm.faces.new((a,b,upper[(ia+1)%na]));ia+=1
 else:bm.faces.new((a,b,top[(ib+1)%nb]));ib+=1
# Solid terminal cap shares the real bottom perimeter, including collinear panel vertices.
bottom=set(v for e in bm.edges if e.is_boundary and all(abs(v.co.z-levels[0])<2e-7 for v in e.verts) for v in e.verts)
bottom=sorted(bottom,key=angle);center=bm.verts.new((CX,CY,levels[0]))
for j,v in enumerate(bottom):bm.faces.new((center,bottom[(j+1)%len(bottom)],v))
uv=bm.loops.layers.uv.active
for f in bm.faces:
 if all(tuple(l[uv].uv)==(0.,0.) for l in f.loops):
  for l in f.loops:l[uv].uv=(l.vert.co.x*24,l.vert.co.y*24)
bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
if bm.calc_volume(signed=True)<0:bmesh.ops.reverse_faces(bm,faces=list(bm.faces))
bm.to_mesh(body.data);bm.free();finish_bevel(body,.00016)
# Unequal native cut triangles must not create a scalloped highlight in the neck.
# Its shading follows the actual circular-to-octagonal ruled transition.
neck_normals=[tuple(n.vector) for n in body.data.corner_normals]
mean_cut_radius=sum(math.hypot(p.x-CX,p.y-CY) for p in native_ring)/len(native_ring)
for p in body.data.polygons:
 if all(-.02621<=body.data.vertices[body.data.loops[li].vertex_index].co.z<=zcut+1e-6 for li in p.loop_indices):
  for li in p.loop_indices:
   co=body.data.vertices[body.data.loops[li].vertex_index].co;a=math.atan2(co.y-CY,co.x-CX);face_angle=round(a/(math.pi/4))*math.pi/4
   bottom_radius=radius(-.0262)*math.cos(math.pi/8)/math.cos(a-face_angle);slope=(mean_cut_radius-bottom_radius)/(.0262-.02465)
   blend=max(0,min(1,(co.z+.0262)/(.0262-.02465)))
   outward=(Vector((math.cos(face_angle),math.sin(face_angle),0))*(1-blend)+Vector((math.cos(a),math.sin(a),0))*blend).normalized()
   neck_normals[li]=tuple(Vector((outward.x,outward.y,-slope)).normalized())
body.data.normals_split_custom_set(neck_normals)

def solid_relief(name,i,outline,depth,thickness,mat):
 front=[facepoint(i,s,z,depth) for s,z in outline];back=[facepoint(i,s,z,depth+thickness) for s,z in outline];n=len(outline)
 return make(name,front+back,[tuple(range(n)),tuple(reversed(range(n,2*n)))]+[(j,(j+1)%n,(j+1)%n+n,j+n) for j in range(n)],mat,.00007)
if KIND=='LeiXi':
 for i in range(0,8,2):
  zs=sorted(set([-.0618,-.0465,-.032]+[z for z,r in profile if -.0618<z<-.032]))
  normal=Vector((math.cos(i*math.pi/4),math.sin(i*math.pi/4),0))
  border=[facepoint(i,section(z)[4][0],z,-.00016) for z in zs]+[facepoint(i,-section(z)[4][0],z,-.00016) for z in list(reversed(zs))[1:-1]]
  ribbon('Flush thick silver diamond surround',border,normal,.00105,.00040,silver,True)
  inner=[p-normal*.00035 for p in border]
  ribbon('Dark bronze inset window lip',inner,normal,.00043,.00022,bronze,True)
else:
 for i in range(0,8,2):
  normal=Vector((math.cos(i*math.pi/4),math.sin(i*math.pi/4),0))
  border=[facepoint(i,s,z,-.00013) for s,z in [(-.84,-.065),(.84,-.065),(.84,-.040),(-.84,-.040)]]
  ribbon('Recess frame silver arris',border,normal,.00056,.00026,silver,True)
  for z in [-.0412,-.0484,-.0556]:
   shape=[(-.72,z),(0,z-.0040),(.72,z),(.48,z-.0030),(0,z-.0055),(-.48,z-.0030)]
   solid_relief('Triple bevelled folded thunder inlay',i,shape,.00026,.00066,silver)
   pts=[facepoint(i,s,zz,.00056) for s,zz in [(-.62,z-.0018),(0,z-.0059),(.62,z-.0018)]]
   ribbon('Contained blue white thunder cut',pts,normal,.00030,.00015,coremat)
  for side in [-1,1]:
   for z in [-.045,-.052,-.059]:
    pts=[facepoint(i,side*s,zz,-.00008) for s,zz in [(.92,z+.001),(.96,z),(.92,z-.001)]]
    ribbon('Small forged corner incisions',pts,normal,.00022,.00014,bronze)
for i in range(1,8,2):
 normal=(math.cos(i*math.pi/4),math.sin(i*math.pi/4),0)
 z0,z1=(-.0634,-.0298) if KIND=='LeiXi' else (-.065,-.040)
 for strand in range(2):
  pts=[]
  for t in sorted(set(list(np.linspace(0,1,81))+[(z-z0)/(z1-z0) for z,r in profile if z0<z<z1])):
   phase=t*math.pi*6+strand*math.pi;z=z0+t*(z1-z0)
   offset=.00036+.00014*math.cos(phase*2+strand*math.pi)
   pts.append(facepoint(i,.32*math.sin(phase),z,-offset))
  ribbon('Flat interwoven Nordic silver inlay',pts,normal,.00120,.00024,silver)
 # Border is a narrow inlay, and its root ends are embedded in the metal shoulder.
 for side in [-1,1]:
  pts=[facepoint(i,side*.58,z,-.00009) for z in sorted(set([z0,z1]+[z for z,r in profile if z0<z<z1]))]
  ribbon('Inset braid panel border',pts,normal,.00037,.00021,bronze)
 if KIND=='ZhenTing':
  for side in [-1,1]:
   pts=[facepoint(i,side*(.34-.2*t),-.066-t*.004,-.00017) for t in np.linspace(0,1,9)]
   ribbon('Lower bevel interlace return',pts,normal,.00058,.00022,silver)
seams=[-.0287,-.0641,-.0686,-.0734] if KIND=='LeiXi' else [-.0298,-.0342,-.0396,-.0657,-.0718,-.0743]
for z in seams:
 tube('Flush silver forged edge', [facepoint(i,-1,z,-.00004) for i in range(8)],.00020,silver,True,10)
# Bottom ornaments use proper cyclic topology, not duplicate first/last vertices and overlapping caps.
def flat_band(name,points,width,mat,closed=False):
 pts=[Vector(p) for p in points];vs=[];fs=[];normal=Vector((0,0,-1));n=len(pts)
 for j,p in enumerate(pts):
  tangent=(pts[(j+1)%n]-pts[(j-1)%n]) if closed else (pts[min(j+1,n-1)]-pts[max(0,j-1)])
  side=normal.cross(tangent.normalized())*width*.5
  vs.extend([p-side+normal*.00010,p+side+normal*.00010,p+side-normal*.00010,p-side-normal*.00010])
 for j in range(n if closed else n-1):
  for k in range(4):fs.append((j*4+k,j*4+(k+1)%4,((j+1)%n)*4+(k+1)%4,((j+1)%n)*4+k))
 if not closed:fs.extend([(3,2,1,0),tuple((n-1)*4+k for k in range(4))])
 return make(name,vs,fs,mat,.000045)
if KIND=='LeiXi':
 for r in [.0086,.0057]:
  pts=[(CX+r*math.cos(i*math.pi/2),CY+r*math.sin(i*math.pi/2),-.07517) for i in range(4)]
  flat_band('Terminal silver diamond seal',pts,.00072,silver,True)
 pts=[(CX,CY,-.07542),(CX+.0035,CY,-.07510),(CX,CY+.0047,-.07510),(CX-.0035,CY,-.07510),(CX,CY-.0047,-.07510),(CX,CY,-.0747)]
 make('Solid inset terminal storm seal',pts,[(0,2,1),(0,3,2),(0,4,3),(0,1,4),(5,1,2),(5,2,3),(5,3,4),(5,4,1)],coremat,uvs=[(.5,.5),(1,.5),(.5,1),(0,.5),(.5,0),(.5,.5)])
else:
 for r in [.0127,.0177]:ring(-.07513,r,silver,.00025)
 for strand in range(2):
  pts=[]
  for a in np.linspace(0,math.pi*2,240,endpoint=False):
   r=.0152+.00125*math.sin(a*12+strand*math.pi);z=-.07528-.00012*math.cos(a*24+strand*math.pi)
   pts.append((CX+r*math.cos(a),CY+r*math.sin(a),z))
  flat_band('Interwoven terminal silver seal border',pts,.00077,silver,True)
 for j in range(3):
  y=.0064-j*.0061;xy=[(-.0047,y+.002),(.0046,y+.0042),(-.0036,y-.0015),(.0040,y+.0003)]
  flat_band('Terminal triple thunder silver seal',[(CX+x,CY+y,-.07524) for x,y in xy],.00058,silver)
  flat_band('Terminal thunder engraving',[(CX+x,CY+y-.00057,-.07508) for x,y in xy],.00025,coremat)
for i in range(0,8,2):
 tube('Inset neck energy conductor',[facepoint(i,0,z,-.00005) for z in np.linspace(-.0273,-.0248,12)],.00013,coremat)

# Join and sew only coincident construction vertices while preserving every corner UV and normal.
bpy.ops.object.select_all(action='DESELECT')
for o in parts:o.select_set(True)
bpy.context.view_layer.objects.active=factory;bpy.ops.object.join();obj=factory
obj.name='SM_ThunderGodHammer_pommel_'+KEY+'_v2';obj.data.name=obj.name
me=obj.data;bm=bmesh.new();bm.from_mesh(me);nl=bm.loops.layers.float_vector.new('AuthoredCornerNormal')
for f,p in zip(bm.faces,me.polygons):
 for l,li in zip(f.loops,p.loop_indices):l[nl]=me.corner_normals[li].vector
bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=1e-8)
bmesh.ops.dissolve_degenerate(bm,edges=list(bm.edges),dist=1e-10)
boundary=[e for e in bm.edges if e.is_boundary];multi=[e for e in bm.edges if len(e.link_faces)>2]
if boundary or multi:
 diagnostic={'boundary_edges':len(boundary),'multi_face_edges':len(multi),'boundary_positions':[[list(v.co) for v in e.verts] for e in boundary[:32]]}
 (P/'construction_issue.json').write_text(json.dumps(diagnostic,indent=2),encoding='utf-8')
 raise RuntimeError('Structural surface not closed: '+str(diagnostic)[:500])
bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
bmesh.ops.triangulate(bm,faces=list(bm.faces));bm.normal_update()
normals=[]
for f in bm.faces:
 for l in f.loops:
  n=l[nl].normalized()
  if n.length<.5:n=f.normal.copy()
  if n.dot(f.normal)<-.1:n=-n
  normals.append(tuple(n))
bm.to_mesh(me);bm.free()
for p in me.polygons:p.use_smooth=True
me.normals_split_custom_set(normals);me.calc_loop_triangles()
positions=np.array([v.co[:] for v in me.vertices])
bpy.ops.export_scene.fbx(filepath=str(E/(obj.name+'.fbx')),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',bake_anim=False,mesh_smooth_type='FACE',use_tspace=False,path_mode='STRIP')
bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(P/(KIND+'PommelV2_Editable.blend')))
manifest={'complete':True,'id':KEY+'_pommel','mesh':obj.name,'triangles':len(me.loop_triangles),'vertices':len(me.vertices),'materials':[m.name for m in me.materials],'bounds_m':[positions.min(0).tolist(),positions.max(0).tolist()],'boundary_edges':0,'multi_face_edges':0,'protected_interface':'Native socket and lip UV/custom normals; exact cut boundary sewn into continuous body; middle braid strip rebuilt','location_cm':[0,0,-8.500000089406967],'method':'Continuous solid surface with blind recessed relief, physically closed terminals, sewn native neck and precision woven collar','normal_convention':'OpenGL; UE flip green','runtime_tested':False}
(P/'model_manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8');print(KIND+'_CLOSED_V2_EXPORTED',manifest['triangles'],flush=True)
