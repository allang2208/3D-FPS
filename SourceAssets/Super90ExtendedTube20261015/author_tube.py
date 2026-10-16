"""Author the game exterior in native SUPER90 bind coordinates; preserve its cap."""
import bpy,bmesh,json,math
from pathlib import Path
from mathutils import Matrix
O=Path(__file__).parent;X=O/'Exports';X.mkdir(exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.context.preferences.filepaths.save_version=0
bpy.context.scene.unit_settings.system='METRIC';bpy.context.scene.unit_settings.scale_length=1
source=O.parent/'Super90Birdcage20261015/Preview/super90.fbx'
bpy.ops.import_scene.fbx(filepath=str(source),use_anim=False)
rows=json.loads((O/'native_components.json').read_text())
selected=[r for r in rows if r['min'][1]>.474 and r['max'][2]<-.757]
face_ids={i for r in selected for i in r['face_ids']}
if not face_ids:raise RuntimeError('Factory end-cap selection is empty')
host=bpy.data.objects[selected[0]['object']]
mesh=host.data;normals=[n.vector.copy() for n in mesh.corner_normals]
attr=mesh.attributes.new('PreservedCornerNormal','FLOAT_VECTOR','CORNER')
for value,normal in zip(attr.data,normals):value.vector=normal
bm=bmesh.new();bm.from_mesh(mesh)
bmesh.ops.delete(bm,geom=[f for f in bm.faces if f.index not in face_ids],context='FACES')
bmesh.ops.delete(bm,geom=[v for v in bm.verts if not v.link_faces],context='VERTS')
bm.to_mesh(mesh);bm.free()
normals=[tuple(v.vector.normalized()) for v in mesh.attributes['PreservedCornerNormal'].data]
for face in mesh.polygons:face.use_smooth=True
mesh.normals_split_custom_set(normals)
mesh.transform(host.matrix_world);host.parent=None;host.matrix_world=Matrix.Identity(4);host.modifiers.clear()
for v in mesh.vertices:v.co.y+=.165
for obj in list(bpy.data.objects):
    if obj!=host:bpy.data.objects.remove(obj,do_unlink=True)
host.name='Super90_ExtTube_NativeCap'
cap_material=mesh.materials[mesh.polygons[0].material_index].copy();cap_material.name='S90_ExtTube_NativeCap'
mesh.materials.clear();mesh.materials.append(cap_material)
for face in mesh.polygons:face.material_index=0

steel=bpy.data.materials.new('S90_ExtTube_Steel');steel.use_nodes=True
nodes=steel.node_tree.nodes;nodes.clear();bs=nodes.new('ShaderNodeBsdfPrincipled');out=nodes.new('ShaderNodeOutputMaterial')
steel.node_tree.links.new(bs.outputs[0],out.inputs['Surface'])
bs.inputs['Base Color'].default_value=(.034,.035,.037,1);bs.inputs['Roughness'].default_value=.42;bs.inputs['Metallic'].default_value=1

def select(objects):
    bpy.ops.object.select_all(action='DESELECT')
    for obj in objects:obj.select_set(True)
    bpy.context.view_layer.objects.active=objects[0]

def tube(n):
    # Cosmetic exterior only. The source cap keeps its original UV and normals.
    z=-.77279532
    profile=[(.4742,.01410),(.4748,.01414),(.4765,.01310),(.4898,.01310),
             (.494,.0122),(.501,.0107),(.507,.0100),(.621,.0100),
             (.633,.0125),(.6394,.01414),(.6400,.01414)]
    vertices=[(r*math.cos(j*math.tau/n),y,z+r*math.sin(j*math.tau/n)) for y,r in profile for j in range(n)]
    faces=[tuple(reversed(range(n)))]
    for k in range(len(profile)-1):
        for j in range(n):
            q=(j+1)%n;faces.append((k*n+j,k*n+q,(k+1)*n+q,(k+1)*n+j))
    faces.append(tuple((len(profile)-1)*n+j for j in range(n)))
    m=bpy.data.meshes.new('ExtendedTube_Shell');m.from_pydata(vertices,[],faces);m.materials.append(steel)
    bm=bmesh.new();bm.from_mesh(m);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(m);bm.free()
    for f in m.polygons:f.use_smooth=True
    m.set_sharp_from_angle(angle=math.radians(40))
    obj=bpy.data.objects.new('Super90_ExtendedTube_Shell',m);bpy.context.collection.objects.link(obj)
    select([obj]);bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.smart_project(angle_limit=math.radians(66),island_margin=.018);bpy.ops.object.mode_set(mode='OBJECT')
    obj.modifiers.new('Planar end normals','WEIGHTED_NORMAL').keep_sharp=True
    return obj

def export(parts,level):
    select(parts);bpy.ops.object.duplicate();copies=list(bpy.context.selected_objects)
    for obj in copies:select([obj]);bpy.ops.object.convert(target='MESH')
    select(copies);bpy.ops.object.join();obj=bpy.context.object;obj.name='SM_Super90_ExtendedTube_'+level
    tri=obj.modifiers.new('Export triangles','TRIANGULATE');bpy.ops.object.modifier_apply(modifier=tri.name)
    obj.data.calc_loop_triangles();count=len(obj.data.loop_triangles)
    fbx=X/(obj.name+'.fbx');glb=X/(obj.name+'.glb')
    bpy.ops.export_scene.fbx(filepath=str(fbx),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',bake_anim=False,add_leaf_bones=False,mesh_smooth_type='FACE',use_tspace=True)
    bpy.ops.export_scene.gltf(filepath=str(glb),use_selection=True,export_format='GLB',export_animations=False,export_tangents=True)
    bpy.data.objects.remove(obj,do_unlink=True)
    return {'triangles':count,'fbx':str(fbx),'glb':str(glb)}

body=tube(96);lods={'LOD0':export([host,body],'LOD0')}
for level,n in [('LOD1',48),('LOD2',24)]:
    low=tube(n);lods[level]=export([host,low],level);bpy.data.objects.remove(low,do_unlink=True)
select([host,body]);bpy.ops.wm.save_as_mainfile(filepath=str(O/'Super90_ExtendedTube_Editable.blend'))
report={'lods':lods,'source':str(source),'factory_cap_faces':len(face_ids),
    'cap_source_bounds':[[min(r['min'][k] for r in selected) for k in range(3)],[max(r['max'][k] for r in selected) for k in range(3)]],
    'cap_forward_offset_m':.165,'native_coordinates':True,'engine_imported':False,'runtime_tested':False}
(O/'authoring_receipt.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('SUPER90_EXTENDED_TUBE_AUTHORED',json.dumps(lods),flush=True)
