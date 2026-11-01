"""Lei Xi: preserve factory mount/collar, build solid faceted pommel and recessed windows."""
import bpy,bmesh,math,json,numpy as np
from mathutils import Vector,Matrix
from pathlib import Path
P=Path(__file__).resolve().parent;T=P/'Textures';E=P/'Export';E.mkdir(exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True);bpy.context.preferences.filepaths.save_version=0
with bpy.data.libraries.load(str(P.parent/'ModulesV1/ThunderGodHammer_Modular_Editable.blend'),link=False) as(a,b):b.objects=['SM_ThunderGodHammer_pommel_factory']
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
steel=material('M_LeiXi_ForgedSteel',(.20,.22,.25));silver=material('M_LeiXi_SilverInlay',(1.55,1.47,1.29));bronze=material('M_LeiXi_AgedSeams',(.70,.47,.26));coremat=material('M_LeiXi_StormCore',(1,1,1),core=True)
# Restore the retained native material from its current original maps.
m=src.materials[0];m.use_nodes=True;n=m.node_tree.nodes;l=m.node_tree.links;n.clear();out=n.new('ShaderNodeOutputMaterial');bs=n.new('ShaderNodeBsdfPrincipled');l.new(bs.outputs[0],out.inputs[0])
for name in ['BaseColor','MetallicRoughness','Normal']:
 tex=n.new('ShaderNodeTexImage');tex.image=bpy.data.images.load(str(P.parent/'Textures'/(name+'.jpg')),check_existing=True)
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
   vi=me.loops[li].vertex_index;co=me.vertices[vi].co
   uv.data[li].uv=uvs[vi] if uvs else (co[axes[0]]*24,co[axes[1]]*24)
 if bevel:
  bpy.ops.object.select_all(action='DESELECT');o.select_set(True);bpy.context.view_layer.objects.active=o
  b=o.modifiers.new('Forged edge radii','BEVEL');b.width=bevel;b.segments=3;b.affect='EDGES'
  bpy.ops.object.modifier_apply(modifier=b.name)
  w=o.modifiers.new('Weighted corner normals','WEIGHTED_NORMAL');w.keep_sharp=True;bpy.ops.object.modifier_apply(modifier=w.name)
 return o
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
# Close the real cut face into the new throat. The retained native boundary is
# sampled, so tiny asymmetric factory edges do not leave an annular gap.
boundary=[v.co.copy() for v in src.vertices if abs(v.co.z+.02465)<.000005]
samples=sorted([(math.atan2(p.y-CY,p.x-CX)%(2*math.pi),math.hypot(p.x-CX,p.y-CY)) for p in boundary])
angles=[a for a,r in samples];radii=[r for a,r in samples]
angles=[angles[-1]-2*math.pi]+angles+[angles[0]+2*math.pi];radii=[radii[-1]]+radii+[radii[0]]
tv=[];tf=[]
for j in range(128):
 a=j*2*math.pi/128;r=float(np.interp(a,angles,radii));tv.append((CX+r*math.cos(a),CY+r*math.sin(a),-.02462))
 face=int(math.floor((a+math.pi/8)/(math.pi/4)))%8;delta=(a-face*math.pi/4+math.pi)%(2*math.pi)-math.pi;s=math.tan(delta)/math.tan(math.pi/8)
 tv.append(facepoint(face,s,-.0262))
for j in range(128):k=(j+1)%128;tf.append((j*2,k*2,k*2+1,j*2+1))
make('Native collar continuous throat transition',tv,tf,steel)
# Continuous octagonal shell: alternating facets have genuine diamond openings.
zt=-.032;zc=-.0465;zb=-.0618
levels=sorted(set([z for z,r in profile]+[zt,zc,zb]));verts=[];faces=[]
def window(z):
 return max(0,.64*((z-zb)/(zc-zb) if z<zc else (zt-z)/(zt-zc))) if zb<=z<=zt else 0
def quad(points):
 idx=len(verts);verts.extend(points)
 if (points[0]-points[1]).length<1e-8:faces.append((idx,idx+2,idx+3))
 elif (points[2]-points[3]).length<1e-8:faces.append((idx,idx+1,idx+2))
 else:faces.append((idx,idx+1,idx+2,idx+3))
for i in range(8):
 for za,zz in zip(levels[:-1],levels[1:]):
  wa=window(za) if i%2==0 else 0;wb=window(zz) if i%2==0 else 0
  if max(wa,wb)<=0:quad([facepoint(i,-1,za),facepoint(i,1,za),facepoint(i,1,zz),facepoint(i,-1,zz)])
  else:
   quad([facepoint(i,-1,za),facepoint(i,-wa,za),facepoint(i,-wb,zz),facepoint(i,-1,zz)])
   quad([facepoint(i,wa,za),facepoint(i,1,za),facepoint(i,1,zz),facepoint(i,wb,zz)])
shell=make('Faceted structural shell',verts,faces,steel,.00018)
# Diamond reveals + real bevelled silver rims and recessed lightning glass.
for i in range(0,8,2):
 zs=sorted(set([zb,zc,zt]+[z for z,r in profile if zb<z<zt]))
 border=[facepoint(i,window(z),z) for z in zs]+[facepoint(i,-window(z),z) for z in list(reversed(zs))[1:-1]]
 inward=Vector((math.cos(i*math.pi/4),math.sin(i*math.pi/4),0))
 inside=[p-inward*.00165 for p in border];wallverts=border+inside;k=len(border)
 make('Deep diamond reveal',wallverts,[(j,(j+1)%k,(j+1)%k+k,j+k) for j in range(k)],bronze,.00012)
 ribbon('Inlaid diamond silver bezel',[p+inward*.00042 for p in border],inward,.00110,.0004,silver,True)
 cv=[facepoint(i,0,zc,.0018)]+inside;uv=[(.5,.5)]
 for p in inside:
  z=p.z;s=((p-Vector((CX,CY,z))).dot(Vector((-math.sin(i*math.pi/4),math.cos(i*math.pi/4),0))))/(radius(z)*math.sin(math.pi/8))
  uv.append((.5+s/(2*.64),(z-zb)/(zt-zb)))
 make('Contained storm aperture',cv,[(0,j+1,(j+1)%k+1) for j in range(k)],coremat,uvs=uv)
# Curving interwoven silver strips on solid faces; follow the shoulders instead
# of using straight bars. Burial depth is sub-millimetre; joints meet the rims.
for i in range(1,8,2):
 for strand in range(2):
  coords=[]
  for t in np.linspace(0,1,121):
   z=-.0634+t*.0345;phase=t*math.pi*6+strand*math.pi
   s=.34*math.sin(phase);depth=-.00046-.00018*math.cos(phase*2+strand*math.pi)
   coords.append(facepoint(i,s,z,depth))
  ribbon('Interlaced silver ribbon',coords,(math.cos(i*math.pi/4),math.sin(i*math.pi/4),0),.00135,.00020,silver)
 # Fine borders frame the native-style braid into the facet without thick rails.
 for side in [-1,1]:tube('Inset facet fillet',[facepoint(i,side*.57,z,-.00004) for z in np.linspace(-.0624,-.0303,40)],.00022,bronze)
# Narrow forged shoulder borders and stepped terminal cap.
for z in [-.0287,-.0641,-.0686,-.0734]:
 points=[facepoint(i,-1,z,-.00004) for i in range(8)]
 tube('Octagonal fine seam',points,.00026,silver,True,8)
bottom=[(CX+radius(-.075)*math.cos((i-.5)*math.pi/4),CY+radius(-.075)*math.sin((i-.5)*math.pi/4),-.075) for i in range(8)]
make('Solid end face',bottom,[tuple(reversed(range(8)))],steel,.00018)
for r in [.0087,.0056]:
 points=[(CX+r*math.cos(i*math.pi/2),CY+r*math.sin(i*math.pi/2),-.07512) for i in range(4)]
 tube('Terminal nested diamond',points,.00042,silver,True,8)
make('Terminal storm jewel',[(CX,CY,-.07522),(CX+.0036,CY,-.07508),(CX,CY+.0048,-.07508),(CX-.0036,CY,-.07508),(CX,CY-.0048,-.07508)],[(0,2,1),(0,3,2),(0,4,3),(0,1,4)],coremat,uvs=[(.5,.5),(1,.5),(.5,1),(0,.5),(.5,0)])
# Add precisely inset throat conductors, rooted in collar/body.
for i in range(0,8,2):tube('Throat energy trace',[facepoint(i,0,z,-.00005) for z in np.linspace(-.0285,-.0245,15)],.00016,coremat)
# Recalculate only new geometry normals. The source collar retains its custom normals.
for o in parts[1:]:
 bm=bmesh.new();bm.from_mesh(o.data);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(o.data);bm.free()
bpy.ops.object.select_all(action='DESELECT')
for o in parts:o.select_set(True)
bpy.context.view_layer.objects.active=factory;bpy.ops.object.join();obj=factory;obj.name='SM_ThunderGodHammer_pommel_lei_xi';obj.data.name=obj.name
obj.data.calc_loop_triangles();positions=np.array([v.co[:] for v in obj.data.vertices])
bpy.ops.export_scene.fbx(filepath=str(E/(obj.name+'.fbx')),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',bake_anim=False,mesh_smooth_type='FACE',use_tspace=False,path_mode='STRIP')
bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(P/'LeiXiPommelV1_Editable.blend'))
manifest={'complete':True,'id':'lei_xi_pommel','mesh':obj.name,'triangles':len(obj.data.loop_triangles),'vertices':len(obj.data.vertices),'materials':[m.name for m in obj.data.materials],'bounds_m':[positions.min(0).tolist(),positions.max(0).tolist()],'protected_interface':'Native geometry at z>=-0.02465m including UV/custom normals; native pivot z=0','location_cm':[0,0,-8.500000089406967],'method':'Precision solid shell; four recessed diamond windows; woven inlays and stepped terminal diamond','normal_convention':'OpenGL; UE flip green','runtime_tested':False}
(P/'model_manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8');print('LEIXI_EDITABLE_FBX_SAVED',manifest['triangles'],flush=True)
