"""Cosmetic M870 extension: current native cap/UV, continuous tube and collar."""
import bpy, bmesh, json, math, hashlib
from pathlib import Path
from mathutils import Vector

O=Path(__file__).parent;P=O.parents[1]
SOURCE=P/'SourceAssets/M870CommonFurniture20261016/Inputs/Native_Edit.blend'
NATIVE=P/'Content/Weapons/M870/Tactical20261015/SK_M870_V7.uasset'
HOST=P/'SourceAssets/M870TacticalFit20261017/inputs.json'
known_hashes={json.loads(HOST.read_text())['host_sha256']}
if (O/'import_receipt.json').exists():
    known_hashes.add(json.loads((O/'import_receipt.json').read_text()).get('native_cap',{}).get('saved_sha256'))
if hashlib.sha256(NATIVE.read_bytes()).hexdigest() not in known_hashes:
    raise RuntimeError('Native changed since the measured geometry; refresh the authoring source first')
bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
bpy.context.scene.unit_settings.system='METRIC';bpy.context.scene.unit_settings.scale_length=1.0
source=next(o for o in bpy.context.scene.objects if o.type=='MESH' and any(m and 'M870' in m.name for m in o.data.materials))
cap=bmesh.new();cap.from_mesh(source.data)
selected=[f for f in cap.faces if all(v.co.y>=.46 and -.774<v.co.z<-.747 for v in f.verts)]
if len(selected)!=24:raise RuntimeError('Native tube cap selection differs: '+str(len(selected)))
bmesh.ops.delete(cap,geom=[f for f in cap.faces if f not in set(selected)],context='FACES')
bmesh.ops.remove_doubles(cap,verts=list(cap.verts),dist=1e-7)
base=cap.copy();cap.free()
for obj in list(bpy.data.objects):bpy.data.objects.remove(obj,do_unlink=True)
coat=bpy.data.materials.new('M870_ExtTube_Coat');native=bpy.data.materials.new('M870_ExtTube_NativeCap')
for mat in (coat,native):
    mat.diffuse_color=(.012,.012,.012,1);mat.use_nodes=True
    shader=next((n for n in mat.node_tree.nodes if n.type=='BSDF_PRINCIPLED'),None) or mat.node_tree.nodes.new('ShaderNodeBsdfPrincipled')
    output=next((n for n in mat.node_tree.nodes if n.type=='OUTPUT_MATERIAL'),None) or mat.node_tree.nodes.new('ShaderNodeOutputMaterial')
    mat.node_tree.links.new(shader.outputs['BSDF'],output.inputs['Surface'])
    shader.inputs['Base Color'].default_value=(.012,.012,.012,1);shader.inputs['Roughness'].default_value=.416
group=bpy.data.objects.new('SM_M870_ExtendedTube_LODGroup',None);group['fbx_type']='LodGroup';bpy.context.collection.objects.link(group)
delta=.1653;centre_z=-.7602509
original_tip=sum(v.co.y for v in base.verts)/len(base.verts);tip=original_tip+delta
profile=[(.4500,.01190),(.4510,.01270),(.4640,.01270),(.4660,.011953),
         (tip-.0080,.011953),(tip-.0075,.01210),(tip-.0040,.01210),(tip-.0035,.011953),
         (tip-.0025,.011953)]
receipt={'source_native':str(NATIVE),'native_sha256':hashlib.sha256(NATIVE.read_bytes()).hexdigest(),
         'source_cap_blend':str(SOURCE),'extension_cm':delta*100,'native_cap_faces':24,
         'original_tip_forward_cm':original_tip*100,'new_tip_forward_cm':tip*100,
         'centre_z_cm':centre_z*100,'capacity_delta':3,'lods':[],'runtime_tested':False}
for level,cuts in enumerate((3,1,0)):
    bm=base.copy()
    for v in bm.verts:v.co.y+=delta
    for f in bm.faces:f.material_index=1;f.smooth=False
    boundary=[e for e in bm.edges if e.is_boundary]
    if cuts:bmesh.ops.subdivide_edges(bm,edges=boundary,cuts=cuts,use_grid_fill=False)
    rim=list({v for e in bm.edges if e.is_boundary for v in e.verts})
    rim.sort(key=lambda v:math.atan2(v.co.z-centre_z,v.co.x))
    n=len(rim);angles=[math.atan2(v.co.z-centre_z,v.co.x) for v in rim]
    uv=bm.loops.layers.uv.active or bm.loops.layers.uv.new('UVMap')
    rings=[]
    for y,radius in profile:
        rings.append([bm.verts.new((math.cos(a)*radius,y,centre_z+math.sin(a)*radius)) for a in angles])
    rings.append(rim)
    # The last ring is the exact native cap boundary, including its bevel facet spacing.
    for j in range(len(rings)-1):
        for i in range(n):
            ii=(i+1)%n
            f=bm.faces.new((rings[j][i],rings[j][ii],rings[j+1][ii],rings[j+1][i]));f.material_index=0;f.smooth=True
            for loop,uvco in zip(f.loops,((i/n,j/(len(rings)-1)),((i+1)/n,j/(len(rings)-1)),((i+1)/n,(j+1)/(len(rings)-1)),(i/n,(j+1)/(len(rings)-1)))):
                loop[uv].uv=uvco
    back=bm.verts.new((0,profile[0][0],centre_z))
    for i in range(n):
        f=bm.faces.new((back,rings[0][(i+1)%n],rings[0][i]));f.material_index=0;f.smooth=False
        for loop in f.loops:loop[uv].uv=(.5+loop.vert.co.x/.03,.5+(loop.vert.co.z-centre_z)/.03)
    bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
    bmesh.ops.triangulate(bm,faces=list(bm.faces))
    mesh=bpy.data.meshes.new('M870_ExtendedTube_LOD'+str(level));bm.to_mesh(mesh);bm.free()
    mesh.materials.append(coat);mesh.materials.append(native);mesh.update()
    obj=bpy.data.objects.new('SM_M870_ExtendedTube_LOD'+str(level),mesh);bpy.context.collection.objects.link(obj);obj.parent=group
    receipt['lods'].append({'level':level,'segments':n,'triangles':len(mesh.polygons)})
base.free()
out=O/'Exports';out.mkdir(exist_ok=True)
bpy.ops.wm.save_as_mainfile(filepath=str(O/'M870_ExtendedTube.blend'))
bpy.ops.object.select_all(action='SELECT')
bpy.ops.export_scene.fbx(filepath=str(out/'SM_M870_ExtendedTube_Lods.fbx'),use_selection=True,
    object_types={'MESH','EMPTY'},axis_forward='-Y',axis_up='Z',bake_anim=False,
    add_leaf_bones=False,mesh_smooth_type='FACE',use_tspace=True)
(O/'authoring_receipt.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
print('M870_EXTENSION_AUTHORED',json.dumps(receipt['lods']),flush=True)
