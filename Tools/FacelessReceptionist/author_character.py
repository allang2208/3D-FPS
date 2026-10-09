"""Author Meshy receptionist on the intact Nurse skeleton. Background production only."""
import bpy,bmesh,json,math,sys
import numpy as np
from pathlib import Path
from mathutils import Vector,Matrix,Quaternion
from mathutils.bvhtree import BVHTree
from mathutils.geometry import barycentric_transform
ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/FacelessReceptionist20261007')
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'Authoring/Inputs.blend'))
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
 return Matrix.Translation(Vector(target))@Matrix.Rotation(angle,4,'Y')@Matrix.Scale(scale,4)@Matrix.Translation(a)
def major(n):
 if n.startswith(('thumb','index','middle','ring','pinky','wrist')):return 'hand_'+n[-1]
 for p in ['upperarm','lowerarm','thigh','calf','foot','ball']:
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
 MAP['hand_'+side]=turn(HEAD['hand_'+side],wrist,sign*math.radians(22))
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
points=[v.co.copy() for v in body.data.vertices]
body_weights=[]
for p in points:
 ws=sample(p,bvh,dp,tri,dw)
 if p.z>1.64:ws={'head':1.}
 elif p.z>1.585:
  t=max(0,min(1,(p.z-1.585)/.055));ws={'head':t,'neck_02':1-t}
 body_weights.append(norm(ws))
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
suit=textile('Receptionist_Suit',(.20,.235,.265))
shirt=textile('Receptionist_Shirt',(.69,.685,.625),.84)
leather=textile('Receptionist_Shoes',(.10,.115,.125),.47,leather=True)
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
levels=np.linspace(1.005,1.495,29)
jacket=garment_rings('Receptionist_Blazer_Body',levels,96,lambda z,t:radial(z,gap(z)+(2*math.pi-2*gap(z))*t,.017),suit)
shell(jacket,.0028);kinds[jacket.name]='jacket'
# Shoulder yoke bridges the shoulder line to an open collar without sealing the neck.
def yoke(z,t):
 f=(z-1.495)/.062;theta=gap(z)+(2*math.pi-2*gap(z))*t
 p=radial(1.495,theta,.018);inner=Vector((.060*math.sin(theta),.006-.052*math.cos(theta),1.557))
 return p.lerp(inner,f)
o=garment_rings('Receptionist_Blazer_ShoulderYoke',np.linspace(1.495,1.557,8),96,yoke,suit);shell(o,.0028)
o=garment_rings('Receptionist_Shirt_Body',np.linspace(1.03,1.505,26),80,lambda z,t:radial(z,t*2*math.pi,.006),shirt);shell(o,.0015)
def shirt_top(z,t):
 f=(z-1.505)/.066;theta=t*2*math.pi
 p=radial(1.505,theta,.006)
 return p.lerp(Vector((.051*math.sin(theta),.005-.045*math.cos(theta),1.571)),f)
o=garment_rings('Receptionist_Shirt_Shoulder',np.linspace(1.505,1.571,8),80,shirt_top,shirt);shell(o,.0015)
o=garment_rings('Receptionist_Shirt_CollarStand',np.linspace(1.561,1.588,5),64,lambda z,t:(.052*math.sin(2*math.pi*t),.005-.046*math.cos(2*math.pi*t),z),shirt);shell(o,.002)
# Long sleeves fitted around actual arm sections, with explicit cuff openings.
for side,sign in [('l',1),('r',-1)]:
 a,e,w=(Vector(TARGET[side][n]) for n in ['shoulder','elbow','wrist'])
 centers=[]
 for f in np.linspace(-.12,.98,30):
  centers.append(a.lerp(e,f*2) if f<.5 else e.lerp(w,(f-.5)*2))
 vs=[];uv=[]
 for j,c in enumerate(centers):
  tangent=((centers[min(j+1,len(centers)-1)]-centers[max(j-1,0)])).normalized()
  u=Vector((0,1,0));u=(u-tangent*u.dot(tangent)).normalized();v=tangent.cross(u).normalized()
  for i in range(49):
   theta=i/48*2*math.pi;direction=u*math.cos(theta)+v*math.sin(theta)
   hit=body_bvh.ray_cast(c,direction,.145)
   radius=(hit[0]-c).length if hit[0] is not None else .039
   radius=max(.031,min(.080,radius))+.012
   # Small compression folds around the elbow.
   radius+=.0018*math.sin(j*2.0+theta*2)*math.exp(-((j-15)/5)**2)
   vs.append(tuple(c+direction*radius));uv.append((i/48,j/29*2))
 faces=[]
 for j in range(29):
  for i in range(48):
   k=j*49+i;faces.append((k,k+1,k+50,k+49))
 o=mesh('Receptionist_Blazer_Sleeve_'+side,vs,faces,suit,uv);shell(o,.0025)
 # Shirt cuffs occupy the final wrist interval.
 c0=e.lerp(w,.90);c1=e.lerp(w,1.04);axis=(c1-c0).normalized()
 u=Vector((0,1,0));u=(u-axis*u.dot(axis)).normalized();v=axis.cross(u).normalized()
 def cuff(z,t,c0=c0,c1=c1,u=u,v=v):
  return c0.lerp(c1,z)+(u*math.cos(t*2*math.pi)*.037+v*math.sin(t*2*math.pi)*.034)
 o=garment_rings('Receptionist_Shirt_Cuff_'+side,np.linspace(0,1,5),48,cuff,shirt);shell(o,.002)
# Flared knee-length skirt; an overlapping back vent leaves stride allowance.
skirt_levels=np.linspace(.475,1.13,40)
def skirtpoint(z,t):
 theta=t*2*math.pi;f=(1.13-z)/.655
 rx=float(np.interp(z,[.475,.65,.85,.96,1.03,1.13],[.247,.227,.215,.207,.18,.147]))
 ry=float(np.interp(z,[.475,.65,.85,.96,1.03,1.13],[.151,.143,.142,.151,.140,.110]))
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
o=garment_rings('Receptionist_Skirt_Waistband',np.linspace(1.092,1.13,5),96,lambda z,t:Vector(skirtpoint(z,t))+Vector((math.sin(t*2*math.pi)*.003,-math.cos(t*2*math.pi)*.003,0)),suit);shell(o,.003)
# Lapels are real folded strips, not painted onto the jacket.
for sign in [-1,1]:
 vs=[];uv=[]
 for j,z in enumerate(np.linspace(1.165,1.53,28)):
  theta=gap(min(z,1.495));p=radial(min(z,1.495),sign*theta,.021)
  if z>1.495:p.z=z;p.x=sign*(.06+(1.53-z)*1.2);p.y=-.055
  width=float(np.interp(z,[1.165,1.3,1.435,1.46,1.53],[.004,.032,.047,.022,.019]))
  for i in range(5):
   f=i/4;v=p+Vector((sign*width*f,-.008*math.sin(f*math.pi)-.002,f*.010))
   vs.append(tuple(v));uv.append((f,j/27*2))
 faces=[(j*5+i,j*5+i+1,(j+1)*5+i+1,(j+1)*5+i) for j in range(27) for i in range(4)]
 o=mesh('Receptionist_Lapel_'+str(sign),vs,faces,suit,uv);shell(o,.0025)
 # Point collar tip folds over the shirt, clear of the neck.
 vs=[(sign*.017,-.046,1.58),(sign*.061,-.052,1.565),(sign*.079,-.090,1.505),(sign*.035,-.092,1.535)]
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
 bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.normal_update()
 for v in bm.verts:
  # Envelope expands forefoot and merges the toe grooves visually.
  v.co+=v.normal*.006
  if v.co.z<.012:v.co.z=.004
 bm.to_mesh(o.data);bm.free()
 active(o)
 rem=o.modifiers.new('SmoothShoeEnvelope','REMESH');rem.mode='VOXEL';rem.voxel_size=.0045;rem.use_smooth_shade=True;apply(o,rem)
 sm=o.modifiers.new('LeatherSurface','SMOOTH');sm.factor=.8;sm.iterations=7;apply(o,sm)
 sub=o.modifiers.new('UpperFinish','SUBSURF');sub.levels=1;apply(o,sub)
 o.data.materials.clear();o.data.materials.append(leather)
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
# Retain authored independent objects; donor geometry is not in delivered character.
bpy.data.objects.remove(donor,do_unlink=True)
for o in list(bpy.context.scene.objects):
 if o not in parts+[body,rig]:bpy.data.objects.remove(o,do_unlink=True)
rig.name='root'
rig.show_in_front=True
for m in list(bpy.data.materials):
 if not m.users:bpy.data.materials.remove(m)
for im in list(bpy.data.images):
 if not im.users:bpy.data.images.remove(im)
bpy.context.scene.unit_settings.system='METRIC';bpy.context.scene.unit_settings.scale_length=1.
bpy.ops.object.select_all(action='SELECT');bpy.context.view_layer.objects.active=body
# Source contains complete body and separate clothing, with original Meshy UVs.
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'Authoring/FacelessReceptionist_V01.blend'))
def selected(objs):
 bpy.ops.object.select_all(action='DESELECT')
 for o in objs:o.select_set(True)
 bpy.context.view_layer.objects.active=rig
selected([rig,body]+parts)
bpy.ops.export_scene.gltf(filepath=str(ROOT/'Delivery/FacelessReceptionist_V01.glb'),export_format='GLB',use_selection=True,export_animations=False,export_skins=True,export_all_influences=True)
bpy.ops.export_scene.fbx(filepath=str(ROOT/'Delivery/SK_FacelessReceptionist_V01.fbx'),use_selection=True,object_types={'ARMATURE','MESH'},add_leaf_bones=False,bake_anim=False,axis_forward='-Y',axis_up='Z',apply_unit_scale=True,use_armature_deform_only=False,mesh_smooth_type='FACE',path_mode='COPY',embed_textures=False)
selected([rig,body])
bpy.ops.export_scene.fbx(filepath=str(ROOT/'Delivery/SK_FacelessReceptionist_Body_V01.fbx'),use_selection=True,object_types={'ARMATURE','MESH'},add_leaf_bones=False,bake_anim=False,axis_forward='-Y',axis_up='Z',apply_unit_scale=True,use_armature_deform_only=False,mesh_smooth_type='FACE')
selected([rig]+parts)
bpy.ops.export_scene.gltf(filepath=str(ROOT/'Delivery/FacelessReceptionist_Clothing_V01.glb'),export_format='GLB',use_selection=True,export_animations=False,export_skins=True,export_all_influences=True)
receipt={'stage':'authored_and_exported','source':'Source/Meshy_AI_Faceless_Mannequin_in_1007155702_texture.glb','source_triangles':len(bodytris),'skeleton_source':'/Game/ZombieFemale/Asset/Meshes/SK_ZombieFemale','rig_bones':len(rig.data.bones),'rig_object_matrix':[list(x) for x in rig.matrix_world],'fit_targets':TARGET,'body_vertices':len(body.data.vertices),'parts':[{'name':o.name,'vertices':len(o.data.vertices),'triangles':sum(len(p.vertices)-2 for p in o.data.polygons),'materials':[m.name for m in o.data.materials]} for o in parts],'runtime_tested':False,'rendered':False,'notes':['Full original Meshy body preserved in author source and exports.','Clothing uses skin deformation; no runtime cloth simulation has been authored.','No visual or gameplay acceptance performed.']}
(ROOT/'authoring_receipt.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
print('RECEPTIONIST_AUTHORING_SAVED '+json.dumps({'body_triangles':len(bodytris),'parts':len(parts),'garment_triangles':sum(x['triangles'] for x in receipt['parts']),'bones':len(rig.data.bones)}),flush=True)
