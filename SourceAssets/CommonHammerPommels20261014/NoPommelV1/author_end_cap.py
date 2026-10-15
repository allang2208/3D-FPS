"""Retain the actual upper pommel interface, remove its mass, close the exposed end."""
import bpy,bmesh,json,math
from pathlib import Path
from mathutils import Vector
P=Path(__file__).resolve().parent;ROOT=P.parents[2];(P/'Export').mkdir(exist_ok=True)
with bpy.data.libraries.load(str(ROOT/'SourceAssets/SteelWarhammer20261014/ModulesV1/Warhammer_Modular_Editable.blend'),link=False) as (a,b):
    b.objects=['SM_Warhammer_pommel_factory']
factory=b.objects[0];original=factory.data;original.calc_loop_triangles();mount=list(factory.location)
old=original.materials[0]
with bpy.data.libraries.load(str(ROOT/'SourceAssets/CommonHammerPommels20261014/BuildV1/CommonHammerPommels_Editable.blend'),link=False) as (a,b):
    b.materials=['M_CommonHammerHeadSteel']
steel=b.materials[0]
for obj in list(bpy.context.scene.objects):bpy.data.objects.remove(obj,do_unlink=True)
bpy.context.preferences.filepaths.save_version=0
bpy.context.scene.unit_settings.system='METRIC';bpy.context.scene.unit_settings.scale_length=1
CUT=-.0025
def clip(poly):
    result=[]
    for a,b in zip(poly,poly[1:]+poly[:1]):
        da=a[0].z-CUT;db=b[0].z-CUT
        if da>=0:result.append(a)
        if (da>=0)!=(db>=0):result.append(tuple(x.lerp(y,da/(da-db)) for x,y in zip(a,b)))
    return result
verts=[];faces=[];corners=[]
normals=[n.vector.copy() for n in original.corner_normals]
for tri in original.loop_triangles:
    poly=clip([(original.vertices[original.loops[i].vertex_index].co.copy(),original.uv_layers[0].data[i].uv.copy(),normals[i]) for i in tri.loops])
    for j in range(1,len(poly)-1):
        triangle=[poly[0],poly[j],poly[j+1]]
        if (triangle[1][0]-triangle[0][0]).cross(triangle[2][0]-triangle[0][0]).length<1e-12:continue
        faces.append(tuple(range(len(verts),len(verts)+3)))
        for p in triangle:verts.append(p[0]);corners.append(p)
mesh=bpy.data.meshes.new('Original mounting lip and closed end');mesh.from_pydata(verts,[],faces);mesh.update()
mesh.materials.append(old);mesh.materials.append(steel)
uv0=mesh.uv_layers.new(name='UVMap');uv1=mesh.uv_layers.new(name='SteelUV')
nc=mesh.attributes.new('FactoryNormal',type='FLOAT_VECTOR',domain='CORNER')
color=mesh.color_attributes.new(name='Color',type='FLOAT_COLOR',domain='CORNER')
for face in mesh.polygons:
    face.use_smooth=True
    for i in face.loop_indices:
        p=corners[mesh.loops[i].vertex_index];uv0.data[i].uv=p[1];uv1.data[i].uv=p[1];nc.data[i].vector=p[2];color.data[i].color=(0,0,0,1)
bm=bmesh.new();bm.from_mesh(mesh);bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=1e-7)
edges=[e for e in bm.edges if e.is_boundary and all(abs(v.co.z-CUT)<1e-6 for v in e.verts)]
graph={}
for edge in edges:
    for v in edge.verts:graph.setdefault(v,[]).append(edge.other_vert(v))
if not graph or any(len(x)!=2 for x in graph.values()):raise RuntimeError('Cannot close the original interface boundary')
start=next(iter(graph));ring=[start];previous=None;current=start
while True:
    nxt=next(v for v in graph[current] if v!=previous)
    if nxt==start:break
    if nxt in ring:raise RuntimeError('Invalid interface walk')
    ring.append(nxt);previous,current=current,nxt
if sum(a.co.x*b.co.y-b.co.x*a.co.y for a,b in zip(ring,ring[1:]+ring[:1]))<0:ring.reverse()
center=sum((v.co for v in ring),Vector())/len(ring)
u0=bm.loops.layers.uv['UVMap'];u1=bm.loops.layers.uv['SteelUV'];stored=bm.loops.layers.float_vector['FactoryNormal'];col=bm.loops.layers.float_color['Color']
lower=[bm.verts.new((center.x+(v.co.x-center.x)*.975,center.y+(v.co.y-center.y)*.975,CUT-.0007)) for v in ring]
newfaces=[]
for i in range(len(ring)):
    j=(i+1)%len(ring);newfaces.append(bm.faces.new((ring[i],lower[i],lower[j],ring[j])))
newfaces.append(bm.faces.new(tuple(reversed(lower))))
bm.normal_update()
for face in newfaces:
    face.material_index=1;face.smooth=False
    axes=[i for i in range(3) if i!=max(range(3),key=lambda a:abs(face.normal[a]))]
    for loop in face.loops:
        co=loop.vert.co;loop[u0].uv=(co[axes[0]]/.12,co[axes[1]]/.12);loop[u1].uv=loop[u0].uv
        loop[stored]=face.normal;loop[col]=(1,0,0,1)
bmesh.ops.triangulate(bm,faces=list(bm.faces));bm.to_mesh(mesh);bm.free();mesh.update()
mesh.normals_split_custom_set([tuple(n.vector.normalized()) for n in mesh.attributes['FactoryNormal'].data])
name='SM_CommonHammerPommel_NoWeightCap_V1';obj=bpy.data.objects.new(name,mesh);bpy.context.scene.collection.objects.link(obj)
obj.select_set(True);bpy.context.view_layer.objects.active=obj
bpy.ops.export_scene.fbx(filepath=str(P/'Export'/(name+'.fbx')),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',bake_anim=False,mesh_smooth_type='FACE',use_tspace=True,path_mode='STRIP')
mesh.calc_loop_triangles();obj.location=mount
bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(P/'NoPommel_EndClosure_Editable.blend'))
row={'id':'no_pommel','name':'无配重','mesh':name,'triangles':len(mesh.loop_triangles),'location_cm':[v*100 for v in mount],'materials':[m.name for m in mesh.materials]}
(P/'exports.json').write_text(json.dumps({'parts':[row],'interface':'warhammer_factory_v1','retained_end_depth_m':.0032,'weighted_body_removed':True,'tested':False},ensure_ascii=False,indent=2),encoding='utf-8')
print('NO_POMMEL_END_CLOSURE_AUTHORED '+json.dumps(row),flush=True)
