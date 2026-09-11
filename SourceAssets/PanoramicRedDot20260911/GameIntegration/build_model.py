import bpy, bmesh, math, json
from pathlib import Path
from mathutils import Vector, Matrix
P=Path(__file__).parent;P.mkdir(exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(P.parent/'Reroll03/reroll03_textured_master_00001_.glb'))
body=next(o for o in bpy.context.scene.objects if o.type=='MESH')
bpy.context.view_layer.objects.active=body;body.select_set(True)
bpy.ops.object.transform_apply(location=True,rotation=True,scale=True)
lo=Vector([min(v.co[a] for v in body.data.vertices) for a in range(3)])
hi=Vector([max(v.co[a] for v in body.data.vertices) for a in range(3)])
for v in body.data.vertices:
    p=(v.co-Vector(((lo.x+hi.x)/2,(lo.y+hi.y)/2,lo.z)))*6/(hi.x-lo.x)
    v.co=Vector((-p.x,-p.y,p.z+.25))
# Retain the generated frame; remove the distorted lower tray and rear controls.
bm=bmesh.new();bm.from_mesh(body.data)
bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=.0002)
bmesh.ops.bisect_plane(bm,geom=list(bm.verts)+list(bm.edges)+list(bm.faces),dist=.00001,plane_co=(0,0,1.75),plane_no=(0,0,1),clear_inner=True,clear_outer=False)
remaining=set(bm.verts);islands=[]
while remaining:
    seed=remaining.pop();part={seed};stack=[seed]
    while stack:
        for e in stack.pop().link_edges:
            for v in e.verts:
                if v in remaining:remaining.remove(v);part.add(v);stack.append(v)
    islands.append(part)
keep=max(islands,key=len)
bmesh.ops.delete(bm,geom=[v for v in bm.verts if v not in keep],context='VERTS')
bmesh.ops.holes_fill(bm,edges=[e for e in bm.edges if e.is_boundary],sides=0)
bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(body.data);bm.free()
body.name='5080_Frame_Refined'
mod=body.modifiers.new('Reduce while retaining silhouette','DECIMATE');mod.ratio=min(1,14500/max(1,len(body.data.polygons)));bpy.ops.object.modifier_apply(modifier=mod.name)
mod=body.modifiers.new('Remove generated ripples','SMOOTH');mod.factor=.6;mod.iterations=30;bpy.ops.object.modifier_apply(modifier=mod.name)
for p in body.data.polygons:p.use_smooth=True
def material(name,color,metal,rough):
    m=bpy.data.materials.new(name);m.use_nodes=True;n=m.node_tree.nodes;ln=m.node_tree.links;bs=n.get('Principled BSDF')
    bs.inputs['Base Color'].default_value=(*color,1);bs.inputs['Metallic'].default_value=metal;bs.inputs['Roughness'].default_value=rough
    tex=n.new('ShaderNodeTexNoise');tex.inputs['Scale'].default_value=210;tex.inputs['Detail'].default_value=2
    ramp=n.new('ShaderNodeValToRGB');ramp.color_ramp.elements[0].color=(*(c*.83 for c in color),1);ramp.color_ramp.elements[1].color=(*(c*1.13 for c in color),1);ln.new(tex.outputs['Fac'],ramp.inputs[0]);ln.new(ramp.outputs[0],bs.inputs['Base Color'])
    bump=n.new('ShaderNodeBump');bump.inputs['Strength'].default_value=.15;bump.inputs['Distance'].default_value=.001;ln.new(tex.outputs['Fac'],bump.inputs['Height']);ln.new(bump.outputs[0],bs.inputs['Normal'])
    return m
metal=material('Anodized_Graphite',(.042,.05,.06),.8,.36)
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
box('Mounting_Base',(0,0,.69),(5.9,2.50,.88),metal,.10)
box('Rear_Emitter_Housing',(-2.05,0,1.25),(1.85,2.50,.7),metal,.12)
# Narrow rail foot expands only immediately below the unchanged wide frame.
v=[(x,y,z) for z,w in [(1.0,2.40),(1.90,5.25)] for x,y in [(1.40,-w/2),(2.86,-w/2),(2.86,w/2),(1.40,w/2)]]
me=bpy.data.meshes.new('FlaredBridge');me.from_pydata(v,[],[(3,2,1,0),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)]);me.update();o=bpy.data.objects.new('Front_Frame_Support',me);bpy.context.collection.objects.link(o);o.data.materials.append(metal);bevel(o,.075)
for y in [-1.02,1.02]:box('Tray_Rim',(.20,y,1.28),(2.70,.38,.62),metal,.06)
for y in [-1.03,1.03]:box('Rail_Clamp_Jaw',(0,y,.15),(4.7,.30,.30),steel,.03)
for x in [-1.3,-.45]:box('Brightness_Button',(x,-1.32,.95),(.64,.21,.52),rubber,.075)
for x,vertical in [(-1.3,False),(-.45,True)]:
    box('Button_Minus',(x,-1.435,.95),(.25,.014,.035),steel,.01)
    if vertical:box('Button_Plus',(x,-1.435,.95),(.035,.014,.25),steel,.01)
def cylinder(name,loc,r,depth,mat,axis='Y',verts=32):
    bpy.ops.mesh.primitive_cylinder_add(vertices=verts,radius=r,depth=depth,location=loc);o=bpy.context.object;o.name=name
    o.rotation_euler=(math.pi/2,0,0) if axis=='Y' else (0,math.pi/2,0)
    bpy.ops.object.transform_apply(location=False,rotation=True,scale=True);o.data.materials.append(mat);bevel(o,min(.02,r*.15,depth*.15));return o
for y in [-1.30,1.30]:
    for x in [-2.1,2.05]:
        cylinder('Torx_Fastener',(x,y,.64),.19,.12,steel)
        # Recess represented by a dark hexagonal insert with a clear machined rim.
        cylinder('Hex_Recess',(x,y+(-.069 if y<0 else .069),.64),.087,.01,rubber,verts=6)
cylinder('Side_Adjustment_Cap',(.85,1.32,.95),.34,.14,steel)
box('Cap_Slot',(.85,1.403,.95),(.39,.014,.055),rubber,.015)
# A sealed small emitter aperture on the inner rear housing.
box('Emitter_Recess',(-1.09,0,1.32),(.02,.35,.16),rubber,.035)
opaque=[o for o in bpy.context.scene.objects if o.type=='MESH']
bpy.ops.object.select_all(action='DESELECT')
for o in opaque:o.select_set(True)
bpy.context.view_layer.objects.active=body;bpy.ops.object.join();body.name='SM_PanoramicRedDot_Body'
bpy.ops.object.transform_apply(location=True,rotation=True,scale=True)
bm=bmesh.new();bm.from_mesh(body.data);bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=.0001);bmesh.ops.dissolve_degenerate(bm,edges=list(bm.edges),dist=.00002);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(body.data);bm.free()
bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT');bpy.ops.uv.smart_project(angle_limit=math.radians(65),island_margin=.015);bpy.ops.object.mode_set(mode='OBJECT')
scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=16;scene.render.bake.margin=12
# Bake the procedural anodizing and hard/rubber material separation to a single UV atlas.
maps={}
for channel in ['BaseColor','Roughness','Metallic','Normal']:
    img=bpy.data.images.new('T_Panoramic_'+channel,2048,2048,alpha=False)
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
atlas=bpy.data.materials.new('Panoramic_Body');atlas.use_nodes=True;bs=atlas.node_tree.nodes.get('Principled BSDF')
for channel,img in maps.items():
    n=atlas.node_tree.nodes.new('ShaderNodeTexImage');n.image=img
    if channel=='Normal':
        norm=atlas.node_tree.nodes.new('ShaderNodeNormalMap');atlas.node_tree.links.new(n.outputs[0],norm.inputs['Color']);atlas.node_tree.links.new(norm.outputs[0],bs.inputs['Normal'])
    else:atlas.node_tree.links.new(n.outputs[0],bs.inputs[{'BaseColor':'Base Color','Roughness':'Roughness','Metallic':'Metallic'}[channel]])
body.data.materials.clear();body.data.materials.append(atlas)
for f in body.data.polygons:f.material_index=0
# Optical aperture: inset rounded glass, its center is the authoritative ADS point.
aim=(2.15,0,3.25)
glass=bpy.data.materials.new('Panoramic_Glass');glass.use_nodes=True;bs=glass.node_tree.nodes.get('Principled BSDF');bs.inputs['Base Color'].default_value=(.40,.64,.69,1);bs.inputs['Transmission Weight'].default_value=.98;bs.inputs['Roughness'].default_value=.035;bs.inputs['IOR'].default_value=1.08
from mathutils.bvhtree import BVHTree
bm=bmesh.new();bm.from_mesh(body.data);tree=BVHTree.FromBMesh(bm)
verts=[]
for i in range(128):
    theta=i*math.tau/128;direction=Vector((0,math.cos(theta),math.sin(theta)))
    hit,normal,index,distance=tree.ray_cast(Vector(aim),direction,8)
    assert hit is not None,('lens aperture ray missed',i)
    verts.append(Vector(aim)+direction*(distance+.025))
bm.free()
# The lens follows the actual generated inner frame cross-section with an inset overlap.
me=bpy.data.meshes.new('Lens');me.from_pydata(verts,[],[list(range(len(verts)))]);me.update();lens=bpy.data.objects.new('Optical_Lens',me);bpy.context.collection.objects.link(lens);lens.data.materials.append(glass)
ret=bpy.data.materials.new('Panoramic_Reticle');ret.use_nodes=True;bs=ret.node_tree.nodes.get('Principled BSDF');bs.inputs['Base Color'].default_value=(1,.002,0,1);bs.inputs['Emission Color'].default_value=(1,.002,0,1);bs.inputs['Emission Strength'].default_value=8
cylinder('Red_Dot',(aim[0]-.025,0,aim[2]),.045,.004,ret,axis='X',verts=24)
meshes=[o for o in bpy.context.scene.objects if o.type=='MESH']
bpy.ops.object.select_all(action='DESELECT')
for o in meshes:o.select_set(True)
bpy.context.view_layer.objects.active=body
# Source coordinates in centimetres; FBX exported in metres and imported once to UE cm.
bpy.ops.export_scene.fbx(filepath=str(P/'SM_PanoramicRedDot.fbx'),use_selection=True,object_types={'MESH'},global_scale=.01,axis_forward='-Y',axis_up='Z',bake_anim=False)
report={'source':'Reroll03/reroll03_textured_master_00001_.glb','source_triangles':99829,'aim_point_cm':list(aim),'meshes':[],'textures':{c:i.filepath_raw for c,i in maps.items()},'revision':'generated upper frame retained; distorted base replaced; machined controls; UV baked anodizing'}
for o in meshes:
    o.data.calc_loop_triangles();bm=bmesh.new();bm.from_mesh(o.data)
    report['meshes'].append({'name':o.name,'triangles':len(o.data.loop_triangles),'boundary_edges':sum(e.is_boundary for e in bm.edges),'nonmanifold_edges':sum(not e.is_manifold for e in bm.edges),'degenerate_faces':sum(f.calc_area()<1e-10 for f in bm.faces)});bm.free()
report['triangles']=sum(m['triangles'] for m in report['meshes']);(P/'mesh_report.json').write_text(json.dumps(report,indent=2))
scene.world=bpy.data.worlds.new('Studio');scene.world.use_nodes=True;scene.world.node_tree.nodes['Background'].inputs[0].default_value=(.15,.18,.22,1)
def aimat(o,p):o.rotation_euler=(Vector(p)-o.location).to_track_quat('-Z','Y').to_euler()
for pos,energy,size in [((-8,-10,14),1800,9),((4,8,12),2400,8),((10,-5,6),1400,6)]:
    bpy.ops.object.light_add(type='AREA',location=pos);l=bpy.context.object;l.data.energy=energy;l.data.shape='DISK';l.data.size=size;aimat(l,(0,0,2))
bpy.ops.object.camera_add(location=(-10,-10,8));cam=bpy.context.object;cam.data.type='ORTHO';cam.data.ortho_scale=9;scene.camera=cam
scene.render.resolution_x=1100;scene.render.resolution_y=950;scene.render.resolution_percentage=100;scene.cycles.samples=48;scene.cycles.use_denoising=True;scene.view_settings.view_transform='AgX'
for name,pos in [('beauty',(-10,-10,8)),('side',(0,-14,3)),('ads',(-16,0,3.25))]:
    cam.location=pos;aimat(cam,(0,0,2.4) if name!='ads' else (2,0,3.25));scene.render.filepath=str(P/(name+'.png'));bpy.ops.render.render(write_still=True)
cam.location=(-10,-10,8);aimat(cam,(0,0,2.4));bpy.ops.wm.save_as_mainfile(filepath=str(P/'PanoramicRedDot_Editable.blend'))
print('PANORAMIC_MODEL_PASS',json.dumps(report),flush=True)
