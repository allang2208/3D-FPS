"""Fit the real generated body to the frozen frost_hilt_v1 stock collar.
No gameplay tests or acceptance renders. Optional 'icon' produces the UI asset.
"""
import bpy,bmesh,json,math,sys
import numpy as np
from pathlib import Path
from mathutils import Vector,Matrix
from mathutils.bvhtree import BVHTree
P=Path(__file__).parent
ARGS=sys.argv[sys.argv.index('--')+1:];KEY=ARGS[0];OUT=P/KEY;OUT.mkdir(exist_ok=True)
OLD=P.parent/'FrostSwordPommels5080_20260915'
SOURCE=P.parent/'FrostSwordModules20260915/FrostSword_Modular_Editable.blend'
WIDTHS={'ballast_hardened':.076,'ballast_rune':.070,'ballast_magic_orb':.072}
COLLAR_END=-.004;BODY_CUT=-.014
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.read_factory_settings(use_empty=True)

def activate(obj):
    bpy.ops.object.select_all(action='DESELECT');obj.hide_set(False);obj.select_set(True);bpy.context.view_layer.objects.active=obj
def apply(obj,mod):
    activate(obj);bpy.ops.object.modifier_apply(modifier=mod.name)
def source_object(name):
    with bpy.data.libraries.load(str(SOURCE),link=False) as (src,dst):dst.objects=[name]
    obj=dst.objects[0];bpy.context.collection.objects.link(obj);obj.matrix_world=Matrix.Identity(4);obj.hide_render=True;return obj
stock=source_object('SM_FrostSword_Pommel_factory');blade=source_object('SM_FrostSword_Blade_factory')

def projector(mesh):
    mesh.calc_loop_triangles();triangles=list(mesh.loop_triangles)
    bvh=BVHTree.FromPolygons([v.co for v in mesh.vertices],[t.vertices for t in triangles],all_triangles=True)
    def sample(point):
        hit,normal,index,d=bvh.find_nearest(point)
        tri=triangles[index];a,b,c=[mesh.vertices[i].co for i in tri.vertices]
        v0=b-a;v1=c-a;v2=hit-a;d00=v0.dot(v0);d01=v0.dot(v1);d11=v1.dot(v1);den=d00*d11-d01*d01
        if abs(den)<1e-16:return mesh.uv_layers[0].data[tri.loops[0]].uv.copy()
        t=(d11*v2.dot(v0)-d01*v2.dot(v1))/den;s=(d00*v2.dot(v1)-d01*v2.dot(v0))/den
        uvs=[mesh.uv_layers[0].data[i].uv for i in tri.loops];return uvs[0]*(1-t-s)+uvs[1]*t+uvs[2]*s
    return sample
stock_uv=projector(stock.data);blade_uv=projector(blade.data)

def clip_mesh(obj,z,keep_above):
    data=obj.data;data.calc_loop_triangles();records=[]
    uv=data.uv_layers[0].data;normals=[n.vector.copy() for n in data.corner_normals]
    for tri in data.loop_triangles:
        poly=[(data.vertices[data.loops[i].vertex_index].co.copy(),uv[i].uv.copy(),normals[i]) for i in tri.loops];clipped=[]
        for a,b in zip(poly,poly[1:]+poly[:1]):
            da=(a[0].z-z)*(1 if keep_above else -1);db=(b[0].z-z)*(1 if keep_above else -1)
            if da>=0:clipped.append(a)
            if (da>=0)!=(db>=0):
                t=da/(da-db);clipped.append(tuple(x.lerp(y,t) for x,y in zip(a,b)))
        for i in range(1,len(clipped)-1):records.append(([clipped[0],clipped[i],clipped[i+1]],tri.material_index))
    return records

# glTF Y-up is converted to Blender Z-up by the native importer. Size the body
# envelope here; the installation datum is taken from the stock mesh below.
MASTER=(OLD if KEY=='ballast_hardened' else P)/KEY/'textured_master_00001_.glb'
bpy.ops.import_scene.gltf(filepath=str(MASTER))
imported=[o for o in bpy.context.selected_objects if o.type=='MESH']
for obj in imported:
    obj.data.transform(obj.matrix_world);obj.matrix_world=Matrix.Identity(4)
activate(imported[0])
for obj in imported:obj.select_set(True)
bpy.ops.object.join();high=bpy.context.object;high.name='Generated_5080_Master'
xyz=np.array([v.co[:] for v in high.data.vertices]);lo=xyz.min(0);hi=xyz.max(0)
scale=WIDTHS[KEY]/(hi[0]-lo[0]);size=(hi-lo)*scale
new=(xyz-(lo+hi)/2)*scale;new[:,2]-=size[2]/2
high.data.vertices.foreach_set('co',new.ravel());high.data.update()
# glTF splits positions at UV seams. Weld before reduction, retaining loop UVs.
bm=bmesh.new();bm.from_mesh(high.data)
bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=.000001)
bmesh.ops.dissolve_degenerate(bm,edges=list(bm.edges),dist=.0000001)
bmesh.ops.holes_fill(bm,edges=[e for e in bm.edges if e.is_boundary],sides=16)
bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(high.data);bm.free();high.data.update()
bsdf=next(n for n in high.data.materials[0].node_tree.nodes if n.type=='BSDF_PRINCIPLED')
def linked_image(socket):
    for link in socket.links:
        node=link.from_node
        if node.type=='TEX_IMAGE':return node.image
        for s in node.inputs:
            image=linked_image(s)
            if image:return image
    return None
generated_color=linked_image(bsdf.inputs['Base Color'])
low=high.copy();low.data=high.data.copy();bpy.context.collection.objects.link(low);low.name='Generated_Game_Body'
dec=low.modifiers.new('Welded game mesh preserving outline','DECIMATE');dec.ratio=min(1,22000/max(1,len(low.data.polygons)));dec.use_collapse_triangulate=True;apply(low,dec)
for f in low.data.polygons:f.use_smooth=True
low.data.update()
# Bake onto fresh game UVs instead of keeping fragmented, reduced source islands.
while low.data.uv_layers:low.data.uv_layers.remove(low.data.uv_layers[0])
low.data.uv_layers.new(name='UVMap');activate(low)
bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT')
bpy.ops.uv.smart_project(angle_limit=math.radians(66),island_margin=.012)
bpy.ops.object.mode_set(mode='OBJECT')
for slot in low.material_slots:slot.material=slot.material.copy()
scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=4
scene.render.bake.use_selected_to_active=True;scene.render.bake.cage_extrusion=.001;scene.render.bake.max_ray_distance=.003;scene.render.bake.margin=16
hn=high.data.materials[0].node_tree.nodes;hl=high.data.materials[0].node_tree.links
hout=next(n for n in hn if n.type=='OUTPUT_MATERIAL');emission=hn.new('ShaderNodeEmission')
def bake_image(name,kind,resolution=4096):
    image=bpy.data.images.new(name,width=resolution,height=resolution,alpha=False)
    image.colorspace_settings.name='sRGB' if name=='base_color' else 'Non-Color'
    for slot in low.material_slots:
        nodes=slot.material.node_tree.nodes;target=nodes.new('ShaderNodeTexImage');target.image=image;nodes.active=target
    activate(low);high.hide_set(False);high.select_set(True);bpy.ops.object.bake(type=kind)
    image.filepath_raw=str(OUT/(name+'.png'));image.file_format='PNG';image.save();return image
hl.new(bsdf.inputs['Base Color'].links[0].from_socket,emission.inputs['Color']);hl.new(emission.outputs[0],hout.inputs['Surface'])
base_color=bake_image('base_color','EMIT')
combine=hn.new('ShaderNodeCombineXYZ');combine.inputs['X'].default_value=1
for target,source in [('Y','Roughness'),('Z','Metallic')]:
    socket=bsdf.inputs[source]
    if socket.is_linked:hl.new(socket.links[0].from_socket,combine.inputs[target])
    else:combine.inputs[target].default_value=socket.default_value
hl.new(combine.outputs[0],emission.inputs['Color']);orm=bake_image('orm','EMIT')
hl.new(bsdf.outputs[0],hout.inputs['Surface']);normal_image=bake_image('normal','NORMAL',2048)
pixels=np.empty(len(base_color.pixels),np.float32);base_color.pixels.foreach_get(pixels);pixels=pixels.reshape((base_color.size[1],base_color.size[0],4))
def pixel(uv):
    return pixels[min(pixels.shape[0]-1,max(0,int(uv.y*pixels.shape[0]))),min(pixels.shape[1]-1,max(0,int(uv.x*pixels.shape[1]))),:3]
mask=np.clip((pixels[:,:,:3].min(axis=2)-.45)/.3,0,1)*np.clip(1-(pixels[:,:,:3].max(axis=2)-pixels[:,:,:3].min(axis=2))/.20,0,1)
mask_rgba=np.repeat(mask[:,:,None],4,axis=2);mask_rgba[:,:,3]=1
rune_mask=bpy.data.images.new('GeneratedRuneCoverage',width=pixels.shape[1],height=pixels.shape[0],alpha=True);rune_mask.colorspace_settings.name='Non-Color';rune_mask.pixels.foreach_set(mask_rgba.ravel());rune_mask.filepath_raw=str(OUT/'rune_mask.png');rune_mask.file_format='PNG';rune_mask.save()
high.hide_render=True;high.hide_set(True)
body=clip_mesh(low,BODY_CUT,False);collar=clip_mesh(stock,COLLAR_END,True)

# Keep the installation atlas and the generated body's own baked UVs separate.
stock_material=stock.data.materials[0]
stock_images={}
for n in stock_material.node_tree.nodes:
    if n.type=='TEX_IMAGE':
        name=n.image.name.lower()
        tag='normal' if 'normal' in name else 'metallic' if 'metallic' in name else 'roughness' if 'roughness' in name else 'base'
        stock_images[tag]=n.image
def body_material(crystal=False):
    mat=bpy.data.materials.new('M_FrostPommel_Crystal' if crystal else 'M_FrostPommel_Bronze');mat.use_nodes=True
    n=mat.node_tree.nodes;l=mat.node_tree.links;b=n.get('Principled BSDF');uv=n.new('ShaderNodeUVMap');uv.uv_map='UVMap'
    tex=n.new('ShaderNodeTexImage');tex.image=base_color;l.new(uv.outputs['UV'],tex.inputs['Vector']);l.new(tex.outputs['Color'],b.inputs['Base Color'])
    packed=n.new('ShaderNodeTexImage');packed.image=orm;l.new(uv.outputs['UV'],packed.inputs['Vector']);split=n.new('ShaderNodeSeparateXYZ');l.new(packed.outputs['Color'],split.inputs[0])
    l.new(split.outputs['Y'],b.inputs['Roughness']);b.inputs['Metallic'].default_value=.82
    tex=n.new('ShaderNodeTexImage');tex.image=normal_image;normal=n.new('ShaderNodeNormalMap');l.new(tex.outputs['Color'],normal.inputs['Color']);l.new(normal.outputs['Normal'],b.inputs['Normal'])
    if crystal:
        for socket in ['Base Color','Roughness']:
            for link in list(b.inputs[socket].links):l.remove(link)
        b.inputs['Base Color'].default_value=(.0052,.3486,.5705,1)
        b.inputs['Metallic'].default_value=0;b.inputs['Roughness'].default_value=.16;b.inputs['Transmission Weight'].default_value=.65;b.inputs['IOR'].default_value=1.45
        b.inputs['Emission Color'].default_value=(.0052,.3486,.5705,1);b.inputs['Emission Strength'].default_value=.20
    elif KEY=='ballast_rune':
        tex=n.new('ShaderNodeTexImage');tex.image=rune_mask
        l.new(tex.outputs['Color'],b.inputs['Emission Color']);b.inputs['Emission Strength'].default_value=1.6
    return mat
bronze=body_material();crystal=body_material(True)

vertices=[];faces=[];corner_uv=[];corner_uv1=[];corner_normals=[];materials=[];lookup={}
def vertex(p):
    key=tuple(round(v,6) for v in p)
    if key not in lookup:lookup[key]=len(vertices);vertices.append(p.copy())
    return lookup[key]
def atlas(p,is_crystal):
    if not is_crystal:return stock_uv(p)
    z=.16+min(1,max(0,(-p.z-.014)/.05))*.48
    target=Vector((p.x*.5,(1 if p.y>=0 else -1)*.045,z))
    return blade_uv(target)
def emit(samples,mat,original=False):
    if (samples[1][0]-samples[0][0]).cross(samples[2][0]-samples[0][0]).length<1e-12:return
    faces.append([vertex(t[0]) for t in samples]);materials.append(mat)
    for p,uv,n in samples:
        corner_uv.append(uv.copy());corner_uv1.append(uv.copy());corner_normals.append(n.normalized())
for poly,mat in collar:emit(poly,0,True)
for poly,mat in body:
    color=pixel(sum((p[1] for p in poly),Vector((0,0)))/3)
    blue=KEY=='ballast_magic_orb' and color[2]>color[0]*1.45 and color[1]>color[0]*1.30
    emit(poly,2 if blue else 1)

def boundary(z):
    edges={}
    for f in faces:
        for a,b in zip(f,f[1:]+f[:1]):
            key=tuple(sorted((a,b)));edges[key]=edges.get(key,0)+1
    graph={}
    for (a,b),count in edges.items():
        if count==1 and abs(vertices[a].z-z)<1e-6 and abs(vertices[b].z-z)<1e-6:
            graph.setdefault(a,[]).append(b);graph.setdefault(b,[]).append(a)
    rings=[];unused=set(graph)
    while unused:
        start=next(iter(unused));current=start;prev=None;ring=[]
        for _ in range(len(graph)+1):
            ring.append(current);unused.discard(current);nxt=next((v for v in graph[current] if v!=prev and (v in unused or v==start)),start)
            if nxt==start:break
            prev,current=current,nxt
        rings.append(ring)
    ring=max(rings,key=lambda r:sum((vertices[r[i]]-vertices[r[i-1]]).length for i in range(len(r))))
    return sorted(ring,key=lambda i:math.atan2(vertices[i].y,vertices[i].x))
top=boundary(COLLAR_END);bottom=boundary(BODY_CUT)
normal_sums={i:Vector() for i in set(top+bottom)};uv_at={}
for fi,f in enumerate(faces):
    for j,v in enumerate(f):
        if v in normal_sums:normal_sums[v]+=corner_normals[fi*3+j];uv_at[v]=corner_uv[fi*3+j]
for i in normal_sums:normal_sums[i].normalize()
def angle(i):return (math.atan2(vertices[i].y,vertices[i].x)+math.pi)/(2*math.pi)
def ring_sample(ring,t):
    for i,a in enumerate(ring):
        b=ring[(i+1)%len(ring)];ta=angle(a);tb=angle(b)+(1 if i==len(ring)-1 else 0);tt=t+(1 if t<ta and i==len(ring)-1 else 0)
        if ta<=tt<=tb:
            k=(tt-ta)/max(1e-10,tb-ta);return vertices[a].lerp(vertices[b],k),normal_sums[a].lerp(normal_sums[b],k).normalized()
    return vertices[ring[0]],normal_sums[ring[0]]
def slope(p,n):
    radial=Vector((p.x,p.y,0)).normalized();d=n.dot(radial)
    return radial*max(-2,min(2,-n.z/d)) if abs(d)>.05 else Vector()
def connect(a,b):
    i=j=0
    while i<len(a) or j<len(b):
        ia=a[i%len(a)];ib=b[j%len(b)]
        na=angle(a[(i+1)%len(a)])+(1 if i+1>=len(a) else 0) if i<len(a) else 1e9
        nb=angle(b[(j+1)%len(b)])+(1 if j+1>=len(b) else 0) if j<len(b) else 1e9
        if na<nb:ids=[ia,a[(i+1)%len(a)],ib];i+=1
        else:ids=[ia,b[(j+1)%len(b)],ib];j+=1
        # Outward orientation independent of source loop winding.
        ps=[vertices[v] for v in ids];center=sum(ps,Vector())/3
        if (ps[1]-ps[0]).cross(ps[2]-ps[0]).dot(Vector((center.x,center.y,0)))<0:ids.reverse()
        emit([(vertices[v],stock_uv(vertices[v]),normal_sums[v]) for v in ids],0,True)
last=top
for step in range(1,9):
    t=step/9;ring=[]
    for b in bottom:
        end=vertices[b];start,n0=ring_sample(top,angle(b));n1=normal_sums[b];gap=BODY_CUT-COLLAR_END
        p=(2*t**3-3*t*t+1)*start+(t**3-2*t*t+t)*slope(start,n0)*gap+(-2*t**3+3*t*t)*end+(t**3-t*t)*slope(end,n1)*gap
        p.z=COLLAR_END+gap*t;i=vertex(p);normal_sums[i]=n0.lerp(n1,t).normalized();ring.append(i)
    connect(last,ring);last=ring
connect(last,bottom)
data=bpy.data.meshes.new('Pommel fitted continuous surface');data.from_pydata(vertices,[],faces);data.update()
for mat in (stock_material,bronze,crystal):data.materials.append(mat)
uv0=data.uv_layers.new(name='UVMap');uv1=data.uv_layers.new(name='StockSurfaceUV')
for f in data.polygons:
    f.material_index=materials[f.index];f.use_smooth=True
    for i in f.loop_indices:uv0.data[i].uv=corner_uv[i];uv1.data[i].uv=corner_uv1[i]
data.uv_layers.active_index=0;data.uv_layers[0].active_render=True
data.normals_split_custom_set(corner_normals)
obj=bpy.data.objects.new('SM_FrostPommel_'+KEY,data);bpy.context.collection.objects.link(obj)
low.hide_set(True);low.hide_render=True;stock.hide_set(True);blade.hide_set(True)
activate(obj)
bpy.ops.export_scene.fbx(filepath=str(OUT/(obj.name+'.fbx')),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',bake_anim=False,mesh_smooth_type='FACE',use_tspace=True)
bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'FrostPommel_Editable.blend'))
(OUT/'authoring.json').write_text(json.dumps({'id':KEY,'generator_master':str(MASTER),'uniform_scale':scale,'original_source':str(SOURCE),'generated_import_bounds':[lo.tolist(),hi.tolist()],'body_size_m':list(size),'stock_collar_end_m':COLLAR_END,'generated_body_cut_m':BODY_CUT,'pivot':'original grip-pommel interface; UE install [0,0,-22.7] cm','interface':'frost_hilt_v1','stock_ring_vertices':len(top),'body_ring_vertices':len(bottom),'triangles':len(faces),'material_triangles':{m.name:materials.count(i) for i,m in enumerate(data.materials)},'material_slots':[m.name for m in data.materials],'source_textures':{k:v.name for k,v in stock_images.items()},'testing':'not run'},indent=2))
print('FROST_POMMEL_AUTHORED',KEY,len(faces),flush=True)
