"""Preserve the three shared meshes; author one host adapter and three UI icons."""
import bpy, json, math
from pathlib import Path
from mathutils import Vector, Matrix
from mathutils.bvhtree import BVHTree
P=Path(__file__).parent
SRC=P.parent/'RuneSwordPommels20260920'
OUT=P/'Export'; OUT.mkdir(exist_ok=True)
ICONS=P/'Icons'; ICONS.mkdir(exist_ok=True)
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.open_mainfile(filepath=str(SRC/'RuneSword_Pommels_PBR.blend'))
with bpy.data.libraries.load(str(P.parent/'FrostSwordModules20260915/FrostSword_Modular_Editable.blend'),link=False) as (a,b):
    b.objects=['SM_FrostSword_Pommel_factory']
stock=b.objects[0]
scene=bpy.data.scenes.new('SharedPommel_FrostFit')
bpy.context.window.scene=scene
scene.collection.objects.link(stock)
stock.matrix_world=Matrix.Identity(4);stock.hide_set(True);stock.hide_render=True
shared=bpy.data.objects['SM_RunePommel_Meteor']
SCALE=.9
DEPTH=.006

def surface(obj):
    mesh=obj.data;mesh.calc_loop_triangles();tris=list(mesh.loop_triangles)
    bvh=BVHTree.FromPolygons([v.co for v in mesh.vertices],[t.vertices for t in tris],all_triangles=True)
    def sample(point):
        hit,normal,index,distance=bvh.find_nearest(point)
        tri=tris[index];a,b,c=[mesh.vertices[i].co for i in tri.vertices]
        ab=b-a;ac=c-a;ap=hit-a
        aa=ab.dot(ab);bb=ab.dot(ac);cc=ac.dot(ac);den=aa*cc-bb*bb
        if abs(den)<1e-18:return mesh.uv_layers[0].data[tri.loops[0]].uv.copy(),normal
        v=(cc*ap.dot(ab)-bb*ap.dot(ac))/den;w=(aa*ap.dot(ac)-bb*ap.dot(ab))/den
        uv=sum((mesh.uv_layers[0].data[i].uv*x for i,x in zip(tri.loops,[1-v-w,v,w])),Vector((0,0)))
        normal=sum((mesh.corner_normals[i].vector*x for i,x in zip(tri.loops,[1-v-w,v,w])),Vector()).normalized()
        return uv,normal
    return sample

stock_sample=surface(stock);shared_sample=surface(shared)
def rim(obj):
    # Only the outside faces meeting the mounting plane; exclude concealed cap centres.
    pts=set()
    for face in obj.data.polygons:
        coords=[obj.data.vertices[i].co for i in face.vertices]
        if not any(v.z<-.000001 for v in coords):continue
        for v in coords:
            if abs(v.z)<.000001:pts.add((round(v.x,8),round(v.y,8)))
    return sorted([Vector(p) for p in pts],key=lambda p:math.atan2(p.y,p.x))

top=rim(stock);bottom=rim(shared)
angles=sorted(set(round(math.atan2(p.y,p.x),9) for p in top+bottom))
def cross(a,b):return a.x*b.y-a.y*b.x
def radial(points,angle):
    ray=Vector((math.cos(angle),math.sin(angle)))
    hits=[]
    for a,b in zip(points,points[1:]+points[:1]):
        edge=b-a;den=cross(ray,edge)
        if abs(den)<1e-12:continue
        distance=cross(a,edge)/den;along=cross(a,ray)/den
        if distance>0 and -.000001<=along<=1.000001:hits.append(distance)
    if not hits:raise RuntimeError('Mount contour has no radial intersection')
    return ray*max(hits)

verts=[];end_normals={};steps=10
for ring in range(steps+1):
    t=ring/steps
    for angle in angles:
        a=radial(top,angle);b=radial(bottom,angle)*SCALE
        n0=stock_sample(Vector((a.x,a.y,-.00002)))[1]
        n1=shared_sample(Vector((b.x/SCALE,b.y/SCALE,-.00002)))[1]
        direction=Vector((math.cos(angle),math.sin(angle)))
        def tangent(n):
            radial_normal=Vector((n.x,n.y)).dot(direction)
            slope=n.z/radial_normal if abs(radial_normal)>.1 else 0
            return direction*(DEPTH*max(-1.5,min(1.5,slope)))
        xy=(2*t**3-3*t*t+1)*a+(t**3-2*t*t+t)*tangent(n0)+(-2*t**3+3*t*t)*b+(t**3-t*t)*tangent(n1)
        index=len(verts);verts.append((xy.x,xy.y,-DEPTH*t))
        if ring==0:end_normals[index]=n0
        if ring==steps:end_normals[index]=n1
n=len(angles);faces=[]
for j in range(steps):
    for i in range(n):
        a=j*n+i;b=j*n+(i+1)%n;c=(j+1)*n+(i+1)%n;d=(j+1)*n+i
        faces.extend([(a,c,b),(a,d,c)])
mesh=bpy.data.meshes.new('Frost_to_shared_pommel_interface')
mesh.from_pydata(verts,[],faces);mesh.update()
adapter=bpy.data.objects.new('SM_SwordPommel_FrostAdapter',mesh);scene.collection.objects.link(adapter)
uv0=mesh.uv_layers.new(name='SourceUV');uv1=mesh.uv_layers.new(name='BronzeUV')
colors=mesh.color_attributes.new(name='PommelFinish',type='FLOAT_COLOR',domain='CORNER')
mesh.color_attributes.active_color=colors
patch=json.loads((P.parent/'MeleeGuards20260915/finish_patch.json').read_text())
lo=patch['uv_min'];hi=patch['uv_max']
for face in mesh.polygons:
    face.use_smooth=True
    for loop in face.loop_indices:
        v=mesh.vertices[mesh.loops[loop].vertex_index].co
        t=-v.z/DEPTH;blend=max(0,min(1,(t-.1)/.45));blend=blend*blend*(3-2*blend)
        u=(math.atan2(v.y,v.x)+math.pi)/(2*math.pi)
        uv0.data[loop].uv=stock_sample(v)[0]
        uv1.data[loop].uv=(lo[0]+u*(hi[0]-lo[0]),lo[1]+t*(hi[1]-lo[1]))
        colors.data[loop].color=(blend,blend,blend,1)
    indices=list(face.loop_indices)
    if max(uv1.data[i].uv.x for i in indices)-min(uv1.data[i].uv.x for i in indices)>(hi[0]-lo[0])*.5:
        for i in indices:
            if uv1.data[i].uv.x<(lo[0]+hi[0])*.5:uv1.data[i].uv.x+=hi[0]-lo[0]
    if all(colors.data[i].color[0]>.999 for i in indices):
        for i in indices:uv0.data[i].uv=uv1.data[i].uv
mesh.update()
normals=[end_normals.get(loop.vertex_index,mesh.corner_normals[loop.index].vector.copy()) for loop in mesh.loops]
mesh.normals_split_custom_set(normals)

images={}
for node in stock.data.materials[0].node_tree.nodes:
    if node.type=='TEX_IMAGE' and node.image:
        label=node.image.name.lower()
        key='Normal' if 'normal' in label else 'Metallic' if 'metallic' in label else 'Roughness' if 'roughness' in label else 'BaseColor'
        images[key]=node.image
mat=bpy.data.materials.new('M_SharedPommel_FrostAdapter');mat.use_nodes=True
nt=mat.node_tree;nt.nodes.clear()
bs=nt.nodes.new('ShaderNodeBsdfPrincipled');output=nt.nodes.new('ShaderNodeOutputMaterial');nt.links.new(bs.outputs[0],output.inputs['Surface'])
c=nt.nodes.new('ShaderNodeVertexColor');c.layer_name='PommelFinish'
u0=nt.nodes.new('ShaderNodeUVMap');u0.uv_map='SourceUV'
u1=nt.nodes.new('ShaderNodeUVMap');u1.uv_map='BronzeUV'
for key,socket in [('BaseColor','Base Color'),('Metallic','Metallic'),('Roughness','Roughness')]:
    a=nt.nodes.new('ShaderNodeTexImage');a.image=images[key];nt.links.new(u0.outputs[0],a.inputs['Vector'])
    b=nt.nodes.new('ShaderNodeTexImage');b.image=images[key];nt.links.new(u1.outputs[0],b.inputs['Vector'])
    mix=nt.nodes.new('ShaderNodeMixRGB');nt.links.new(c.outputs[0],mix.inputs[0]);nt.links.new(a.outputs[0],mix.inputs[1]);nt.links.new(b.outputs[0],mix.inputs[2]);nt.links.new(mix.outputs[0],bs.inputs[socket])
mesh.materials.append(mat)
# Same shape assets as Rune Sword; the frost finish only affects the metallic PBR region.
tint=(.70,.37,.16)
rows=json.loads((SRC/'model_exports.json').read_text())
for row in rows:
    obj=bpy.data.objects[row['mesh']].copy();obj.name='Frost_'+row['mesh'];scene.collection.objects.link(obj)
    obj.data=obj.data.copy();obj.scale=(SCALE,)*3;obj.location=(0,0,-DEPTH);obj.hide_set(True);obj.hide_render=True
    for i,original in enumerate(obj.data.materials):
        if not original.name.endswith('_Opaque'):continue
        m=original.copy();m.name='FrostFinish_'+original.name;obj.data.materials[i]=m
        nt=m.node_tree;bs=next(n for n in nt.nodes if n.type=='BSDF_PRINCIPLED')
        source=bs.inputs['Base Color'].links[0].from_socket
        metallic=bs.inputs['Metallic'].links[0].from_socket
        bw=nt.nodes.new('ShaderNodeRGBToBW');nt.links.new(source,bw.inputs[0])
        multiply=nt.nodes.new('ShaderNodeMixRGB');multiply.blend_type='MULTIPLY';multiply.inputs[0].default_value=1;multiply.inputs[2].default_value=(*tint,1);nt.links.new(bw.outputs[0],multiply.inputs[1])
        mix=nt.nodes.new('ShaderNodeMixRGB');nt.links.new(metallic,mix.inputs[0]);nt.links.new(source,mix.inputs[1]);nt.links.new(multiply.outputs[0],mix.inputs[2]);nt.links.new(mix.outputs[0],bs.inputs['Base Color'])
        rough_source=bs.inputs['Roughness'].links[0].from_socket
        rough=nt.nodes.new('ShaderNodeMath');rough.operation='MULTIPLY';rough.inputs[1].default_value=1.1;nt.links.new(rough_source,rough.inputs[0]);nt.links.new(rough.outputs[0],bs.inputs['Roughness'])
    row['frost_object']=obj.name
for obj in scene.objects:obj.select_set(False)
adapter.select_set(True);bpy.context.view_layer.objects.active=adapter
bpy.ops.export_scene.fbx(filepath=str(OUT/(adapter.name+'.fbx')),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',bake_anim=False,mesh_smooth_type='FACE',use_tspace=False)
bpy.ops.export_scene.gltf(filepath=str(OUT/(adapter.name+'.glb')),export_format='GLB',use_selection=True,export_apply=True,export_normals=True)

# Production icons, no acceptance renders.
scene.render.engine='CYCLES';scene.cycles.samples=48;scene.cycles.use_denoising=True
scene.render.threads_mode='FIXED';scene.render.threads=8
scene.render.resolution_x=scene.render.resolution_y=1024;scene.render.resolution_percentage=100
scene.render.film_transparent=True;scene.render.image_settings.file_format='PNG';scene.render.image_settings.color_mode='RGBA'
scene.view_settings.view_transform='AgX'
scene.world=bpy.data.worlds.new('SharedPommel_Studio');scene.world.use_nodes=True;nt=scene.world.node_tree;nt.nodes.clear()
background=nt.nodes.new('ShaderNodeBackground');background.inputs[0].default_value=(.28,.28,.28,1);background.inputs[1].default_value=.45
output=nt.nodes.new('ShaderNodeOutputWorld');nt.links.new(background.outputs[0],output.inputs[0])
data=bpy.data.cameras.new('FrostPommel_IconCamera');camera=bpy.data.objects.new(data.name,data);scene.collection.objects.link(camera);scene.camera=camera;data.type='ORTHO';data.clip_start=.001
lights=[]
for name,offset,power,size in [('Key',(-2,-3,3),850,2.4),('Fill',(2.5,-1.5,.7),550,2),('Rim',(.5,2.5,2),1100,1.8)]:
    d=bpy.data.lights.new(name,'AREA');o=bpy.data.objects.new(name,d);scene.collection.objects.link(o);lights.append((o,Vector(offset),power,size))
ids={'meteor':'ballast_hardened','jade_core':'ballast_rune','swift':'ballast_magic_orb'}
for row in rows:
    model=bpy.data.objects[row['frost_object']];model.hide_set(False);model.hide_render=False;bpy.context.view_layer.update()
    points=[o.matrix_world@Vector(p) for o in [model,adapter] for p in o.bound_box]
    low=Vector(tuple(min(p[i] for p in points) for i in range(3)));high=Vector(tuple(max(p[i] for p in points) for i in range(3)))
    center=(low+high)/2;span=max(high.x-low.x,high.z-low.z)
    camera.location=center+Vector((0,-4*span,0));camera.rotation_euler=(center-camera.location).to_track_quat('-Z','Y').to_euler();data.ortho_scale=span/.83
    for o,offset,power,size in lights:
        o.location=center+offset*span;o.rotation_euler=(center-o.location).to_track_quat('-Z','Y').to_euler();o.data.energy=power*span*span;o.data.size=size*span
    scene.render.filepath=str(ICONS/('ue_frost_crystal_sword_pommel_'+ids[row['id']]+'.png'))
    bpy.ops.render.render(write_still=True,scene=scene.name)
    model.hide_set(True);model.hide_render=True
    print('SHARED_POMMEL_FROST_ICON',row['id'])
last=bpy.data.objects[rows[-1]['frost_object']];last.hide_set(False);last.hide_render=False
bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(P/'SharedPommels_FrostFit.blend'))
(P/'frost_fit.json').write_text(json.dumps({'scale':SCALE,'adapter_length_cm':DEPTH*100,'stock_mount_cm':[0,0,-22.7],
    'pommel_mount_cm':[0,0,-22.7-DEPTH*100],'metal_tint':tint,'metal_desaturation':1,'roughness_scale':1.1,
    'source_meshes_unchanged':True,'adapter':adapter.name,'adapter_triangles':len(faces),
    'icon_axis':'+Z toward blade, front -Y','icon_resolution':[1024,1024]},indent=2),encoding='utf-8')
