"""Recover source triangle orientation and split normals lost by island-wise recalculation."""
import bpy,bmesh,json
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from mathutils.geometry import barycentric_transform
P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/ChapelNun20261115';O=R/'HeadQualityR2/Authored'
bpy.ops.wm.open_mainfile(filepath=str(O/'Nun_Head_Hair_R2.blend'))
head=bpy.data.objects['SK_NunHead'];me=head.data
existing=set(bpy.data.objects)
bpy.ops.import_scene.gltf(filepath=str(R/'MeshyHeadR1/Source/NunHead_R1_glb.glb'))
source=next(o for o in bpy.data.objects if o not in existing and o.type=='MESH')
bpy.ops.object.select_all(action='DESELECT');source.select_set(True);bpy.context.view_layer.objects.active=source
bpy.ops.object.transform_apply(location=True,rotation=True,scale=True)
sm=source.data;sm.calc_loop_triangles();points=[]
for v in sm.vertices:points.append(Vector((v.co.x*15.8,-v.co.y*15.8+1.4,v.co.z*15.8+168.0523223876953-.94961101*15.8)))
faces=[tuple(reversed(t.vertices)) for t in sm.loop_triangles]
normals=[]
for t in sm.loop_triangles:
    normals.append([Vector((sm.corner_normals[k].vector.x,-sm.corner_normals[k].vector.y,sm.corner_normals[k].vector.z)).normalized() for k in reversed(t.loops)])
ref=BVHTree.FromPolygons(points,faces,all_triangles=True)
native=json.loads((R/'ProductionR1/Inputs/native_head.json').read_text())
np=[Vector(v) for v in native['positions']]
ni=[i for i,m in enumerate(native['triangle_materials']) if m==0]
nf=[tuple(reversed(native['triangles'][i])) for i in ni]
nn=[[Vector(v) for v in reversed(native['normals'][i])] for i in ni]
nref=BVHTree.FromPolygons(np,nf,all_triangles=True)
bm=bmesh.new();bm.from_mesh(me);bm.normal_update();flipped=0
for f in bm.faces:
    if f.material_index==4:continue
    lookup=nref if f.material_index==1 else ref
    point,normal,index,dist=lookup.find_nearest(f.calc_center_median())
    if normal is not None and f.normal.dot(normal)<0:
        f.normal_flip();flipped+=1
bm.to_mesh(me);bm.free();me.update()
# Restore smooth source normals on every corner while leaving UV seams and weights intact.
types={}
for f in me.polygons:
    for i in f.vertices:types.setdefault(i,f.material_index)
smooth=[]
for v in me.vertices:
    material=types[v.index]
    if material==4:
        smooth.append(v.normal.copy());continue
    tree,ps,fs,ns=(nref,np,nf,nn) if material==1 else (ref,points,faces,normals)
    p,n,index,dist=tree.find_nearest(v.co)
    a,b,c=(ps[j] for j in fs[index]);na,nb,nc=ns[index]
    normal=barycentric_transform(p,a,b,c,na,nb,nc)
    smooth.append(normal.normalized() if normal.length_squared>1e-10 else n)
me.normals_split_custom_set([smooth[l.vertex_index] for l in me.loops])
for obj in list(bpy.data.objects):
    if obj not in existing:bpy.data.objects.remove(obj,do_unlink=True)
me.calc_loop_triangles();d=json.loads((O/'head.json').read_text())
d['triangles']=[];d['normals']=[];d['uv']=[];d['triangle_materials']=[]
for t in me.loop_triangles:
    order=list(t.loops)[::-1];d['triangles'].append(list(t.vertices)[::-1])
    d['normals'].append([list(me.corner_normals[k].vector) for k in order])
    d['uv'].append([[me.uv_layers.active.data[k].uv.x,1-me.uv_layers.active.data[k].uv.y] for k in order]);d['triangle_materials'].append(t.material_index)
(O/'head.json').write_text(json.dumps(d,separators=(',',':')),encoding='utf-8')
bpy.ops.wm.save_as_mainfile(filepath=str(O/'Nun_Head_Hair_R2.blend'))
(O/'orientation_repair.json').write_text(json.dumps({'flipped_faces_restored':flipped,'split_normals':'Interpolated original Meshy corner normals; native neck normals retained','uv_and_skin_weights_preserved':True},indent=2),encoding='utf-8')
print('HEAD_ORIENTATION_RESTORED',flipped,flush=True)
