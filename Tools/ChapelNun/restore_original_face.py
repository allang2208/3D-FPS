"""Bind the untouched Meshy face to the existing nun; adapt only the lower neck."""
import bpy,json,math,struct,bisect
from pathlib import Path
from mathutils import Vector
from mathutils.kdtree import KDTree

P=Path('D:/FPS3D/FPSGAME');N=P/'SourceAssets/ChapelNun20261115'
R=N/'OriginalMeshyFaceR3';O=R/'Authored';S=R/'Source'
O.mkdir(parents=True,exist_ok=True);S.mkdir(exist_ok=True)
original=N/'MeshyHeadR1/Source/NunHead_R1_glb.glb'
raw=original.read_bytes();json_size,_=struct.unpack_from('<II',raw,12)
gltf=json.loads(raw[20:20+json_size]);bin_size,_=struct.unpack_from('<II',raw,20+json_size)
binary=raw[28+json_size:28+json_size+bin_size]
material=gltf['materials'][0];images={}
for name,texture_index in [('base_color',material['pbrMetallicRoughness']['baseColorTexture']['index']),('metallic_roughness',material['pbrMetallicRoughness']['metallicRoughnessTexture']['index']),('normal',material['normalTexture']['index'])]:
    entry=gltf['images'][gltf['textures'][texture_index]['source']];view=gltf['bufferViews'][entry['bufferView']]
    suffix='.jpg' if entry['mimeType']=='image/jpeg' else '.png';path=S/('MeshyOriginal_'+name+suffix)
    offset=view.get('byteOffset',0);path.write_bytes(binary[offset:offset+view['byteLength']]);images[name]=str(path)
(R/'original_material.json').write_text(json.dumps({'source':str(original),'material':material,'images':images},indent=2),encoding='utf-8')

native=json.loads((N/'ProductionR1/Inputs/native_head.json').read_text(encoding='utf-8-sig'))
bpy.ops.wm.open_mainfile(filepath=str(N/'HeadQualityR2/Authored/Nun_Head_Hair_R2.blend'))
head=bpy.data.objects['SK_NunHead'];old=head.data;old.calc_loop_triangles()
neck_material=old.materials[1];scalp_material=old.materials[4]
ring_ids={i for f in old.polygons if f.material_index==1 for i in f.vertices if abs(old.vertices[i].co.z-144.5)<.002}
ring=sorted([old.vertices[i].co.copy() for i in ring_ids],key=lambda p:math.atan2(p.y-1,p.x))
angles=[math.atan2(p.y-1,p.x) for p in ring]
def fit_neck(p):
    p=p.copy()
    if p.z>=149:return p
    theta=math.atan2(p.y-1,p.x);k=bisect.bisect_left(angles,theta);a=ring[(k-1)%len(ring)];b=ring[k%len(ring)]
    ta=angles[(k-1)%len(ring)];tb=angles[k%len(ring)]
    if tb<ta:tb+=math.tau
    if theta<ta:theta+=math.tau
    q=a.lerp(b,(theta-ta)/max(tb-ta,1e-6));t=max(0,min(1,(149-p.z)/4));t=t*t*(3-2*t)
    p.x=p.x*(1-t)+q.x*t;p.y=p.y*(1-t)+q.y*t;return p

native_ids=sorted({i for t,m in zip(native['triangles'],native['triangle_materials']) if m==0 for i in t})
tree=KDTree(len(native_ids))
for i,vi in enumerate(native_ids):tree.insert(native['positions'][vi],vi)
tree.balance()
def weights(p):
    accum={}
    for _,i,dist in tree.find_n(p,4):
        for bone,w in native['weights'][i]:accum[bone]=accum.get(bone,0)+w/max(dist,.03)**2
    pairs=sorted(accum.items(),key=lambda x:-x[1])[:8];total=sum(w for _,w in pairs)
    return [[bone,w/total] for bone,w in pairs]

before=set(bpy.data.objects);bpy.ops.import_scene.gltf(filepath=str(original))
source=next(o for o in bpy.data.objects if o not in before and o.type=='MESH')
bpy.ops.object.select_all(action='DESELECT');source.select_set(True);bpy.context.view_layer.objects.active=source
bpy.ops.object.transform_apply(location=True,rotation=True,scale=True)
mesh=source.data;mesh.calc_loop_triangles();original_material=mesh.materials[0]
offset_z=168.0523223876953-.94961101*15.8
source_positions=[Vector((v.co.x*15.8,-v.co.y*15.8+1.4,v.co.z*15.8+offset_z)) for v in mesh.vertices]
positions=[];bindings=[];triangles=[];uvs=[];normals=[];material_ids=[];lookup={}
def add_vertex(key,p,binding=None):
    if key not in lookup:
        lookup[key]=len(positions);positions.append(list(p));bindings.append(weights(p) if binding is None else binding)
    return lookup[key]
def append_face(vertices,face_uv,face_normals,mat):
    triangles.append(vertices);uvs.append(face_uv);normals.append(face_normals);material_ids.append(mat)

preserved_triangles=0;clipped_triangles=0
for triangle in mesh.loop_triangles:
    # Reflection changes handedness; reverse each triangle once, without recalculating source normals.
    polygon=[]
    for li in reversed(triangle.loops):
        vi=mesh.loops[li].vertex_index;n=mesh.corner_normals[li].vector
        polygon.append((('source',vi),source_positions[vi],Vector((n.x,-n.y,n.z)),mesh.uv_layers.active.data[li].uv.copy()))
    if all(v[1].z>=145 for v in polygon):preserved_triangles+=1
    else:
        clipped=[]
        for i,current in enumerate(polygon):
            previous=polygon[i-1];inside=current[1].z>=145;was_inside=previous[1].z>=145
            if inside!=was_inside:
                t=(145-previous[1].z)/(current[1].z-previous[1].z)
                key=('cut',*sorted((previous[0][1],current[0][1])))
                clipped.append((key,previous[1].lerp(current[1],t),previous[2].lerp(current[2],t).normalized(),previous[3].lerp(current[3],t)))
            if inside:clipped.append(current)
        polygon=clipped
        if polygon:clipped_triangles+=1
    for i in range(1,len(polygon)-1):
        corners=[polygon[0],polygon[i],polygon[i+1]]
        append_face([add_vertex(key,fit_neck(p)) for key,p,n,uv in corners],[list(uv) for key,p,n,uv in corners],[list(n) for key,p,n,uv in corners],0)

# Keep the existing native lower-neck interface and separate scalp foundation.
for t in old.loop_triangles:
    if t.material_index not in (1,4):continue
    ids=[]
    for vi in t.vertices:
        v=old.vertices[vi];ids.append(add_vertex(('retained',vi),v.co,[[g.group,g.weight] for g in v.groups]))
    append_face(ids,[list(old.uv_layers.active.data[i].uv) for i in t.loops],[list(old.corner_normals[i].vector) for i in t.loops],1 if t.material_index==1 else 2)

new=bpy.data.meshes.new('NunOriginalMeshyFace');new.from_pydata(positions,[],triangles);new.update()
for mat in (original_material,neck_material,scalp_material):new.materials.append(mat)
uv_layer=new.uv_layers.new(name='UVMap')
for face,face_uv,mat in zip(new.polygons,uvs,material_ids):
    face.material_index=mat;face.use_smooth=True
    for li,uv in zip(face.loop_indices,face_uv):uv_layer.data[li].uv=uv
new.normals_split_custom_set([n for face in normals for n in face]);head.data=new
head.vertex_groups.clear()
for bone in native['bones']:head.vertex_groups.new(name=bone['name'])
for vi,skin in enumerate(bindings):
    for bone,w in skin:head.vertex_groups[int(bone)].add([vi],w,'REPLACE')
for obj in list(bpy.data.objects):
    if obj not in before:bpy.data.objects.remove(obj,do_unlink=True)

data=dict(binding_source=native['source'],skeleton=native['skeleton'],bones=native['bones'],positions=positions,weights=bindings,
          triangles=[t[::-1] for t in triangles],uv=[[[u,1-v] for u,v in face[::-1]] for face in uvs],
          normals=[face[::-1] for face in normals],triangle_materials=material_ids,material_slots=['NunMeshyOriginal','NativeNeck','ScalpFoundation'])
(O/'head.json').write_text(json.dumps(data,separators=(',',':')),encoding='utf-8')
for image in bpy.data.images:
    if image.source=='FILE':image.pack()
bpy.ops.wm.save_as_mainfile(filepath=str(O/'Nun_OriginalMeshyFace_Hair.blend'))
report={'source':str(original),'face_source':'Original Meshy triangles, vertex positions, corner normals and UVs; no facial smoothing or sculpting',
        'neck_adaptation':'Existing native lower neck; fitting restricted below z=149 cm, cut at z=145 cm',
        'material':'Original embedded glTF PBR images, channels, factors and double-sided setting',
        'retained_hair':'HeadQualityR2 black low-bun grooms and scalp foundation',
        'source_triangles_retained':preserved_triangles,'lower_neck_triangles_clipped':clipped_triangles,
        'runtime_tested':False}
(R/'authoring.json').write_text(json.dumps(report,indent=2),encoding='utf-8')

# Package the restored face with the existing body, robe and groom authoring scene.
bpy.ops.wm.open_mainfile(filepath=str(N/'ProductionR1/Authored/ChapelNun_Complete_Source.blend'))
for obj in list(bpy.data.objects):
    if obj.name=='SK_NunHead' or obj.name.startswith('Nun_LowBun_'):bpy.data.objects.remove(obj,do_unlink=True)
with bpy.data.libraries.load(str(O/'Nun_OriginalMeshyFace_Hair.blend'),link=False) as (src,dst):
    dst.objects=[name for name in src.objects if name=='SK_NunHead' or name.startswith('Nun_LowBun_')]
rig=bpy.data.objects['Kaitlin_Nun_Rig']
for obj in dst.objects:
    bpy.context.scene.collection.objects.link(obj)
    if obj.name=='SK_NunHead':obj.modifiers.new('NativeBinding','ARMATURE').object=rig;obj.parent=rig
bpy.ops.wm.save_as_mainfile(filepath=str(O/'ChapelNun_Complete_OriginalFace.blend'))
print('ORIGINAL_MESHY_FACE_AUTHORED',preserved_triangles,clipped_triangles,flush=True)
