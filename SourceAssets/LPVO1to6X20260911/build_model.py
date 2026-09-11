import bpy,bmesh,math,json
from pathlib import Path
from mathutils import Vector
P=Path(__file__).parent
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(P/'lpvo_textured_master_00001_.glb'))
body=next(o for o in bpy.context.scene.objects if o.type=='MESH');bpy.context.view_layer.objects.active=body;body.select_set(True);bpy.ops.object.transform_apply(location=True,rotation=True,scale=True)
body.data.calc_loop_triangles();source_triangles=len(body.data.loop_triangles);body.data.clear_geometry()
side_sign=-1
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
    m=o.modifiers.new('Machined edge radii','BEVEL');m.width=r;m.segments=2;bpy.ops.object.modifier_apply(modifier=m.name)
    for p in o.data.polygons:p.use_smooth=True
    m=o.modifiers.new('Face weighted normals','WEIGHTED_NORMAL');m.keep_sharp=True;bpy.ops.object.modifier_apply(modifier=m.name)
def box(name,loc,dim,mat,r=.055):
    bpy.ops.mesh.primitive_cube_add(size=1,location=loc);o=bpy.context.object;o.name=name;o.dimensions=dim;bpy.ops.object.transform_apply(location=False,rotation=False,scale=True);o.data.materials.append(mat);bevel(o,r);return o
def cylinder(name,loc,r,depth,mat,axis='Y',verts=32):
    bpy.ops.mesh.primitive_cylinder_add(vertices=verts,radius=r,depth=depth,location=loc);o=bpy.context.object;o.name=name
    o.rotation_euler=(math.pi/2,0,0) if axis=='Y' else (0,math.pi/2,0)
    bpy.ops.object.transform_apply(location=False,rotation=True,scale=True);o.data.materials.append(mat);bevel(o,min(.02,r*.15,depth*.15));return o
def tube(name,profile,inner,mat,flutes=0):
 n=160 if flutes else 96;vv=[];ff=[]
 for x,r,d in profile:
  for i in range(n):
   a=i*math.tau/n;rr=r+(d*(.5+.5*math.cos(flutes*a)) if flutes else 0);vv.append((x,rr*math.cos(a),4+rr*math.sin(a)))
 for x,r in [(profile[0][0],inner[0]),(profile[-1][0],inner[1])]:
  for i in range(n):a=i*math.tau/n;vv.append((x,r*math.cos(a),4+r*math.sin(a)))
 L=len(profile)
 for j in range(L-1):
  for i in range(n):k=(i+1)%n;ff.append((j*n+i,j*n+k,(j+1)*n+k,(j+1)*n+i))
 for i in range(n):
  k=(i+1)%n;ff.extend([(L*n+i,(L+1)*n+i,(L+1)*n+k,L*n+k),(i,L*n+i,L*n+k,k),((L-1)*n+i,(L-1)*n+k,(L+1)*n+k,(L+1)*n+i)])
 me=bpy.data.meshes.new(name);me.from_pydata(vv,[],ff);me.update();o=bpy.data.objects.new(name,me);bpy.context.collection.objects.link(o);o.data.materials.append(mat)
 o.data.materials.append(rubber)
 for f in me.polygons:
  f.use_smooth=True
  if f.index>=(L-1)*n and (f.index-(L-1)*n)%3==0:f.material_index=1
 return o
# 250 mm design derived from the generated reference, with concentric machined optical surfaces.
pr=[(-12.5,1.95,0),(-12.43,2,0),(-8.3,2,0),(-8.15,1.89,0),(-6.3,1.89,0),(-5.5,1.5,0),(-1.8,1.5,0),(-1.5,1.70,0),(1.5,1.70,0),(1.8,1.5,0),(8.7,1.5,0),(10.4,1.65,0),(12.43,1.65,0),(12.5,1.60,0)]
tube('OpticalHousing',pr,(1.78,1.38),metal)
tube('DiopterGrip',[(-12.48,2.005,0),(-12.42,2.035,.018),(-11.58,2.035,.018),(-11.52,2.005,0)],(1.99,1.99),metal,40)
ring=tube('MagnificationRing',[(-7.9,1.895,0),(-7.84,1.945,.026),(-6.40,1.945,.026),(-6.34,1.895,0)],(1.89,1.89),metal,40)
vg=ring.vertex_groups.new(name='LPVORing');vg.add(list(range(len(ring.data.vertices))),1,'REPLACE')
# Radial throw lever attached to the moving ring, initially upright.
bpy.ops.mesh.primitive_cylinder_add(vertices=24,radius=.16,depth=1.1,location=(-7.1,0,6.45));lever=bpy.context.object;lever.name='ThrowLever';lever.data.materials.append(steel);bevel(lever,.06);vg=lever.vertex_groups.new(name='LPVORing');vg.add(list(range(len(lever.data.vertices))),1,'REPLACE')
# Two split rings around the 30 mm tube, bridged cantilever rail mount.
for x in [-3.9,4.8]:
 tube('MountRing',[(x-.58,1.62,0),(x-.52,1.70,0),(x+.52,1.70,0),(x+.58,1.62,0)],(1.505,1.505),metal)
 box('RingPillar',(x,0,1.76),(1.05,1.95,1.9),metal,.09)
 for y in [-1.65,1.65]:
  box('RingLug',(x,y,3.85),(1.12,.40,.66),metal,.045)
  cylinder('RingBolt',(x,y*1.14,3.86),.15,.10,steel)
box('CantileverBridge',(.2,0,.95),(10.1,2.18,.6),metal,.08)
box('RailBase',(-1.4,0,.45),(7,2.5,.65),metal,.06)
for y in [-1.03,1.03]:box('ClampJaw',(-1.4,y,.125),(6.7,.30,.25),steel,.025)
for x in [-3.8,1]:
 for y in [-1.30,1.30]:cylinder('ClampBolt',(x,y,.46),.20,.14,steel);cylinder('HexInsert',(x,y+(-.076 if y<0 else .076),.46),.085,.012,rubber,verts=6)
bpy.ops.mesh.primitive_cylinder_add(vertices=64,radius=.67,depth=.22,location=(0,0,5.73));o=bpy.context.object;o.data.materials.append(metal);bevel(o,.025)
cylinder('WindageSeat',(0,-1.72,4),.67,.22,metal)
def control(name,origin,axis,radius=.85):
 # Turned cap: lower seat, chamfer, 40 shallow flutes, upper chamfer and flat face.
 count=160;pr=[(0,.89,0),(.045,.98,0),(.10,1,.023),(.38,1,.023),(.435,.98,0),(.46,.89,0)]
 vv=[];ff=[]
 def point(x,y,z):return (origin[0]+x,origin[1]+y,origin[2]+z) if axis=='Z' else (origin[0]+x,origin[1]+side_sign*z,origin[2]+y)
 for z,r,d in pr:
  for i in range(count):
   a=i*math.tau/count;rr=radius*r+d*(.5+.5*math.cos(40*a));vv.append(point(rr*math.cos(a),rr*math.sin(a),z))
 for j in range(len(pr)-1):
  for i in range(count):k=(i+1)%count;ff.append((j*count+i,j*count+k,(j+1)*count+k,(j+1)*count+i))
 ff.append(tuple(reversed(range(count))));ff.append(tuple((len(pr)-1)*count+i for i in range(count)))
 me=bpy.data.meshes.new(name);me.from_pydata(vv,[],ff);me.update();o=bpy.data.objects.new(name,me);bpy.context.collection.objects.link(o);o.data.materials.append(metal)
 for f in me.polygons:f.use_smooth=len(f.vertices)==4
 # Fine radial index marks lie on the flat cap, with one longer reference mark.
 for i in range(12):
  a=i*math.tau/12;rr=radius*.70;length=.11 if i%3==0 else .065
  pos=point(rr*math.cos(a),rr*math.sin(a),.462)
  q=box(name+'_Index',pos,(length,.012,.003) if axis=='Z' else (length,.003,.012),steel,.001)
  if axis=='Z':q.rotation_euler.z=a
  else:q.rotation_euler.y=-a
control('Elevation',(0,0,5.83),'Z',.86)
control('Windage',(0,-1.83,4),'Y',.78)
bpy.ops.wm.save_as_mainfile(filepath=str(P/'LPVO_SeparateParts.blend'))
opaque=[o for o in bpy.context.scene.objects if o.type=='MESH']
bpy.ops.object.select_all(action='DESELECT')
for o in opaque:o.select_set(True)
bpy.context.view_layer.objects.active=body;bpy.ops.object.join();body.name='SM_LPVO1to6X_Body'
bpy.ops.object.transform_apply(location=True,rotation=True,scale=True)
assert not body.ray_cast(Vector((-14,0,4)),Vector((1,0,0)))[0], 'Opaque geometry blocks optical center'
bm=bmesh.new();bm.from_mesh(body.data);bmesh.ops.dissolve_degenerate(bm,edges=list(bm.edges),dist=.00002);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(body.data);bm.free()
if body.data.has_custom_normals:bpy.ops.mesh.customdata_custom_splitnormals_clear()
bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT');bpy.ops.uv.smart_project(angle_limit=math.radians(65),island_margin=.015);bpy.ops.object.mode_set(mode='OBJECT')
scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=16;scene.render.bake.margin=12
# Bake the procedural anodizing and hard/rubber material separation to a single UV atlas.
maps={}
for channel in ['BaseColor','Roughness','Metallic','Normal']:
    img=bpy.data.images.new('T_LPVO_'+channel,2048,2048,alpha=False)
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
atlas=bpy.data.materials.new('LPVO_Body');atlas.use_nodes=True;bs=atlas.node_tree.nodes.get('Principled BSDF')
for channel,img in maps.items():
    n=atlas.node_tree.nodes.new('ShaderNodeTexImage');n.image=img
    if channel=='Normal':
        norm=atlas.node_tree.nodes.new('ShaderNodeNormalMap');atlas.node_tree.links.new(n.outputs[0],norm.inputs['Color']);atlas.node_tree.links.new(norm.outputs[0],bs.inputs['Normal'])
    else:atlas.node_tree.links.new(n.outputs[0],bs.inputs[{'BaseColor':'Base Color','Roughness':'Roughness','Metallic':'Metallic'}[channel]])
body.data.materials.clear();body.data.materials.append(atlas)
for f in body.data.polygons:f.material_index=0
glass=bpy.data.materials.new('LPVO_Glass');glass.use_nodes=True;bs=glass.node_tree.nodes.get('Principled BSDF');bs.inputs['Base Color'].default_value=(.35,.62,.65,1);bs.inputs['Transmission Weight'].default_value=1;bs.inputs['Roughness'].default_value=.035;bs.inputs['IOR'].default_value=1.06
for x,lensr in [(-12.12,1.79),(12.10,1.39)]:
 verts=[(x,lensr*math.cos(i*math.tau/128),4+lensr*math.sin(i*math.tau/128)) for i in range(128)]
 me=bpy.data.meshes.new('Lens');me.from_pydata(verts,[],[list(range(128))]);me.update();o=bpy.data.objects.new('Coated_Lens',me);bpy.context.collection.objects.link(o);o.data.materials.append(glass)
ret=bpy.data.materials.new('LPVO_Reticle');ret.use_nodes=True;bs=ret.node_tree.nodes.get('Principled BSDF');bs.inputs['Base Color'].default_value=(1,.001,0,1);bs.inputs['Emission Color'].default_value=(1,.001,0,1);bs.inputs['Emission Strength'].default_value=6
# Game center dot and four separated fine crosshair arms, on the ocular plane.
cylinder('Center_Dot',(-12.15,0,4),.025,.004,ret,axis='X',verts=24)
for sign in [-1,1]:
 box('Horizontal_Stadia',(-12.15,sign*.24,4),(.004,.30,.009),ret,.001)
 box('Vertical_Stadia',(-12.15,0,4+sign*.24),(.004,.009,.30),ret,.001)
# Split baked moving ring from the body, retaining atlas UVs and its local pivot.
g=body.vertex_groups.get('LPVORing');assert g
ids={v.index for v in body.data.vertices if any(a.group==g.index and a.weight>.5 for a in v.groups)}
ring=body.copy();ring.data=body.data.copy();ring.name='SM_LPVORing';bpy.context.collection.objects.link(ring)
for ob,remove in [(ring,False),(body,True)]:
 bm=bmesh.new();bm.from_mesh(ob.data);bm.verts.ensure_lookup_table();bmesh.ops.delete(bm,geom=[v for v in bm.verts if (v.index in ids)==remove],context='VERTS');bm.to_mesh(ob.data);bm.free()
for v in ring.data.vertices:v.co-=Vector((-7.1,0,4))
ring.location=(-7.1,0,4)
meshes=[o for o in bpy.context.scene.objects if o.type=='MESH']
bpy.ops.object.select_all(action='DESELECT')
for o in meshes:o.select_set(o!=ring)
bpy.context.view_layer.objects.active=body
bpy.ops.export_scene.fbx(filepath=str(P/'SM_LPVO1to6X.fbx'),use_selection=True,object_types={'MESH'},global_scale=.01,axis_forward='-Y',axis_up='Z',bake_anim=False)
bpy.ops.object.select_all(action='DESELECT');ring.select_set(True);bpy.context.view_layer.objects.active=ring;ring.location=(0,0,0);bpy.ops.export_scene.fbx(filepath=str(P/'SM_LPVORing.fbx'),use_selection=True,object_types={'MESH'},global_scale=.01,axis_forward='-Y',axis_up='Z',bake_anim=False);ring.location=(-7.1,0,4)
report={'source':'lpvo_textured_master_00001_.glb','source_triangles':source_triangles,'aim_point_cm':[-12.15,0,4],'base_width_cm':2.5,'meshes':[]}
for o in meshes:
 o.data.calc_loop_triangles();bm=bmesh.new();bm.from_mesh(o.data);report['meshes'].append({'name':o.name,'triangles':len(o.data.loop_triangles),'boundary_edges':sum(e.is_boundary for e in bm.edges),'nonmanifold_edges':sum(not e.is_manifold for e in bm.edges),'degenerate_faces':sum(f.calc_area()<1e-10 for f in bm.faces)});bm.free()
report['triangles']=sum(m['triangles'] for m in report['meshes']);assert report['triangles']<24000,report['triangles'];(P/'mesh_report.json').write_text(json.dumps(report,indent=2))
scene.world=bpy.data.worlds.new('Studio');scene.world.use_nodes=True;scene.world.node_tree.nodes['Background'].inputs[0].default_value=(.15,.18,.22,1)
def aimat(o,p):o.rotation_euler=(Vector(p)-o.location).to_track_quat('-Z','Y').to_euler()
for pos,energy,size in [((-8,-10,14),1800,9),((4,8,12),2400,8),((10,-5,6),1400,6)]:
    bpy.ops.object.light_add(type='AREA',location=pos);l=bpy.context.object;l.data.energy=energy;l.data.shape='DISK';l.data.size=size;aimat(l,(0,0,4))
bpy.ops.object.camera_add(location=(-16,-18,11));cam=bpy.context.object;cam.data.type='ORTHO';cam.data.ortho_scale=30;scene.camera=cam
scene.render.resolution_x=1100;scene.render.resolution_y=950;scene.render.resolution_percentage=100;scene.cycles.samples=48;scene.cycles.use_denoising=True;scene.view_settings.view_transform='AgX'
for name,pos in [('beauty',(-24,-28,15)),('side',(0,-14,3)),('ads',(-20,0,4))]:
    cam.location=pos;aimat(cam,(0,0,3.7) if name!='ads' else (2,0,4));scene.render.filepath=str(P/(name+'.png'));bpy.ops.render.render(write_still=True)
cam.location=(-16,-18,11);aimat(cam,(0,0,3.7));bpy.ops.wm.save_as_mainfile(filepath=str(P/'LPVO_Editable.blend'))
print('SCOPE2X_MODEL_PASS',json.dumps(report),flush=True)
