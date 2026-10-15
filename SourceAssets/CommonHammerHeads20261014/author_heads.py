"""Three paired steel heads, joined to the actual factory neck boundaries."""
import bpy,bmesh,json,math,sys
import numpy as np
from pathlib import Path
from mathutils import Vector
P=Path(__file__).resolve().parent;ROOT=P.parents[1];sys.path.insert(0,str(P))
from catalog import OPTIONS
for folder in ('Export','Textures'): (P/folder).mkdir(parents=True,exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'SourceAssets/SteelWarhammer20261014/ModulesV1/Warhammer_Modular_Editable.blend'))
bpy.context.preferences.filepaths.save_version=0
factory=bpy.data.objects['SM_Warhammer_hammer_heads_factory'];source=factory.data.copy();source.update()
old_mat=source.materials[0];cut=.075
# Shared, physically scaled steel maps, independent of the source model's atlas.
N=1024;rng=np.random.default_rng(20261014)
fy=np.fft.fftfreq(N)[:,None];fx=np.fft.rfftfreq(N)[None,:]
noise=np.fft.irfft2(np.fft.rfft2(rng.standard_normal((N,N)))/(1+220*(fx*fx+fy*fy))**1.1,s=(N,N))
noise=(noise-noise.mean())/noise.std();grain=rng.standard_normal((N,1))*.18
height=noise*.12+grain
for _ in range(1700):
    y=int(rng.integers(N));x=int(rng.integers(N));length=int(rng.integers(8,135))
    height[y,(np.arange(length)+x)%N]-=float(rng.uniform(.05,.28))
gx=(np.roll(height,-1,1)-np.roll(height,1,1))*.35;gy=(np.roll(height,-1,0)-np.roll(height,1,0))*.35
norm=np.stack((-gx,-gy,np.ones_like(gx)),axis=-1);norm/=np.linalg.norm(norm,axis=-1,keepdims=True)
base=np.clip(.255+noise*.025+grain*.015,.12,.42)
rough=np.clip(.40+noise*.055+grain*.04,.23,.62)
arrays={'BaseColor':np.stack((base*.98,base,base*1.02),axis=-1),
        'MetallicRoughness':np.stack((np.ones_like(base),rough,np.ones_like(base)*.98),axis=-1),
        'Normal':norm*.5+.5}
textures={}
for key,array in arrays.items():
    img=bpy.data.images.new('T_CommonHammerSteel_'+key,width=N,height=N,alpha=True)
    img.colorspace_settings.name='sRGB' if key=='BaseColor' else 'Non-Color'
    rgba=np.concatenate((array,np.ones((N,N,1))),axis=-1).astype(np.float32)
    img.pixels.foreach_set(rgba.ravel());img.filepath_raw=str(P/'Textures'/(key+'.png'));img.file_format='PNG';img.save();img.pack();textures[key]=img

mat=old_mat.copy();mat.name='M_CommonHammerHeadSteel'
nodes=mat.node_tree.nodes;links=mat.node_tree.links
bs=next(n for n in nodes if n.type=='BSDF_PRINCIPLED');vertex=nodes.new('ShaderNodeVertexColor');vertex.layer_name='Color'
split=nodes.new('ShaderNodeSeparateColor');links.new(vertex.outputs['Color'],split.inputs[0])
uv=nodes.new('ShaderNodeUVMap');uv.uv_map='SteelUV'
samples={}
for key,img in textures.items():
    n=nodes.new('ShaderNodeTexImage');n.image=img;links.new(uv.outputs[0],n.inputs['Vector']);samples[key]=n
mr=nodes.new('ShaderNodeSeparateColor');links.new(samples['MetallicRoughness'].outputs['Color'],mr.inputs[0])
normal=nodes.new('ShaderNodeNormalMap');normal.uv_map='SteelUV';links.new(samples['Normal'].outputs['Color'],normal.inputs['Color'])
for pin,new in [('Base Color',samples['BaseColor'].outputs['Color']),('Roughness',mr.outputs['Green']),('Metallic',mr.outputs['Blue']),('Normal',normal.outputs['Normal'])]:
    old=next((l.from_socket for l in links if l.to_socket==bs.inputs[pin]),None)
    if old:
        mix=nodes.new('ShaderNodeMixRGB');links.new(split.outputs['Red'],mix.inputs[0]);links.new(old,mix.inputs[1]);links.new(new,mix.inputs[2]);links.new(mix.outputs[0],bs.inputs[pin])
    else:links.new(new,bs.inputs[pin])

def clip(poly,axis,limit,positive):
    out=[]
    for a,b in zip(poly,poly[1:]+poly[:1]):
        da=(a[0][axis]-limit)*(1 if positive else -1);db=(b[0][axis]-limit)*(1 if positive else -1)
        if da>=0:out.append(a)
        if (da>=0)!=(db>=0):
            t=da/(da-db);out.append(tuple(x.lerp(y,t) for x,y in zip(a,b)))
    return out

source.calc_loop_triangles();normals=[n.vector.copy() for n in source.corner_normals]
verts=[];faces=[];corners=[]
for tri in source.loop_triangles:
    poly=[(source.vertices[source.loops[i].vertex_index].co.copy(),source.uv_layers[0].data[i].uv.copy(),normals[i]) for i in tri.loops]
    poly=clip(clip(poly,0,-cut,True),0,cut,False)
    for k in range(1,len(poly)-1):
        triangle=[poly[0],poly[k],poly[k+1]]
        if (triangle[1][0]-triangle[0][0]).cross(triangle[2][0]-triangle[0][0]).length<1e-12:continue
        faces.append(tuple(range(len(verts),len(verts)+3)))
        for item in triangle:verts.append(item[0]);corners.append(item)
connector=bpy.data.meshes.new('Factory head necks');connector.from_pydata(verts,[],faces);connector.update()
connector.materials.append(old_mat);connector.materials.append(mat)
uv0=connector.uv_layers.new(name='UVMap');uv1=connector.uv_layers.new(name='SteelUV')
stored=connector.attributes.new('SurfaceNormal',type='FLOAT_VECTOR',domain='CORNER')
color=connector.color_attributes.new(name='Color',type='FLOAT_COLOR',domain='CORNER')
for f in connector.polygons:
    f.use_smooth=True
    for i in f.loop_indices:
        item=corners[connector.loops[i].vertex_index];uv0.data[i].uv=item[1];uv1.data[i].uv=item[1]
        stored.data[i].vector=item[2].normalized();color.data[i].color=(0,0,0,1)
for obj in list(bpy.context.scene.objects):bpy.data.objects.remove(obj,do_unlink=True)

PROFILES={
 'heavy_forged':[(.078,None),(.091,(.038,.047)),(.104,(.053,.063)),(.111,(.057,.067)),(.174,(.057,.067)),(.183,(.050,.060)),(.1835,(.042,.052))],
 'flanged_breaker':[(.078,None),(.091,(.036,.041)),(.102,(.055,.061)),(.112,(.059,.065)),(.157,(.059,.065)),(.168,(.051,.057)),(.165,(.032,.037))],
 'light_drum':[(.078,None),(.091,(.030,.034)),(.098,(.036,.041)),(.104,(.036,.041)),(.110,(.028,.033)),(.137,(.028,.033)),(.143,(.036,.041)),(.151,(.036,.041)),(.157,(.031,.036)),(.154,(.025,.030))]
}
def radius_shape(kind,theta,ry,rz):
    c=math.cos(theta);s=math.sin(theta)
    if kind=='heavy_forged':
        r=(abs(c)**5+abs(s)**5)**(-.2)
    elif kind=='flanged_breaker':
        r=.68+.32*max(0.,math.cos(8*theta))**2
    else:r=1.
    return Vector((0,ry*c*r,rz*s*r))

receipts=[];interfaces={}
for option in OPTIONS:
    kind=option['id'];data=connector.copy();bm=bmesh.new();bm.from_mesh(data)
    bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=.0000005);bm.normal_update()
    normals_layer=bm.loops.layers.float_vector['SurfaceNormal'];u0=bm.loops.layers.uv['UVMap'];u1=bm.loops.layers.uv['SteelUV'];col=bm.loops.layers.float_color['Color']
    all_new=[];caps=[];stored_boundary={};rings_receipt=[]
    for sign in (-1,1):
        edges=[e for e in bm.edges if e.is_boundary and all(abs(v.co.x-sign*cut)<3e-6 for v in e.verts)]
        graph={}
        for edge in edges:
            for v in edge.verts:graph.setdefault(v,[]).append(edge.other_vert(v))
        if not graph or any(len(v)!=2 for v in graph.values()):raise RuntimeError('Factory neck boundary is not a single ring: '+kind)
        start=min(graph,key=lambda v:tuple(v.co));ring=[start];previous=None;current=start
        while True:
            nxt=next(v for v in graph[current] if v!=previous)
            if nxt==start:break
            if nxt in ring:raise RuntimeError('Factory neck ring folds onto itself')
            ring.append(nxt);previous,current=current,nxt
        area=sum(a.co.y*b.co.z-b.co.y*a.co.z for a,b in zip(ring,ring[1:]+ring[:1]))
        if area*sign<0:ring.reverse()
        center=Vector((sign*cut,(min(v.co.y for v in ring)+max(v.co.y for v in ring))*.5,(min(v.co.z for v in ring)+max(v.co.z for v in ring))*.5))
        original=[v.co.copy() for v in ring];angles=[math.atan2(v.co.z-center.z,v.co.y-center.y) for v in ring]
        old_uv=[];old_norm=[]
        for v in ring:
            loops=[loop for face in v.link_faces for loop in face.loops if loop.vert==v]
            old_uv.append(loops[0][u0].uv.copy());old_norm.append(sum((Vector(l[normals_layer]) for l in loops),Vector()).normalized())
            stored_boundary[v]=old_norm[-1]
        rings_receipt.append({'side':sign,'cut_x_m':sign*cut,'boundary_local_m':[list(v.co) for v in ring]})
        n=len(ring);previous_ring=ring
        for stage,(x,dims) in enumerate(PROFILES[kind]):
            new_ring=[]
            for j in range(n):
                if dims is None:
                    radial=Vector((0,original[j].y-center.y,original[j].z-center.z)).normalized()
                    denom=old_norm[j].dot(radial)
                    slope=max(-1.,min(1.,-old_norm[j].x*sign/denom)) if abs(denom)>.1 else 0.
                    point=original[j]+Vector((sign*(x-cut),0,0))+radial*(x-cut)*slope
                else:point=Vector((sign*x,center.y,center.z))+radius_shape(kind,angles[j],*dims)
                new_ring.append(bm.verts.new(point))
            for j in range(n):
                k=(j+1)%n;face=bm.faces.new((previous_ring[j],previous_ring[k],new_ring[k],new_ring[j]));face.material_index=1;face.smooth=True;all_new.append(face)
                for loop,index in zip(face.loops,(j,k,k,j)):
                    blend=min(1.,max(0.,(abs(loop.vert.co.x)-cut)/.025));new_uv=Vector(((abs(loop.vert.co.x)-cut)/.12,(j+1 if index==k else j)/n))
                    loop[u1].uv=new_uv;loop[u0].uv=old_uv[index].lerp(new_uv,blend);loop[col]=(blend,0,0,1)
            previous_ring=new_ring
        cap_center=bm.verts.new(Vector((sign*PROFILES[kind][-1][0],center.y,center.z)))
        for j in range(n):
            face=bm.faces.new((previous_ring[j],previous_ring[(j+1)%n],cap_center));face.material_index=1;face.smooth=False;caps.append(face);all_new.append(face)
            for loop in face.loops:
                loop[u0].uv=((loop.vert.co.y-center.y)/.12+.5,(loop.vert.co.z-center.z)/.12+.5);loop[u1].uv=loop[u0].uv;loop[col]=(1,0,0,1)
    bm.normal_update()
    for face in all_new:
        for loop in face.loops:loop[normals_layer]=stored_boundary.get(loop.vert,face.normal if face in caps else loop.vert.normal)
    bmesh.ops.triangulate(bm,faces=all_new);bm.to_mesh(data);bm.free();data.update()
    data.normals_split_custom_set([tuple(n.vector) for n in data.attributes['SurfaceNormal'].data])
    name='SM_CommonHammerHeads_'+kind;obj=bpy.data.objects.new(name,data);bpy.context.scene.collection.objects.link(obj)
    bpy.ops.object.select_all(action='DESELECT');obj.select_set(True);bpy.context.view_layer.objects.active=obj
    bpy.ops.export_scene.fbx(filepath=str(P/'Export'/(name+'.fbx')),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',
        bake_anim=False,mesh_smooth_type='FACE',use_tspace=True,path_mode='STRIP')
    data.calc_loop_triangles();receipts.append({'id':kind,'name':option['name'],'mesh':name,'triangles':len(data.loop_triangles),'location_cm':[0,0,92.5000011920929]})
    interfaces[kind]=rings_receipt;obj.location.z=.925;obj.hide_render=True;obj.hide_set(True)
first=bpy.data.objects[receipts[0]['mesh']];first.hide_render=False;first.hide_set(False)
bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(P/'CommonHammerHeads_Editable.blend'))
(P/'exports.json').write_text(json.dumps({'parts':receipts,'source_interface':'warhammer_factory_v1','tested':False},ensure_ascii=False,indent=2),encoding='utf-8')
(P/'interfaces.json').write_text(json.dumps({'original_mounts':'SteelWarhammer20261014/ModulesV1/interfaces.json','new_neck_boundaries':interfaces},indent=2),encoding='utf-8')
print('COMMON_HAMMER_HEADS_AUTHORED',json.dumps(receipts,ensure_ascii=False))
