"""Add an articulated lower jaw and oral geometry to the authored Meshy dog."""
import bpy, bmesh, json, math
from pathlib import Path
from mathutils import Vector

ROOT=Path(__file__).resolve().parents[2]
BASE=ROOT/'SourceAssets/InfectedDogMeshy20260924'
OUT=BASE/'CompletionV2'
OUT.mkdir(exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(BASE/'LocalRig/InfectedDog_Meshy_LocalRigV1.blend'))
rig=next(o for o in bpy.context.scene.objects if o.type=='ARMATURE')
body=next(o for o in bpy.context.scene.objects if o.type=='MESH')
rig.name='Armature'
body.name='SK_InfectedDog_MeshyV2'
bpy.ops.object.select_all(action='DESELECT')
rig.select_set(True);bpy.context.view_layer.objects.active=rig
bpy.ops.object.mode_set(mode='EDIT')
jaw=rig.data.edit_bones.new('jaw')
jaw.head=(0,-.594,.744);jaw.tail=(0,-.755,.709)
jaw.parent=rig.data.edit_bones['head'];jaw.align_roll(Vector((1,0,0)))
# A bone alias preserves the existing native Wolf attack-origin contract.
socket=rig.data.edit_bones.new('Wolf_-Head')
socket.head=rig.data.edit_bones['head'].head
socket.tail=socket.head+Vector((0,-.025,0))
socket.parent=rig.data.edit_bones['head'];socket.use_deform=False
bpy.ops.object.mode_set(mode='OBJECT')
rig.data.collections['Head and Neck'].assign(rig.data.bones['jaw'])
rig.data.collections['Head and Neck'].assign(rig.data.bones['Wolf_-Head'])
head_group=body.vertex_groups['head'].index
jaw_group=body.vertex_groups.new(name='jaw').index

# Split only the lip arc. The posterior cheek remains connected so its skin
# bends around the hinge. BMesh interpolates UV and deformation layers at cuts.
bm=bmesh.new();bm.from_mesh(body.data)
normals=bm.loops.layers.float_vector.new('PreservedCornerNormal')
bm.faces.ensure_lookup_table()
for f,p in zip(bm.faces,body.data.polygons):
    for loop,li in zip(f.loops,p.loop_indices):loop[normals]=body.data.corner_normals[li].vector
deform=bm.verts.layers.deform.verify()
def roi():
    faces=[f for f in bm.faces if any(v.co.y<-.53 and v.co.z>.62 for v in f.verts)]
    edges={e for f in faces for e in f.edges};verts={v for f in faces for v in f.verts}
    return list(verts)+list(edges)+faces
bmesh.ops.bisect_plane(bm,geom=roi(),dist=1e-7,plane_co=(0,-.605,0),plane_no=(0,1,0))
plane=Vector((0,-.12,1));point=Vector((0,-.72,.724))
bmesh.ops.bisect_plane(bm,geom=roi(),dist=1e-7,plane_co=point,plane_no=plane)
def distance(co):return (co-point).dot(plane)
seam=[e for e in bm.edges if all(abs(distance(v.co))<2e-6 and v.co.y<=-.605+1e-6 for v in e.verts)]
if len(seam)<8:raise RuntimeError('Mouth authoring plane did not form the required lip arc')
adj={}
for e in seam:
    a,b=e.verts;adj.setdefault(a,[]).append(b);adj.setdefault(b,[]).append(a)
ends=[v for v,nb in adj.items() if len(nb)==1]
if len(ends)!=2:raise RuntimeError('Lip arc is not a single continuous open chain')
ordered=[min(ends,key=lambda v:v.co.x)];previous=None
while True:
    nxt=[v for v in adj[ordered[-1]] if v is not previous]
    if not nxt:break
    previous=ordered[-1];ordered.append(nxt[0])
arc=[v.co.copy() for v in ordered]
bmesh.ops.split_edges(bm,edges=seam)
for vert in bm.verts:
    co=vert.co
    # Coplanar seam duplicates are classified by the attached exterior faces.
    d=sum(distance(f.calc_center_median()) for f in vert.link_faces)/max(1,len(vert.link_faces))
    if co.y<-.578 and d<0 and co.z>.62:
        t=max(0,min(1,(-co.y-.578)/(.642-.578)))
        amount=t*t*(3-2*t)
        w=vert[deform]
        for key in list(w.keys()):w[key]*=1-amount
        w[jaw_group]=amount
        keep=sorted(w.items(),key=lambda pair:pair[1],reverse=True)[:4]
        total=sum(value for _,value in keep)
        for key in list(w.keys()):del w[key]
        for key,value in keep:
            if value>1e-7:w[key]=value/total

# Triangulate only new ngons; all unaffected quads remain editable.
bmesh.ops.triangulate(bm,faces=[f for f in bm.faces if len(f.verts)>4])
custom=[loop[normals].normalized() for f in bm.faces for loop in f.loops]
bm.to_mesh(body.data);bm.free()
body.data.normals_split_custom_set(custom)

def material(name,color,roughness):
    m=bpy.data.materials.new(name);m.diffuse_color=(*color,1);m.use_nodes=True
    m.node_tree.nodes.clear()
    p=m.node_tree.nodes.new('ShaderNodeBsdfPrincipled')
    output=m.node_tree.nodes.new('ShaderNodeOutputMaterial')
    m.node_tree.links.new(p.outputs['BSDF'],output.inputs['Surface'])
    p.inputs['Base Color'].default_value=(*color,1)
    p.inputs['Roughness'].default_value=roughness
    return m
tissue=material('M_InfectedDog_OralTissue',(.11,.018,.023),.32)
teeth=material('M_InfectedDog_Teeth',(.68,.60,.44),.3)
parts=[]
def bind(ob,bone,mat):
    ob.data.materials.clear();ob.data.materials.append(mat)
    if not ob.data.uv_layers:
        uv=ob.data.uv_layers.new(name='UVMap')
        for p in ob.data.polygons:
            drop=max(range(3),key=lambda i:abs(p.normal[i]))
            axes=[i for i in range(3) if i!=drop]
            for li in p.loop_indices:
                co=ob.data.vertices[ob.data.loops[li].vertex_index].co
                uv.data[li].uv=(co[axes[0]]*10,co[axes[1]]*10)
    group=ob.vertex_groups.new(name=bone);group.add(list(range(len(ob.data.vertices))),1.,'REPLACE')
    ob.parent=rig
    mod=ob.modifiers.new('Canine Skinning','ARMATURE');mod.object=rig
    for p in ob.data.polygons:p.use_smooth=True
    parts.append(ob)
def shell(name,lower):
    # Paired lip rings extend inward, with a recessed palate/floor and throat.
    ring=arc+[Vector((0,-.583,.740))]
    verts=[tuple(v) for v in ring]
    shift=-.010 if lower else .007
    for v in ring:
        verts.append((v.x*.78,v.y*.88+(-.65)*.12,v.z+shift))
    verts.append((0,-.665,.724+shift))
    count=len(ring);center=2*count;faces=[]
    for i in range(count):
        j=(i+1)%count
        faces.extend([(i,j,j+count,i+count),(i+count,j+count,center)])
    mesh=bpy.data.meshes.new(name);mesh.from_pydata(verts,[],faces);mesh.update()
    ob=bpy.data.objects.new(name,mesh);bpy.context.scene.collection.objects.link(ob)
    bm=bmesh.new();bm.from_mesh(mesh);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
    bm.to_mesh(mesh);bm.free()
    # Normals face the mouth cavity, not through the outer skin.
    average=sum(p.normal.z for p in mesh.polygons)
    if (average<0)==lower:
        bm=bmesh.new();bm.from_mesh(mesh);bmesh.ops.reverse_faces(bm,faces=list(bm.faces));bm.to_mesh(mesh);bm.free()
    bind(ob,'jaw' if lower else 'head',tissue)
shell('LowerMouth_FloorAndGum',True);shell('UpperMouth_PalateAndGum',False)
def tooth(name,center,radius,length,lower,bone):
    # Tapered tooth with curved tip, eight sides and three rings.
    verts=[];faces=[];direction=1 if lower else -1
    for t,r in [(0,1),(.45,.7),(.8,.3)]:
        for i in range(8):
            a=2*math.pi*i/8
            verts.append((center[0]+radius*r*math.cos(a),center[1]+radius*r*math.sin(a)+t*t*.002,center[2]+direction*length*t))
    verts.append((center[0],center[1]+.003,center[2]+direction*length))
    for j in range(2):
        for i in range(8):faces.append((j*8+i,j*8+(i+1)%8,(j+1)*8+(i+1)%8,(j+1)*8+i))
    for i in range(8):faces.append((16+i,16+(i+1)%8,24))
    faces.append(tuple(reversed(range(8))))
    mesh=bpy.data.meshes.new(name);mesh.from_pydata(verts,[],faces);mesh.update()
    ob=bpy.data.objects.new(name,mesh);bpy.context.scene.collection.objects.link(ob)
    bm=bmesh.new();bm.from_mesh(mesh);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(mesh);bm.free()
    bind(ob,bone,teeth)
for lower in [False,True]:
    bone='jaw' if lower else 'head';d=-1 if lower else 1
    for side in [-1,1]:
        tooth('Canine',(.037*side,-.706 if lower else -.72,.724+d*.006),.0045,.015 if lower else .022,lower,bone)
        for k in range(5):
            y=-.633-k*.013;x=(.039+(.706+y)*.10)*side
            z=.724+.12*(y+.72)+d*.005
            tooth('Premolar', (x,y,z),.004,.008,lower,bone)
    for k in range(6):
        x=(k-2.5)*.008
        tooth('Incisor',(x,-.753+abs(x)*.25,.72+d*.004),.0027,.0065,lower,bone)
bpy.ops.mesh.primitive_uv_sphere_add(segments=20,ring_count=10,location=(0,-.671,.713))
tongue=bpy.context.object;tongue.name='Tongue';tongue.scale=(.018,.042,.0035)
bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
bind(tongue,'jaw',tissue)

# Join the authored oral surfaces into the same skinned export and keep only
# three material slots. This retains each part's head/jaw vertex weights.
bpy.ops.object.select_all(action='DESELECT');body.select_set(True)
for ob in parts:ob.select_set(True)
bpy.context.view_layer.objects.active=body
bpy.ops.object.join()
# New tooth-root caps can have more than four sides. Preserve the corner-normal
# layer while triangulating those caps for valid glTF tangent generation.
bm=bmesh.new();bm.from_mesh(body.data)
nl=bm.loops.layers.float_vector.new('ExportCornerNormal')
for f,p in zip(bm.faces,body.data.polygons):
    for loop,li in zip(f.loops,p.loop_indices):loop[nl]=body.data.corner_normals[li].vector
bmesh.ops.triangulate(bm,faces=[f for f in bm.faces if len(f.verts)>4])
normals_out=[loop[nl].normalized() for f in bm.faces for loop in f.loops]
bm.to_mesh(body.data);bm.free();body.data.normals_split_custom_set(normals_out)
# The lip cuts interpolate existing groups. Trim the resulting seam vertices
# too, so the added geometry obeys the same four-influence delivery budget.
bpy.ops.object.vertex_group_limit_total(limit=4)
bpy.ops.object.vertex_group_normalize_all(lock_active=False)
body['closed_mouth']='Articulated jaw, split lip arc, mouth lining, tongue and 36 teeth'
rig['animation_compatibility']='Fitted Meshy skeleton V2 with jaw and native Wolf head alias'
# Material images remain packed; use new local paths for a self-contained file.
texdir=OUT/'Textures';texdir.mkdir(exist_ok=True)
for node in body.data.materials[0].node_tree.nodes:
    if node.type=='TEX_IMAGE' and node.image:
        im=node.image;im.filepath_raw=str(texdir/(im.name.replace('.png','')+'.png'));im.save();im.pack()
        im.filepath='//Textures/'+Path(im.filepath_raw).name
bpy.ops.object.select_all(action='DESELECT');body.select_set(True);rig.select_set(True)
bpy.context.view_layer.objects.active=rig
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'InfectedDog_MeshyV2.blend'))
bpy.ops.export_scene.fbx(filepath=str(OUT/'SK_InfectedDog_MeshyV2.fbx'),use_selection=True,
    object_types={'ARMATURE','MESH'},add_leaf_bones=False,bake_anim=False,
    use_armature_deform_only=False,axis_forward='-Y',axis_up='Z',apply_unit_scale=True,
    apply_scale_options='FBX_SCALE_NONE',use_mesh_modifiers=False,mesh_smooth_type='FACE',
    path_mode='COPY',embed_textures=True)
bpy.ops.export_scene.gltf(filepath=str(OUT/'SK_InfectedDog_MeshyV2.glb'),export_format='GLB',
    use_selection=True,export_animations=False,export_skins=True,export_def_bones=False,
    export_yup=True,export_normals=True,export_tangents=True,export_morph=False)
receipt={'stage':'mouth_and_jaw_authored','bones':len(rig.data.bones),'lip_arc_vertices':len(arc),
    'vertices':len(body.data.vertices),'polygons':len(body.data.polygons),
    'materials':[m.name for m in body.data.materials],'jaw_hinge_m':[0,-.594,.744],
    'source':'LocalRig V1 Meshy body; new local oral surfaces','mouth_interior':True,
    'independent_jaw':True,'max_influences':4,'runtime_tested':False,'rendered':False}
(OUT/'mouth_authoring.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
print('MESHY_MOUTH_SAVED',json.dumps(receipt),flush=True)
