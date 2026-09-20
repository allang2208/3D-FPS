"""Keep all original pommel bodies; author the Rune-to-Frost interface and UI assets."""
import bpy, json, math, sys
from pathlib import Path
from mathutils import Vector, Matrix
from mathutils.bvhtree import BVHTree
P=Path(__file__).parent;SRC=P.parent
OUT=P/'Export';OUT.mkdir(exist_ok=True)
ICONS=P/'Icons';ICONS.mkdir(exist_ok=True)
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.open_mainfile(filepath=str(SRC/'RuneSwordPommels20260920/RuneSword_Pommels_PBR.blend'))
scene=bpy.data.scenes.new('SixSharedPommels_RuneFit');bpy.context.window.scene=scene
top=bpy.data.objects['SM_RunePommel_Meteor']
with bpy.data.libraries.load(str(SRC/'FrostSwordModules20260915/FrostSword_Modular_Editable.blend'),link=False) as (a,b):
    b.objects=['SM_FrostSword_Pommel_factory']
bottom=b.objects[0];bottom.matrix_world=Matrix.Identity(4)
DEPTH=.006;SCALE=1.;SILVER=(2.15,2.3,2.5)
def sampler(obj):
    m=obj.data;m.calc_loop_triangles();tris=list(m.loop_triangles)
    tree=BVHTree.FromPolygons([v.co for v in m.vertices],[t.vertices for t in tris],all_triangles=True)
    def sample(p):
        hit,normal,index,distance=tree.find_nearest(p);tri=tris[index]
        a,b,c=[m.vertices[i].co for i in tri.vertices];ab=b-a;ac=c-a;ap=hit-a
        aa=ab.dot(ab);bb=ab.dot(ac);cc=ac.dot(ac);den=aa*cc-bb*bb
        if abs(den)<1e-18:return m.uv_layers[0].data[tri.loops[0]].uv.copy(),normal
        v=(cc*ap.dot(ab)-bb*ap.dot(ac))/den;w=(aa*ap.dot(ac)-bb*ap.dot(ab))/den
        uv=sum((m.uv_layers[0].data[i].uv*x for i,x in zip(tri.loops,[1-v-w,v,w])),Vector((0,0)))
        n=sum((m.corner_normals[i].vector*x for i,x in zip(tri.loops,[1-v-w,v,w])),Vector()).normalized()
        return uv,n
    return sample
sample_top=sampler(top);sample_bottom=sampler(bottom)
def rim(obj):
    points=set()
    for f in obj.data.polygons:
        coords=[obj.data.vertices[i].co for i in f.vertices]
        if not any(v.z<-.000001 for v in coords):continue
        for v in coords:
            if abs(v.z)<.000001:points.add((round(v.x,8),round(v.y,8)))
    return sorted([Vector(p) for p in points],key=lambda p:math.atan2(p.y,p.x))
def cross(a,b):return a.x*b.y-a.y*b.x
def radial(points,angle):
    ray=Vector((math.cos(angle),math.sin(angle)));hits=[]
    for a,b in zip(points,points[1:]+points[:1]):
        e=b-a;den=cross(ray,e)
        if abs(den)<1e-12:continue
        distance=cross(a,e)/den;along=cross(a,ray)/den
        if distance>0 and -.000001<=along<=1.000001:hits.append(distance)
    if not hits:raise RuntimeError('Mount contour has no radial intersection')
    return ray*max(hits)
rt=rim(top);rb=rim(bottom);angles=sorted(set(round(math.atan2(p.y,p.x),9) for p in rt+rb))
verts=[];end_normals={};steps=10
for ring in range(steps+1):
    t=ring/steps
    for angle in angles:
        a=radial(rt,angle);b=radial(rb,angle)*SCALE
        n0=sample_top(Vector((a.x,a.y,-.00002)))[1];n1=sample_bottom(Vector((b.x/SCALE,b.y/SCALE,-.00002)))[1]
        direction=Vector((math.cos(angle),math.sin(angle)))
        def tangent(n):
            nr=Vector((n.x,n.y)).dot(direction);slope=n.z/nr if abs(nr)>.1 else 0
            return direction*(DEPTH*max(-1.5,min(1.5,slope)))
        xy=(2*t**3-3*t*t+1)*a+(t**3-2*t*t+t)*tangent(n0)+(-2*t**3+3*t*t)*b+(t**3-t*t)*tangent(n1)
        i=len(verts);verts.append((xy.x,xy.y,-DEPTH*t))
        if ring==0:end_normals[i]=n0
        if ring==steps:end_normals[i]=n1
n=len(angles);faces=[]
for j in range(steps):
    for i in range(n):
        a=j*n+i;b=j*n+(i+1)%n;c=(j+1)*n+(i+1)%n;d=(j+1)*n+i
        faces.extend([(a,c,b),(a,d,c)])
mesh=bpy.data.meshes.new('Rune_to_Frost_pommel_interface');mesh.from_pydata(verts,[],faces);mesh.update()
adapter=bpy.data.objects.new('SM_SwordPommel_RuneToFrost',mesh);scene.collection.objects.link(adapter)
uv0=mesh.uv_layers.new(name='RuneMountUV');uv1=mesh.uv_layers.new(name='FrostPatchUV')
color=mesh.color_attributes.new(name='PommelFinish',type='FLOAT_COLOR',domain='CORNER');mesh.color_attributes.active_color=color
patch=json.loads((SRC/'MeleeGuards20260915/finish_patch.json').read_text());lo=patch['uv_min'];hi=patch['uv_max']
for face in mesh.polygons:
    face.use_smooth=True
    for loop in face.loop_indices:
        v=mesh.vertices[mesh.loops[loop].vertex_index].co;t=-v.z/DEPTH
        f=max(0,min(1,(t-.1)/.6));f=f*f*(3-2*f)
        uv0.data[loop].uv=sample_top(v)[0]
        angle=(math.atan2(v.y,v.x)+math.pi)/(2*math.pi)
        uv1.data[loop].uv=(lo[0]+angle*(hi[0]-lo[0]),lo[1]+t*(hi[1]-lo[1]))
        color.data[loop].color=(f,f,f,1)
    ids=list(face.loop_indices)
    if max(uv1.data[i].uv.x for i in ids)-min(uv1.data[i].uv.x for i in ids)>(hi[0]-lo[0])*.5:
        for i in ids:
            if uv1.data[i].uv.x<(hi[0]+lo[0])*.5:uv1.data[i].uv.x+=hi[0]-lo[0]
    if all(color.data[i].color[0]>.999 for i in ids):
        for i in ids:uv0.data[i].uv=uv1.data[i].uv
mesh.update();mesh.normals_split_custom_set([end_normals.get(l.vertex_index,mesh.corner_normals[l.index].vector.copy()) for l in mesh.loops])
def images_for(mat):
    result={}
    for n in mat.node_tree.nodes:
        if n.type!='TEX_IMAGE' or not n.image:continue
        name=n.image.name.lower()
        key='Normal' if 'normal' in name else 'Metallic' if 'metallic' in name else 'Roughness' if 'roughness' in name else 'Emissive' if 'emissive' in name else 'BaseColor'
        result[key]=n.image
    return result
top_images=images_for(next(m for m in top.data.materials if '_Opaque' in m.name));bottom_images=images_for(bottom.data.materials[0])
def tint_socket(nt,source):
    gray=nt.nodes.new('ShaderNodeRGBToBW');nt.links.new(source,gray.inputs[0])
    mul=nt.nodes.new('ShaderNodeMixRGB');mul.blend_type='MULTIPLY';mul.inputs[0].default_value=1;mul.inputs[2].default_value=(*SILVER,1);mul.use_clamp=True
    nt.links.new(gray.outputs[0],mul.inputs[1]);return mul.outputs[0]
mat=bpy.data.materials.new('M_SharedPommel_RuneToFrost');mat.use_nodes=True;nt=mat.node_tree;nt.nodes.clear()
bs=nt.nodes.new('ShaderNodeBsdfPrincipled');output=nt.nodes.new('ShaderNodeOutputMaterial');nt.links.new(bs.outputs[0],output.inputs['Surface'])
vcol=nt.nodes.new('ShaderNodeVertexColor');vcol.layer_name='PommelFinish'
u0=nt.nodes.new('ShaderNodeUVMap');u0.uv_map=uv0.name;u1=nt.nodes.new('ShaderNodeUVMap');u1.uv_map=uv1.name
for channel,socket in [('BaseColor','Base Color'),('Metallic','Metallic'),('Roughness','Roughness')]:
    a=nt.nodes.new('ShaderNodeTexImage');a.image=top_images[channel];nt.links.new(u0.outputs[0],a.inputs[0])
    b=nt.nodes.new('ShaderNodeTexImage');b.image=bottom_images[channel];nt.links.new(u1.outputs[0],b.inputs[0])
    lower=tint_socket(nt,b.outputs[0]) if channel=='BaseColor' else b.outputs[0]
    blend=nt.nodes.new('ShaderNodeMixRGB');nt.links.new(vcol.outputs[0],blend.inputs[0]);nt.links.new(a.outputs[0],blend.inputs[1]);nt.links.new(lower,blend.inputs[2]);nt.links.new(blend.outputs[0],bs.inputs[socket])
# Keep normal detail at the Rune installation edge and fade into the transition surface.
a=nt.nodes.new('ShaderNodeTexImage');a.image=top_images['Normal'];nt.links.new(u0.outputs[0],a.inputs[0])
blend=nt.nodes.new('ShaderNodeMixRGB');nt.links.new(vcol.outputs[0],blend.inputs[0]);nt.links.new(a.outputs[0],blend.inputs[1]);blend.inputs[2].default_value=(.5,.5,1,1)
normal=nt.nodes.new('ShaderNodeNormalMap');normal.uv_map=uv0.name;nt.links.new(blend.outputs[0],normal.inputs['Color']);nt.links.new(normal.outputs[0],bs.inputs['Normal'])
mesh.materials.append(mat)
bpy.context.view_layer.objects.active=adapter;adapter.select_set(True)
bpy.ops.export_scene.fbx(filepath=str(OUT/(adapter.name+'.fbx')),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',bake_anim=False,mesh_smooth_type='FACE',use_tspace=False)
bpy.ops.export_scene.gltf(filepath=str(OUT/(adapter.name+'.glb')),use_selection=True,export_format='GLB',export_all_vertex_colors=True)
keys={'ballast_hardened':'pommel_hardened','ballast_rune':'pommel_runic','ballast_magic_orb':'pommel_mana_orb'}
objects=[]
for old,new in keys.items():
    with bpy.data.libraries.load(str(SRC/'FrostSwordPommelsRepair20260915'/old/'FrostPommel_Editable.blend'),link=False) as (a,b):
        b.objects=['SM_FrostPommel_'+old]
    obj=b.objects[0];scene.collection.objects.link(obj);obj.matrix_world=Matrix.Identity(4);obj.scale=(SCALE,)*3;obj.location.z=-DEPTH
    obj.data=obj.data.copy()
    for i,m in enumerate(obj.data.materials):
        if not any(x in m.name for x in ['Collar','Bronze','InlayBorder','M_FrostCrystalSword']):continue
        newmat=m.copy();newmat.name='RuneFinish_'+old+'_'+m.name;obj.data.materials[i]=newmat
        nt=newmat.node_tree;bs=next(n for n in nt.nodes if n.type=='BSDF_PRINCIPLED')
        if bs.inputs['Base Color'].links:source=bs.inputs['Base Color'].links[0].from_socket
        else:
            rgb=nt.nodes.new('ShaderNodeRGB');rgb.outputs[0].default_value=bs.inputs['Base Color'].default_value;source=rgb.outputs[0]
        nt.links.new(tint_socket(nt,source),bs.inputs['Base Color'])
    obj.hide_render=True;objects.append((new,obj))
scene.render.engine='CYCLES';scene.cycles.samples=48
scene.render.resolution_x=scene.render.resolution_y=1024;scene.render.resolution_percentage=100
scene.render.film_transparent=True;scene.render.image_settings.file_format='PNG';scene.render.image_settings.color_mode='RGBA';scene.view_settings.view_transform='AgX'
scene.world=bpy.data.worlds.new('Shared pommel studio');scene.world.use_nodes=True
background=next(n for n in scene.world.node_tree.nodes if n.type=='BACKGROUND');background.inputs[0].default_value=(.16,.16,.16,1);background.inputs[1].default_value=.45
camera=bpy.data.objects.new('Pommel front camera',bpy.data.cameras.new('Pommel ortho'));scene.collection.objects.link(camera);camera.data.type='ORTHO';camera.data.clip_start=.001;scene.camera=camera
lights=[]
for name,offset,power,size in [('Key',(-.12,-.16,.10),12,.12),('Fill',(.15,-.06,.01),4,.14),('Rim',(.05,.09,.08),8,.10)]:
    o=bpy.data.objects.new(name,bpy.data.lights.new(name,'AREA'));scene.collection.objects.link(o);o.data.energy=power;o.data.shape='DISK';o.data.size=size;lights.append((o,Vector(offset)))
for key,obj in objects:
    obj.hide_render=False;bpy.context.view_layer.update()
    points=[o.matrix_world@v.co for o in [obj,adapter] for v in o.data.vertices]
    low=Vector(tuple(min(v[i] for v in points) for i in range(3)));high=Vector(tuple(max(v[i] for v in points) for i in range(3)));center=(low+high)*.5
    camera.location=center+Vector((0,-.30,0));camera.rotation_euler=(center-camera.location).to_track_quat('-Z','Y').to_euler();camera.data.ortho_scale=max(high.x-low.x,high.z-low.z)/.82
    for light,offset in lights:light.location=center+offset;light.rotation_euler=(center-light.location).to_track_quat('-Z','Y').to_euler()
    scene.render.filepath=str(ICONS/('ue_rune_sword_pommel_'+key+'.png'));bpy.ops.render.render(write_still=True);obj.hide_render=True
    print('SIX_SHARED_RUNE_ICON',key,flush=True)
objects[-1][1].hide_render=False
bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(P/'SixSharedPommels_RuneFit.blend'))
(P/'rune_fit.json').write_text(json.dumps({'scale':SCALE,'adapter_length_cm':DEPTH*100,'silver_tint':SILVER,'adapter':adapter.name,'adapter_triangles':len(faces),'body_meshes_unchanged':True,'icons':'1024 RGBA, front -Y, mount +Z up','ids':keys},indent=2),encoding='utf-8')
print('SIX_SHARED_RUNE_FIT_AUTHORED',flush=True)
