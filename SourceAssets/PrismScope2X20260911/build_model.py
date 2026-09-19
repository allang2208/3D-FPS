import bpy,bmesh,math,json
from pathlib import Path
from mathutils import Vector
P=Path(__file__).parent
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(P/'scope2x_textured_master_00001_.glb'))
body=next(o for o in bpy.context.scene.objects if o.type=='MESH');bpy.context.view_layer.objects.active=body;body.select_set(True);bpy.ops.object.transform_apply(location=True,rotation=True,scale=True)
lo=Vector([min(v.co[a] for v in body.data.vertices) for a in range(3)]);hi=Vector([max(v.co[a] for v in body.data.vertices) for a in range(3)])
ends=[v.co for v in body.data.vertices if v.co.x>hi.x-.025 or v.co.x<lo.x+.025]
cy=(min(v.y for v in ends)+max(v.y for v in ends))/2;cz=(min(v.z for v in ends)+max(v.z for v in ends))/2
scale=13/(hi.x-lo.x)
source_normals=[Vector(n.vector) for n in body.data.corner_normals]
for v in body.data.vertices:v.co=Vector((-(v.co.x-(lo.x+hi.x)/2)*scale,-(v.co.y-cy)*scale,(v.co.z-cz)*scale+4))
import statistics
maxz=max(v.co.z for v in body.data.vertices);topvs=[v.co for v in body.data.vertices if v.co.z>maxz-.15];topx=statistics.median(v.x for v in topvs);topy=statistics.median(v.y for v in topvs)
symin=min(v.co.y for v in body.data.vertices);symax=max(v.co.y for v in body.data.vertices);side_sign=-1 if abs(symin)>abs(symax) else 1;side_edge=max(abs(symin),abs(symax));sv=[v.co for v in body.data.vertices if v.co.y*side_sign>side_edge-.15];sidex=statistics.median(v.x for v in sv);sidez=statistics.median(v.z for v in sv)
body.data.normals_split_custom_set([(-n.x,-n.y,n.z) for n in source_normals])
normal_source=body.copy();normal_source.data=body.data.copy();normal_source.name='HighSurfaceNormals';bpy.context.collection.objects.link(normal_source);normal_source.hide_render=True;normal_source.hide_set(True)
bm=bmesh.new();bm.from_mesh(body.data);bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=.0003)
bmesh.ops.bisect_plane(bm,geom=list(bm.verts)+list(bm.edges)+list(bm.faces),dist=.00001,plane_co=(0,0,1.65),plane_no=(0,0,1),clear_inner=True,clear_outer=False)
bmesh.ops.holes_fill(bm,edges=[e for e in bm.edges if e.is_boundary],sides=0);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(body.data);bm.free()
# Rebuild a closed surface before cutting the lens bore; the generated export contains overlapping sheets.
body.data.remesh_voxel_size=.025;body.data.remesh_voxel_adaptivity=0;bpy.ops.object.voxel_remesh()
bm=bmesh.new();bm.from_mesh(body.data);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));
if bm.calc_volume(signed=True)<0:bmesh.ops.reverse_faces(bm,faces=list(bm.faces))
bm.to_mesh(body.data);bm.free();body.data.calc_loop_triangles()
mod=body.modifiers.new('Remove small generated ripples','SMOOTH');mod.factor=.35;mod.iterations=3;bpy.ops.object.modifier_apply(modifier=mod.name)
# Retain generated focus-ring and control details; retopologize the broad optical housing.
bm=bmesh.new();bm.from_mesh(body.data)
remove=[]
for f in bm.faces:
 c=f.calc_center_median()
 if not (c.x<-4.3 or (c.z>maxz-.70 and abs(c.x-topx)<1.3 and abs(c.y-topy)<1.3) or (c.y*side_sign>side_edge-.55 and abs(c.x-sidex)<1.1 and abs(c.z-sidez)<1.1)) :remove.append(f)
bmesh.ops.delete(bm,geom=remove,context='FACES')
bmesh.ops.holes_fill(bm,edges=[e for e in bm.edges if e.is_boundary],sides=0);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(body.data);bm.free()
for v in body.data.vertices:
 if v.co.z>maxz-.71:v.co.z-=.65
maxz-=.65
bpy.ops.object.voxel_remesh();body.data.calc_loop_triangles()
mod=body.modifiers.new('Preserve generated silhouette','DECIMATE');mod.ratio=min(1,11000/len(body.data.loop_triangles));bpy.ops.object.modifier_apply(modifier=mod.name)
# Machine a coaxial clear bore through both generated placeholder lenses.
bm=bmesh.new();bm.from_mesh(body.data);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
pending=set(bm.faces)
while pending:
 seed=pending.pop();component={seed};stack=[seed]
 while stack:
  for e in stack.pop().edges:
   for f in e.link_faces:
    if f in pending:pending.remove(f);component.add(f);stack.append(f)
 volume=sum(f.calc_center_median().dot(f.normal)*f.calc_area()/3 for f in component)
 if volume<0:bmesh.ops.reverse_faces(bm,faces=list(component))
bm.to_mesh(body.data);bm.free()
bpy.ops.mesh.primitive_cylinder_add(vertices=128,radius=1.22,depth=16,location=(0,0,4),rotation=(0,math.pi/2,0));cut=bpy.context.object
bpy.context.view_layer.objects.active=body;mod=body.modifiers.new('Open optical bore','BOOLEAN');mod.operation='DIFFERENCE';mod.solver='EXACT';mod.object=cut;bpy.ops.object.modifier_apply(modifier=mod.name);bpy.data.objects.remove(cut,do_unlink=True)
# Keep only external generated relief. The clean annular housing supplies the inner wall.
bm=bmesh.new();bm.from_mesh(body.data)
blocked=[f for f in bm.faces if math.hypot(f.calc_center_median().y,f.calc_center_median().z-4)<1.34 or any(math.hypot(v.co.y,v.co.z-4)<1.34 for v in f.verts)]
bmesh.ops.delete(bm,geom=blocked,context='FACES');bm.to_mesh(body.data);bm.free()
mod=body.modifiers.new('Exterior relief budget','DECIMATE');mod.ratio=.50;bpy.ops.object.modifier_apply(modifier=mod.name)
mod=body.modifiers.new('Closed exterior detail shell','SOLIDIFY');mod.thickness=.012;mod.offset=0;bpy.ops.object.modifier_apply(modifier=mod.name)
for f in body.data.polygons:f.use_smooth=True
bpy.data.objects.remove(normal_source,do_unlink=True)
def material(name,color,metal,rough):
    m=bpy.data.materials.new(name);m.use_nodes=True;n=m.node_tree.nodes;ln=m.node_tree.links;bs=n.get('Principled BSDF')
    bs.inputs['Base Color'].default_value=(*color,1);bs.inputs['Metallic'].default_value=metal;bs.inputs['Roughness'].default_value=rough
    tex=n.new('ShaderNodeTexNoise');tex.inputs['Scale'].default_value=210;tex.inputs['Detail'].default_value=2
    ramp=n.new('ShaderNodeValToRGB');ramp.color_ramp.elements[0].color=(*(c*.83 for c in color),1);ramp.color_ramp.elements[1].color=(*(c*1.13 for c in color),1);ln.new(tex.outputs['Fac'],ramp.inputs[0]);ln.new(ramp.outputs[0],bs.inputs['Base Color'])
    bump=n.new('ShaderNodeBump');bump.inputs['Strength'].default_value=.15;bump.inputs['Distance'].default_value=.001;ln.new(tex.outputs['Fac'],bump.inputs['Height']);ln.new(bump.outputs[0],bs.inputs['Normal'])
    return m
metal=material('Anodized_Graphite',(.042,.05,.06),.7,.5)
steel=material('Machined_Fasteners',(.15,.17,.19),.95,.29)
rubber=material('Rubber_Controls',(.012,.014,.018),0,.72)
body.data.materials.clear();body.data.materials.append(metal)
for p in body.data.polygons:p.material_index=0
def bevel(o,r=.055):
    bpy.context.view_layer.objects.active=o
    m=o.modifiers.new('Machined edge radii','BEVEL');m.width=r;m.segments=3;bpy.ops.object.modifier_apply(modifier=m.name)
    for p in o.data.polygons:p.use_smooth=True
    m=o.modifiers.new('Face weighted normals','WEIGHTED_NORMAL');m.keep_sharp=True;bpy.ops.object.modifier_apply(modifier=m.name)
def box(name,loc,dim,mat,r=.055):
    bpy.ops.mesh.primitive_cube_add(size=1,location=loc);o=bpy.context.object;o.name=name;o.dimensions=dim;bpy.ops.object.transform_apply(location=False,rotation=False,scale=True);o.data.materials.append(mat);bevel(o,r);return o
def cylinder(name,loc,r,depth,mat,axis='Y',verts=32):
    bpy.ops.mesh.primitive_cylinder_add(vertices=verts,radius=r,depth=depth,location=loc);o=bpy.context.object;o.name=name
    o.rotation_euler=(math.pi/2,0,0) if axis=='Y' else (0,math.pi/2,0)
    bpy.ops.object.transform_apply(location=False,rotation=True,scale=True);o.data.materials.append(mat);bevel(o,min(.02,r*.15,depth*.15));return o
# Clean annular housing follows the generated axial silhouette; no opaque lens caps.
profile=[(-6.48,1.55),(-4.25,1.55),(-3.9,1.86),(-3.55,1.94),(1.55,1.94),(1.95,1.66),(5.45,1.66),(5.50,1.82),(6.48,1.82)]
N=64;verts=[]
for x,r in profile:
 for i in range(N):
  t=i*math.tau/N
  if -3.55<=x<=1.55:r0=1.78/math.cos(t-round(t/(math.pi/4))*(math.pi/4))
  else:r0=r
  verts.append((x,r0*math.cos(t),4+r0*math.sin(t)))
for x in [profile[0][0],profile[-1][0]]:
 for i in range(N):verts.append((x,1.22*math.cos(i*math.tau/N),4+1.22*math.sin(i*math.tau/N)))
faces=[];L=len(profile)
for j in range(L-1):
 for i in range(N):k=(i+1)%N;faces.append((j*N+i,j*N+k,(j+1)*N+k,(j+1)*N+i))
for i in range(N):
 k=(i+1)%N;faces.extend([(L*N+i,(L+1)*N+i,(L+1)*N+k,L*N+k),(i,L*N+i,L*N+k,k),((L-1)*N+i,(L-1)*N+k,(L+1)*N+k,(L+1)*N+i)])
me=bpy.data.meshes.new('RetopologizedHousing');me.from_pydata(verts,[],faces);me.update();o=bpy.data.objects.new('Machined_Optical_Housing',me);bpy.context.collection.objects.link(o);o.data.materials.append(metal)
for f in me.polygons:f.use_smooth=True
bevel(o,.035)
box('Rail_Clamp_Base',(0,0,.45),(5.3,2.5,.65),metal,.08)
box('Prism_Pedestal',(0,0,1.40),(4.4,2.18,1.65),metal,.09)
bpy.ops.mesh.primitive_cylinder_add(vertices=32,radius=.65,depth=max(.10,maxz-.60-5.65),location=(topx,topy,(5.65+maxz-.60)/2));stem=bpy.context.object;stem.name='Turret_Stem';stem.data.materials.append(metal);bevel(stem,.03)
cylinder('Windage_Stem',(sidex,side_sign*(1.70+side_edge-.45)/2,sidez),.65,side_edge-.45-1.70,metal)
for y in [-1.03,1.03]:box('Clamp_Jaw',(0,y,.125),(4.9,.30,.25),steel,.025)
for x in [-1.85,1.85]:
 for y in [-1.30,1.30]:
  cylinder('Clamp_Fastener',(x,y,.46),.20,.14,steel)
  cylinder('Hex_Insert',(x,y+(-.076 if y<0 else .076),.46),.085,.012,rubber,verts=6)
opaque=[o for o in bpy.context.scene.objects if o.type=='MESH']
bpy.ops.object.select_all(action='DESELECT')
for o in opaque:o.select_set(True)
bpy.context.view_layer.objects.active=body;bpy.ops.object.join();body.name='SM_PrismScope2X_Body'
bpy.ops.object.transform_apply(location=True,rotation=True,scale=True)
assert not body.ray_cast(Vector((-8,0,4)),Vector((1,0,0)))[0], 'Opaque geometry blocks optical center'
bm=bmesh.new();bm.from_mesh(body.data);bmesh.ops.dissolve_degenerate(bm,edges=list(bm.edges),dist=.00002);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(body.data);bm.free()
if body.data.has_custom_normals:bpy.ops.mesh.customdata_custom_splitnormals_clear()
bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT');bpy.ops.uv.smart_project(angle_limit=math.radians(65),island_margin=.015);bpy.ops.object.mode_set(mode='OBJECT')
scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=16;scene.render.bake.margin=12
# Bake the procedural anodizing and hard/rubber material separation to a single UV atlas.
maps={}
for channel in ['BaseColor','Roughness','Metallic','Normal']:
    img=bpy.data.images.new('T_Scope2X_'+channel,2048,2048,alpha=False)
    if channel!='BaseColor':img.colorspace_settings.name='Non-Color'
    saved=[]
    for m in body.data.materials:
        n=m.node_tree.nodes;l=m.node_tree.links;bs=n.get('Principled BSDF');out=n.get('Material Output');target=n.new('ShaderNodeTexImage');target.image=img;n.active=target
        if channel!='Normal':
            socket=bs.inputs[{'BaseColor':'Base Color','Roughness':'Roughness','Metallic':'Metallic'}[channel]]
            em=n.new('ShaderNodeEmission')
            if socket.is_linked:l.new(socket.links[0].from_socket,em.inputs[0])
            else:
                val=socket.default_value;em.inputs[0].default_value=tuple(val) if channel=='BaseColor' else (val,val,val,1)
            l.new(em.outputs[0],out.inputs['Surface']);saved.append((m,em))
    bpy.ops.object.bake(type='NORMAL' if channel=='Normal' else 'EMIT')
    img.filepath_raw=str(P/(img.name+'.png'));img.file_format='PNG';img.save();maps[channel]=img
    for m,em in saved:
        m.node_tree.links.new(m.node_tree.nodes.get('Principled BSDF').outputs[0],m.node_tree.nodes.get('Material Output').inputs['Surface']);m.node_tree.nodes.remove(em)
atlas=bpy.data.materials.new('Scope2X_Body');atlas.use_nodes=True;bs=atlas.node_tree.nodes.get('Principled BSDF')
for channel,img in maps.items():
    n=atlas.node_tree.nodes.new('ShaderNodeTexImage');n.image=img
    if channel=='Normal':
        norm=atlas.node_tree.nodes.new('ShaderNodeNormalMap');atlas.node_tree.links.new(n.outputs[0],norm.inputs['Color']);atlas.node_tree.links.new(norm.outputs[0],bs.inputs['Normal'])
    else:atlas.node_tree.links.new(n.outputs[0],bs.inputs[{'BaseColor':'Base Color','Roughness':'Roughness','Metallic':'Metallic'}[channel]])
body.data.materials.clear();body.data.materials.append(atlas)
for f in body.data.polygons:f.material_index=0
glass=bpy.data.materials.new('Scope2X_Glass');glass.use_nodes=True;bs=glass.node_tree.nodes.get('Principled BSDF');bs.inputs['Base Color'].default_value=(.35,.62,.65,1);bs.inputs['Transmission Weight'].default_value=1;bs.inputs['Roughness'].default_value=.035;bs.inputs['IOR'].default_value=1.06
for x in [-6.12,6.10]:
 verts=[(x,1.225*math.cos(i*math.tau/128),4+1.225*math.sin(i*math.tau/128)) for i in range(128)]
 me=bpy.data.meshes.new('Lens');me.from_pydata(verts,[],[list(range(128))]);me.update();o=bpy.data.objects.new('Coated_Lens',me);bpy.context.collection.objects.link(o);o.data.materials.append(glass)
ret=bpy.data.materials.new('Scope2X_Reticle');ret.use_nodes=True;bs=ret.node_tree.nodes.get('Principled BSDF');bs.inputs['Base Color'].default_value=(1,.001,0,1);bs.inputs['Emission Color'].default_value=(1,.001,0,1);bs.inputs['Emission Strength'].default_value=6
# Game center dot and four separated fine crosshair arms, on the ocular plane.
cylinder('Center_Dot',(-6.15,0,4),.025,.004,ret,axis='X',verts=24)
for sign in [-1,1]:
 box('Horizontal_Stadia',(-6.15,sign*.24,4),(.004,.30,.009),ret,.001)
 box('Vertical_Stadia',(-6.15,0,4+sign*.24),(.004,.009,.30),ret,.001)
meshes=[o for o in bpy.context.scene.objects if o.type=='MESH']
bpy.ops.object.select_all(action='DESELECT')
for o in meshes:o.select_set(True)
bpy.context.view_layer.objects.active=body
bpy.ops.export_scene.fbx(filepath=str(P/'SM_PrismScope2X.fbx'),use_selection=True,object_types={'MESH'},global_scale=.01,axis_forward='-Y',axis_up='Z',bake_anim=False)
report={'source':'scope2x_textured_master_00001_.glb','source_triangles':96513,'aim_point_cm':[-6.15,0,4],'base_width_cm':2.5,'meshes':[]}
for o in meshes:
 o.data.calc_loop_triangles();bm=bmesh.new();bm.from_mesh(o.data);report['meshes'].append({'name':o.name,'triangles':len(o.data.loop_triangles),'boundary_edges':sum(e.is_boundary for e in bm.edges),'nonmanifold_edges':sum(not e.is_manifold for e in bm.edges),'degenerate_faces':sum(f.calc_area()<1e-10 for f in bm.faces)});bm.free()
report['triangles']=sum(m['triangles'] for m in report['meshes']);assert report['triangles']<24000,report['triangles'];(P/'mesh_report.json').write_text(json.dumps(report,indent=2))
scene.world=bpy.data.worlds.new('Studio');scene.world.use_nodes=True;scene.world.node_tree.nodes['Background'].inputs[0].default_value=(.15,.18,.22,1)
def aimat(o,p):o.rotation_euler=(Vector(p)-o.location).to_track_quat('-Z','Y').to_euler()
for pos,energy,size in [((-8,-10,14),1800,9),((4,8,12),2400,8),((10,-5,6),1400,6)]:
    bpy.ops.object.light_add(type='AREA',location=pos);l=bpy.context.object;l.data.energy=energy;l.data.shape='DISK';l.data.size=size;aimat(l,(0,0,4))
bpy.ops.object.camera_add(location=(-16,-18,11));cam=bpy.context.object;cam.data.type='ORTHO';cam.data.ortho_scale=17;scene.camera=cam
scene.render.resolution_x=1100;scene.render.resolution_y=950;scene.render.resolution_percentage=100;scene.cycles.samples=48;scene.cycles.use_denoising=True;scene.view_settings.view_transform='AgX'
for name,pos in [('beauty',(-16,-18,11)),('side',(0,-14,3)),('ads',(-20,0,4))]:
    cam.location=pos;aimat(cam,(0,0,3.7) if name!='ads' else (2,0,4));scene.render.filepath=str(P/(name+'.png'));bpy.ops.render.render(write_still=True)
cam.location=(-16,-18,11);aimat(cam,(0,0,3.7));bpy.ops.wm.save_as_mainfile(filepath=str(P/'PrismScope2X_Editable.blend'))
print('SCOPE2X_MODEL_PASS',json.dumps(report),flush=True)
