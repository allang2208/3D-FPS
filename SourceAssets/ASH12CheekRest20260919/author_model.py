"""Author a stock-conforming ASH cosmetic cheek rest; no weapon mechanics."""
import bpy,bmesh,json,math
import numpy as np
from pathlib import Path
from mathutils import Matrix,Vector
from mathutils.bvhtree import BVHTree

O=Path(__file__).parent;TEX=O/'Textures';TEX.mkdir(exist_ok=True)
S=json.loads((O/'stock_surface.json').read_text());F=Matrix(S['frame'])
PIVOT=Vector((-.224,.0002,-.065));X0=-.307;X1=-.141
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.open_mainfile(filepath=str(O.parent/'ASH12Surface20260919/ASH12_Surface_Editable.blend'))
r=bpy.data.objects['SK_M4_Infima'];gun=bpy.data.objects['ASH12_Export']
M=F.inverted()@r.matrix_world.inverted()@gun.matrix_world
points=[M@v.co for v in gun.data.vertices];polys=[list(p.vertices) for p in gun.data.polygons]
tree=BVHTree.FromPolygons(points,polys)
bpy.ops.wm.read_factory_settings(use_empty=True)
scene=bpy.context.scene;scene.unit_settings.system='METRIC';scene.unit_settings.scale_length=1.
textures={};materials={};parts=[]

def image(name,rgb,srgb=False):
 n=rgb.shape[0];im=bpy.data.images.new(name,width=n,height=n,alpha=True)
 im.colorspace_settings.name='sRGB' if srgb else 'Non-Color'
 rgba=np.ones((n,n,4),np.float32);rgba[:,:,:3]=rgb;im.pixels.foreach_set(rgba.ravel())
 im.filepath_raw=str(TEX/(name+'.png'));im.file_format='PNG';im.save();return im

def material(label,color,rough,metal):
 n=1024;v,u=np.mgrid[0:n,0:n].astype(np.float32)/n
 rng=np.random.default_rng(1912+len(materials));grain=rng.random((n,n),dtype=np.float32)-.5
 broad=np.sin(u*57+np.sin(v*27))*np.sin(v*73)
 h=grain*(.000007 if label=='SoftPad' else .000002)
 if label=='SoftPad':
  # Fine molded stipple, with shallow oblique grip lines on the contact pad.
  rib=(.5+.5*np.cos((u+v*.25)*math.tau*18))**16
  h+=rib*.000018
 else:rib=np.zeros_like(u)
 base=np.clip(np.array(color)[None,None,:]*(1+grain[:,:,None]*.07+broad[:,:,None]*.018),0,1)
 encoded=np.where(base<=.0031308,base*12.92,1.055*np.power(base,1/2.4)-.055)
 bc=image('T_ASH12_Cheek_'+label+'_BaseColor',encoded,True)
 orm=image('T_ASH12_Cheek_'+label+'_ORM',np.stack((1-rib*.045,np.clip(rough+grain*.06+broad*.015,0,1),np.full_like(u,metal)),axis=2))
 du=(np.roll(h,-1,1)-np.roll(h,1,1))/(.08/n);dv=(np.roll(h,-1,0)-np.roll(h,1,0))/(.08/n)
 normal=np.stack((-du,-dv,np.ones_like(u)),axis=2);normal/=np.linalg.norm(normal,axis=2)[:,:,None]
 gl=image('T_ASH12_Cheek_'+label+'_NormalGL',normal*.5+.5);normal[:,:,1]*=-1
 dx=image('T_ASH12_Cheek_'+label+'_NormalDX',normal*.5+.5)
 m=bpy.data.materials.new('ASH12Cheek_'+label);m.use_nodes=True;p=m.node_tree.nodes.get('Principled BSDF')
 p.inputs['Metallic'].default_value=metal;p.inputs['Roughness'].default_value=rough
 for im,socket in ((bc,'Base Color'),(orm,'Roughness'),(gl,'Normal')):
  t=m.node_tree.nodes.new('ShaderNodeTexImage');t.image=im
  if socket=='Roughness':
   sep=m.node_tree.nodes.new('ShaderNodeSeparateColor');m.node_tree.links.new(t.outputs['Color'],sep.inputs['Color']);m.node_tree.links.new(sep.outputs['Green'],p.inputs[socket])
  elif socket=='Normal':
   nm=m.node_tree.nodes.new('ShaderNodeNormalMap');nm.uv_map='UV0';m.node_tree.links.new(t.outputs['Color'],nm.inputs['Color']);m.node_tree.links.new(nm.outputs['Normal'],p.inputs[socket])
  else:m.node_tree.links.new(t.outputs['Color'],p.inputs[socket])
 textures[label]={'basecolor':bc.filepath_raw,'orm':orm.filepath_raw,'normal':dx.filepath_raw}
 materials[label]=m;return m

material('Shell',(.025,.026,.028),.62,.03)
material('SoftPad',(.013,.014,.016),.72,0.)
material('Steel',(.085,.09,.098),.48,.70)

def activate(ob):
 bpy.ops.object.select_all(action='DESELECT');ob.hide_set(False);ob.select_set(True);bpy.context.view_layer.objects.active=ob

def mesh(name,verts,faces,label,bevel=0):
 me=bpy.data.meshes.new(name);me.from_pydata(verts,[],faces);me.update()
 ob=bpy.data.objects.new(name,me);scene.collection.objects.link(ob);me.materials.append(materials[label]);activate(ob)
 bm=bmesh.new();bm.from_mesh(me);bmesh.ops.recalc_face_normals(bm,faces=bm.faces);bm.to_mesh(me);bm.free()
 if bevel:
  mod=ob.modifiers.new('Soft molded edge','BEVEL');mod.width=bevel;mod.segments=3
  mod.limit_method='ANGLE';mod.angle_limit=.5;bpy.ops.object.modifier_apply(modifier=mod.name)
 for p in me.polygons:p.use_smooth=True
 parts.append(ob);return ob

def smooth(t):t=max(0,min(1,t));return t*t*(3-2*t)

def contact(x,theta):
 # The rear buttplate shoulder is wider; sample the actual surface per section.
 edge=min((x-X0)/.014,(X1-x)/.014);zc=-.078+.010*(1-smooth(edge))
 d=Vector((0,math.cos(theta),math.sin(theta)));c=Vector((x,.0002,zc))
 hit,n,_,_=tree.ray_cast(c+d*.065,-d,.1)
 if hit is None:raise RuntimeError('No receiver surface at '+str((x,theta)))
 if n.dot(d)<0:n=-n
 # Mesh normals at broad panels are reliable contact directions.
 return hit,n.normalized()

def saddle(name,x0,x1,a0,a1,label,inner,thickness,steps=68,across=40):
 verts=[];uv=[]
 for layer in range(2):
  for i in range(steps+1):
   x=x0+(x1-x0)*i/steps;end=min((x-x0)/.011,(x1-x)/.011);fade=smooth(end)
   for j in range(across+1):
    a=a0+(a1-a0)*j/across
    # Rounded plan ends; contour remains on the current receiver surface.
    xx=x+(1-fade)*.006*abs(math.cos(a))*(1 if i<steps/2 else -1)
    p,n=contact(xx,a);s=max(0,math.sin(a))
    depth=inner(s,xx)+(thickness(s)*(.38+.62*fade) if layer else 0)
    verts.append(p+n*depth)
    uv.append(((xx-X0)/.04,a*.024/.04))
 row=across+1;sheet=(steps+1)*row;faces=[]
 for layer in range(2):
  for i in range(steps):
   for j in range(across):
    k=layer*sheet+i*row+j;f=(k,k+1,k+row+1,k+row);faces.append(f if layer else f[::-1])
 for i in range(steps):
  for j in (0,across):
   k=i*row+j;faces.append((k,k+row,k+row+sheet,k+sheet))
 for j in range(across):
  for i in (0,steps):
   k=i*row+j;faces.append((k,k+1,k+1+sheet,k+sheet))
 ob=mesh(name,verts,faces,label)
 layer=ob.data.uv_layers.new(name='UV0')
 for p in ob.data.polygons:
  # Flat sidewalls need their own nondegenerate physical projection.
  sidewall=len({int(v>=sheet) for v in p.vertices})>1
  axis=max(range(3),key=lambda k:abs(p.normal[k]));axes=[k for k in range(3) if k!=axis]
  for li in p.loop_indices:
   vi=ob.data.loops[li].vertex_index;v=ob.data.vertices[vi].co
   layer.data[li].uv=(v[axes[0]]/.04,v[axes[1]]/.04) if sidewall else uv[vi]
 return ob

shell=saddle('Fitted_Saddle_Shell',X0,X1,0,math.pi,'Shell',lambda s,x:.00035,lambda s:.0025+.0012*s)
pad=saddle('Overmold_Cheek_Pad',X0+.005,X1-.008,.20,math.pi-.20,'SoftPad',
 lambda s,x:.00045+(.0025+.0012*s)*(.38+.62*smooth(min((x-X0)/.011,(X1-x)/.011))),lambda s:.0013+.0022*s)

def box(name,loc,size,label,bevel):
 bpy.ops.mesh.primitive_cube_add(size=1,location=loc);ob=bpy.context.object;ob.name=name;ob.scale=size
 bpy.ops.object.transform_apply(location=True,rotation=False,scale=True);ob.data.materials.append(materials[label]);activate(ob)
 mod=ob.modifiers.new('Rounded edge','BEVEL');mod.width=bevel;mod.segments=4;bpy.ops.object.modifier_apply(modifier=mod.name)
 for p in ob.data.polygons:p.use_smooth=True
 parts.append(ob);return ob

def screw(x,side):
 y=.0002+side*.0247;z=-.071
 verts=[];faces=[];segments=48
 rings=[(.0034,y),(.0031,y+side*.0005),(.00145,y+side*.0005),(.00145,y-side*.00015)]
 for rad,yy in rings:
  for i in range(segments):
   a=i*math.tau/segments;verts.append((x+rad*math.cos(a),yy,z+rad*math.sin(a)))
 for k in range(3):
  for i in range(segments):faces.append((k*segments+i,k*segments+(i+1)%segments,(k+1)*segments+(i+1)%segments,(k+1)*segments+i))
 faces.extend([tuple(range(segments-1,-1,-1)),tuple(range(3*segments,4*segments))])
 return mesh('Recessed_Fastener',verts,faces,'Steel')

for side in (-1,1):
 for x in (-.274,-.175):
  box('Side_Fixing_Plate',(x,.0002+side*.0232,-.071),(.023,.0027,.014),'Steel',.0013)
  screw(x,side)

# Curved pieces already have physical surface UVs; small fittings get box UVs.
for ob in parts:
 if not ob.data.uv_layers:
  uv=ob.data.uv_layers.new(name='UV0')
  for f in ob.data.polygons:
   axis=max(range(3),key=lambda k:abs(f.normal[k]));a,b=[k for k in range(3) if k!=axis]
   for li in f.loop_indices:
    p=ob.data.vertices[ob.data.loops[li].vertex_index].co;uv.data[li].uv=(p[a]/.04,p[b]/.04)
 ob.data.uv_layers.active_index=0;ob.data.uv_layers[0].active_render=True
 ob.data.transform(Matrix.Translation(-PIVOT))
 activate(ob);w=ob.modifiers.new('Weighted edge normals','WEIGHTED_NORMAL');w.keep_sharp=True;bpy.ops.object.modifier_apply(modifier=w.name)

# Preserve independent editable parts and an exact installation reference.
source=bpy.data.collections.new('Editable_CheekRest_Parts');scene.collection.children.link(source)
for ob in parts:
 for c in list(ob.users_collection):c.objects.unlink(ob)
 source.objects.link(ob)
copies=[]
for ob in parts:
 copy=ob.copy();copy.data=ob.data.copy();scene.collection.objects.link(copy);copies.append(copy)
bpy.ops.object.select_all(action='DESELECT')
for ob in copies:ob.select_set(True)
bpy.context.view_layer.objects.active=copies[0];bpy.ops.object.join();model=bpy.context.object;model.name='SM_ASH12_CheekRest'
tri=model.modifiers.new('Export triangles','TRIANGULATE');bpy.ops.object.modifier_apply(modifier=tri.name)
fbx=O/(model.name+'.fbx')
bpy.ops.export_scene.fbx(filepath=str(fbx),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',bake_anim=False,use_tspace=True,mesh_smooth_type='FACE')
for ob in parts:ob.hide_render=True;ob.hide_set(True)
refme=bpy.data.meshes.new('ASH_Receiver_Reference');refme.from_pydata([p-PIVOT for p in points],[],polys)
ref=bpy.data.objects.new('ASH_Receiver_Reference_DO_NOT_EXPORT',refme);scene.collection.objects.link(ref);ref.hide_render=True;ref.hide_set(True)

# Production card icon only; no gameplay/acceptance preview rendering.
scene.render.engine='CYCLES';scene.cycles.samples=48;scene.cycles.use_denoising=True
scene.render.resolution_x=scene.render.resolution_y=1024;scene.render.resolution_percentage=100
scene.render.film_transparent=True;scene.render.image_settings.file_format='PNG';scene.render.image_settings.color_mode='RGBA'
scene.world=bpy.data.worlds.new('IconWorld');scene.world.use_nodes=True;scene.world.node_tree.nodes['Background'].inputs['Strength'].default_value=.35
center=Vector((0,0,.002))
data=bpy.data.cameras.new('IconCamera');camera=bpy.data.objects.new('IconCamera',data);scene.collection.objects.link(camera)
camera.location=center+Vector((0,.65,0));camera.rotation_euler=(center-camera.location).to_track_quat('-Z','Y').to_euler()
data.type='ORTHO';data.ortho_scale=.166/.83;scene.camera=camera
for i,(loc,power,size) in enumerate([((.05,.22,.25),13,.3),((-.1,-.15,.12),9,.2),((.12,.15,-.08),5,.18)]):
 d=bpy.data.lights.new('IconLight'+str(i),'AREA');d.energy=power;d.size=size
 l=bpy.data.objects.new(d.name,d);scene.collection.objects.link(l);l.location=loc;l.rotation_euler=(center-l.location).to_track_quat('-Z','Y').to_euler()
scene.render.filepath=str(O/'ue_ash12_stock_ash12_cheek_rest.png')
bpy.ops.wm.save_as_mainfile(filepath=str(O/'ASH12_CheekRest_Editable.blend'))
report={'mesh':model.name,'fbx':str(fbx),'source':'../ASH12Surface20260919/ASH12_Surface_Editable.blend',
 'coordinate_frame':'ASH sight rail frame, +X forward, Blender +Y left, +Z up; pivot in that frame',
 'pivot_rail_m':list(PIVOT),'runtime_pivot_cm':[-22.4,-.02,-6.5],
 'span_rail_m':[X0,X1],'fit':'Underside sampled directly from current receiver surface; factory buttpad retained',
 'parts':[o.name for o in parts],'triangles':len(model.data.polygons),'textures':textures,
 'icon':scene.render.filepath,'exclusive_weapon':'ue_ash12','option_id':'ash12_cheek_rest','stats':'Cosmetic only',
 'provenance':'Original local procedural exterior fitted to existing project ASH mesh; host source licensing unchanged',
 'testing':'Not performed; user tests in game.'}
(O/'authoring.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
bpy.ops.render.render(write_still=True)
print('ASH12_CHEEK_REST_AUTHORED '+str(fbx),flush=True)
