"""Zhen Ting: preserve factory mount/collar, build solid faceted pommel and recessed windows."""
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
 im=bpy.data.images.load(str(T/('T_ZhenTing_'+name+'.png')),check_existing=True)
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
steel=material('M_ZhenTing_ForgedSteel',(.20,.22,.25));silver=material('M_ZhenTing_SilverInlay',(1.55,1.47,1.29));bronze=material('M_ZhenTing_AgedSeams',(.70,.47,.26));coremat=material('M_ZhenTing_ThunderGroove',(1,1,1),core=True)
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
profile=[(-.0750,.0200),(-.0740,.0213),(-.0715,.0213),(-.0700,.0235),(-.0660,.0275),(-.0400,.0275),(-.0394,.0275),(-.0386,.0267),(-.0356,.0238),(-.0348,.0242),(-.0338,.0240),(-.0313,.0206),(-.0305,.0210),(-.0295,.0207),(-.0275,.0170),(-.0262,.0150),(-.02435,.0153)]
def radius(z):return float(np.interp(z,[p[0] for p in profile],[p[1] for p in profile]))
def facepoint(i,s,z,depth=0):
 a=(i-.5)*math.pi/4;b=(i+.5)*math.pi/4;r=radius(z);f=(s+1)*.5
 return Vector((CX+r*((1-f)*math.cos(a)+f*math.cos(b))-depth*math.cos(i*math.pi/4),CY+r*((1-f)*math.sin(a)+f*math.sin(b))-depth*math.sin(i*math.pi/4),z))
def make(name,verts,faces,mat,bevel=0,uvs=None):
 me=bpy.data.meshes.new(name);me.from_pydata(verts,[],faces);me.update();o=bpy.data.objects.new(name,me);bpy.context.collection.objects.link(o);me.materials.append(mat);parts.append(o)
 bm=bmesh.new();bm.from_mesh(me);bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=1e-8);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(me);bm.free();me.update()
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
# Integral octagonal forging, with recessed rectangular relief panels on four faces.
levels=sorted(set([z for z,r in profile if z<=-.0262]+[-.065,-.040]))
verts=[];faces=[]
def quad(points):
 idx=len(verts);verts.extend(points);faces.append(tuple(range(idx,idx+4)))
for i in range(8):
 for za,zb in zip(levels[:-1],levels[1:]):
  if i%2==0 and za>=-.065 and zb<=-.040:
   for lo,hi in [(-1,-.84),(.84,1)]:
    quad([facepoint(i,lo,za),facepoint(i,hi,za),facepoint(i,hi,zb),facepoint(i,lo,zb)])
  else:quad([facepoint(i,-1,za),facepoint(i,1,za),facepoint(i,1,zb),facepoint(i,-1,zb)])
shell=make('Integral three-step octagonal forging',verts,faces,steel,.00016)
def relief(name,i,outline,depth,thickness,mat,bevel=.00009):
 front=[facepoint(i,s,z,depth) for s,z in outline];back=[facepoint(i,s,z,depth+thickness) for s,z in outline];n=len(outline)
 return make(name,front+back,[tuple(range(n)),tuple(reversed(range(n,2*n)))]+[(j,(j+1)%n,(j+1)%n+n,j+n) for j in range(n)],mat,bevel)
for i in range(0,8,2):
 normal=Vector((math.cos(i*math.pi/4),math.sin(i*math.pi/4),0))
 border=[facepoint(i,s,z) for s,z in [(-.84,-.065),(.84,-.065),(.84,-.040),(-.84,-.040)]]
 inner=[p-normal*.00080 for p in border]
 make('Recessed relief panel and bevelled reveal',border+inner,[(j,(j+1)%4,(j+1)%4+4,j+4) for j in range(4)]+[(4,5,6,7)],steel,.00014)
 ribbon('Flush silver panel bezel',[p+normal*.00012 for p in border],normal,.00055,.00022,silver,True)
 for row,z in enumerate([-.0412,-.0484,-.0556]):
  # Thick-tipped double sloped silver inlay, with a genuine recessed electric cut below it.
  shape=[(-.72,z),(0,z-.0040),(.72,z),(.48,z-.0030),(0,z-.0055),(-.48,z-.0030)]
  relief('Triple folded thunder silver inlay',i,shape,.00030,.00060,silver)
  path=[facepoint(i,s,zz,.00056) for s,zz in [(-.62,z-.0018),(0,z-.0059),(.62,z-.0018)]]
  ribbon('Blue white energy cut below chevron',path,normal,.00031,.00016,coremat)
  # Tiny recessed peening at the crease gives the inset a forged joint.
  p=facepoint(i,0,z-.00465,.00015)
  tube('Silver centre crease',[p+Vector((0,0,-.00022)),p+Vector((0,0,.00022))],.00016,bronze)
 # Fine inscribed brackets fill the panel corners without bars or loose fittings.
 for side in [-1,1]:
  for z in [-.044,-.051,-.058]:
   pts=[facepoint(i,side*s,zz,-.00006) for s,zz in [(.91,z+.001),(.94,z),(.91,z-.001)]]
   tube('Forged panel edge marks',pts,.00011,bronze)
# Interwoven flat silver straps fit the four intervening facets, rooted into both rims.
for i in range(1,8,2):
 normal=(math.cos(i*math.pi/4),math.sin(i*math.pi/4),0)
 for strand in range(2):
  coords=[]
  for t in np.linspace(0,1,65):
   z=-.0650+t*.0250;phase=t*math.pi*5+strand*math.pi
   coords.append(facepoint(i,.34*math.sin(phase),z,-.00046-.00018*math.cos(phase*2+strand*math.pi)))
  ribbon('Interlaced flat Nordic silver strap',coords,normal,.00105,.00020,silver)
 for side in [-1,1]:
  coords=[facepoint(i,side*.59,z,-.00013) for z in [-.065,-.040]]
  ribbon('Narrow inset braid border',coords,normal,.00038,.00020,bronze)
 # Engraved lower bevel flourishes continue the braid into the terminal rim.
 for side in [-1,1]:
  coords=[facepoint(i,side*(.34-.2*t),-.066-t*.004,-.00022) for t in np.linspace(0,1,9)]
  ribbon('Lower shoulder knot continuation',coords,normal,.00064,.00020,silver)
# Three forged shoulder lips are integral geometry, with thin silver arrises.
for z in [-.0298,-.0342,-.0396,-.0657,-.0718,-.0743]:
 points=[facepoint(i,-1,z,-.00004) for i in range(8)]
 tube('Fine silver forged arris',points,.00022,silver,True,8)
for i in range(8):
 coords=[facepoint(i,0,z,-.00014) for z in sorted(set([-.039,-.0275]+[z for z,r in profile if -.039<z<-.0275]))]
 ribbon('Inset stepped shoulder conductor',coords,(math.cos(i*math.pi/4),math.sin(i*math.pi/4),0),.00054,.00018,bronze)
# Broad solid terminal cap, with circular flat braided inlay and a triple zigzag seal.
bottom=[(CX+radius(-.075)*math.cos((i-.5)*math.pi/4),CY+radius(-.075)*math.sin((i-.5)*math.pi/4),-.075) for i in range(8)]
make('Solid broad terminal cap',bottom,[tuple(reversed(range(8)))],steel,.00020)
def terminal_ribbon(name,points,width,mat):
 pts=[Vector(p) for p in points];vs=[];fs=[];normal=Vector((0,0,-1))
 for j,p in enumerate(pts):
  tangent=(pts[min(j+1,len(pts)-1)]-pts[max(0,j-1)]).normalized();side=normal.cross(tangent)*width*.5
  vs.extend([p-side+normal*.00010,p+side+normal*.00010,p+side-normal*.00010,p-side-normal*.00010])
 for j in range(len(pts)-1):
  for k in range(4):fs.append((j*4+k,j*4+(k+1)%4,(j+1)*4+(k+1)%4,(j+1)*4+k))
 fs.extend([(3,2,1,0),tuple((len(pts)-1)*4+k for k in range(4))]);return make(name,vs,fs,mat,.00004)
for r in [.0127,.0177]:ring(-.07510,r,silver,.00025)
for strand in range(2):
 pts=[]
 for a in np.linspace(0,2*math.pi,193):
  r=.0152+.00125*math.sin(a*12+strand*math.pi);z=-.07527-.00012*math.cos(a*24+strand*math.pi)
  pts.append((CX+r*math.cos(a),CY+r*math.sin(a),z))
 terminal_ribbon('Braided silver terminal seal border',pts,.00078,silver)
for j in range(3):
 y=.0064-j*.0061
 xy=[(-.0047,y+.002),(.0046,y+.0042),(-.0036,y-.0015),(.0040,y+.0003)]
 terminal_ribbon('Triple terminal lightning seal',[(CX+x,CY+y,-.07524) for x,y in xy],.00058,silver)
 terminal_ribbon('Terminal seal electric engraving',[(CX+x,CY+y-.00057,-.07508) for x,y in xy],.00025,coremat)
# Recessed neck conductors meet the intact factory collar.
for i in range(0,8,2):tube('Throat energy trace',[facepoint(i,0,z,-.00005) for z in np.linspace(-.0273,-.0245,15)],.00014,coremat)

# Recalculate only new geometry normals. The source collar retains its custom normals.
for o in parts[1:]:
 bm=bmesh.new();bm.from_mesh(o.data);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(o.data);bm.free()
bpy.ops.object.select_all(action='DESELECT')
for o in parts:o.select_set(True)
bpy.context.view_layer.objects.active=factory;bpy.ops.object.join();obj=factory;obj.name='SM_ThunderGodHammer_pommel_zhen_ting';obj.data.name=obj.name
obj.data.calc_loop_triangles();positions=np.array([v.co[:] for v in obj.data.vertices])
bpy.ops.export_scene.fbx(filepath=str(E/(obj.name+'.fbx')),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',bake_anim=False,mesh_smooth_type='FACE',use_tspace=False,path_mode='STRIP')
bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(P/'ZhenTingPommelV1_Editable.blend'))
manifest={'complete':True,'id':'zhen_ting_pommel','mesh':obj.name,'triangles':len(obj.data.loop_triangles),'vertices':len(obj.data.vertices),'materials':[m.name for m in obj.data.materials],'bounds_m':[positions.min(0).tolist(),positions.max(0).tolist()],'protected_interface':'Native geometry at z>=-0.02465m including UV/custom normals; native pivot z=0','location_cm':[0,0,-8.500000089406967],'method':'Preserved native collar; integral three-step shoulder; four recessed triple-chevron panels; flat woven silver inlays; wide terminal thunder seal','normal_convention':'OpenGL; UE flip green','runtime_tested':False}
(P/'model_manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8');print('ZHENTING_EDITABLE_FBX_SAVED',manifest['triangles'],flush=True)
