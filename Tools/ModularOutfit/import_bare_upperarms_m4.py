"""Build/save the V6 bare arms with V5 physical skin and native M4 binding."""
import hashlib,json
from pathlib import Path
import unreal as u

PROJECT=Path('D:/FPS3D/FPSGAME')
ROOT=PROJECT/'SourceAssets/ModularOutfit20260924/OriginalShapeBareM4/BareUpperArmsV6'
V5='/Game/Characters/ModularOutfit20260924/OriginalShapeBareM4SurfaceV5'
DEST='/Game/Characters/ModularOutfit20260924/OriginalShapeBareM4BareArmsV6'
E=u.EditorAssetLibrary;A=u.AssetToolsHelpers.get_asset_tools();L=u.MaterialEditingLibrary
G=u.GeometryScript_AssetUtils;B=u.GeometryScript_BoneWeights
if u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world():
    raise RuntimeError('Finish play before saving V6 bare-arm assets; original assets remain unchanged')
data_bytes=(ROOT/'M4_original.json').read_bytes();data=json.loads(data_bytes)
saved=[]
def load(path):
    asset=u.load_asset(path)
    if not asset:raise RuntimeError('Required asset missing: '+path)
    return asset
def save(asset):
    if not E.save_loaded_asset(asset,False):raise RuntimeError('Could not save '+asset.get_path_name())
    saved.append(asset.get_path_name())

parent=u.load_asset(DEST+'/M_M4FullBareArmSkin')
if not parent:parent=A.duplicate_asset('M_M4FullBareArmSkin',DEST,load(V5+'/M_M4UnifiedSkin_Forearm'))
custom=L.get_material_property_input_node(parent,u.MaterialProperty.MP_NORMAL)
if not isinstance(custom,u.MaterialExpressionCustom):
    raise RuntimeError('The V5 skin normal output is not its shared skin expression')
# All of the former sleeve now uses the same skin field as the exposed arm.
# Constant full coverage lets the compiler remove the old textile branch.
coverage=L.create_material_expression(parent,u.MaterialExpressionConstant4Vector)
coverage.set_editor_property('constant',u.LinearColor(1,1,0,0))
if not L.connect_material_expressions(coverage,'',custom,'Forearm'):
    raise RuntimeError('Cannot author full bare-arm skin coverage')
L.set_material_usage(parent,u.MaterialUsage.MATUSAGE_SKELETAL_MESH)
errors=L.recompile_material(parent)
if errors:raise RuntimeError('Bare-arm skin compilation failed: '+str(errors))
save(parent)
skin=u.load_asset(DEST+'/MI_M4FullBareArmSkin')
if not skin:skin=A.create_asset('MI_M4FullBareArmSkin',DEST,u.MaterialInstanceConstant,u.MaterialInstanceConstantFactoryNew())
L.set_material_instance_parent(skin,parent);L.update_material_instance(skin);save(skin)
hand_skin=load(V5+'/MI_M4UnifiedSkin_Hand')

source=load(data['source'])
native,result=G.copy_mesh_from_skeletal_mesh(source,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD())
if result!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Cannot read native reference skeleton')
_,bones=B.get_all_bones_info(native);bone_ids={str(b.name):b.index for b in bones}
vertices=[];normals=[];uvs=[];weights=[];triangles=[];lookup={}
for ti,face in enumerate(data['triangles']):
    row=[]
    for corner,vi in enumerate(face):
        uv=data['uv'][ti][corner];normal=data['normals'][ti][corner]
        key=(vi,*[round(v,7) for v in (*uv,*normal)])
        if key not in lookup:
            lookup[key]=len(vertices);vertices.append(u.Vector(*data['positions'][vi]))
            normals.append(u.Vector(*normal));uvs.append(u.Vector2D(*uv));weights.append(data['weights'][vi])
        row.append(lookup[key])
    triangles.append(u.IntVector(*row))
dm=u.DynamicMesh()
u.GeometryScript_MeshEdits.append_buffers_to_mesh(dm,u.GeometryScriptSimpleMeshBuffers(vertices=vertices,normals=normals,uv0=uvs,triangles=triangles),0,True)
B.copy_bones_from_mesh(native,dm);B.mesh_create_bone_weights(dm)
for vi,bindings in enumerate(weights):
    B.set_vertex_bone_weights(dm,vi,[u.GeometryScriptBoneWeight(bone_index=bone_ids[name],weight=w) for name,w in bindings.items()])
for ti,material in enumerate(data['triangle_materials']):u.GeometryScript_Materials.set_triangle_material_id(dm,ti,material,True)
mesh=u.load_asset(DEST+'/SK_M4_OriginalShape_BareHands')
if not mesh:mesh=A.duplicate_asset('SK_M4_OriginalShape_BareHands',DEST,load(V5+'/SK_M4_OriginalShape_BareHands'))
options=u.GeometryScriptCopyMeshToAssetOptions(replace_materials=True,new_materials=[skin,skin,hand_skin],
    new_material_slot_names=['BareUpperArms','BareLowerArms','BareHandsOriginalGrip'],
    enable_recompute_normals=False,enable_recompute_tangents=True,
    bone_hierarchy_mismatch_handling=u.GeometryScriptBoneHierarchyMismatchHandling.REMAP_GEOMETRY_TO_REFERENCE_SKELETON)
_,result=G.copy_mesh_to_skeletal_mesh(dm,mesh,options,u.GeometryScriptMeshWriteLOD())
if result!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Cannot write bare-arm geometry')
mesh.set_editor_property('physics_asset',None)
if not u.FPSModularOutfitComponent.configure_outfit_lods(mesh):raise RuntimeError('Cannot configure arm LODs')
if not u.get_editor_subsystem(u.SkeletalMeshEditorSubsystem).regenerate_lod(mesh,3,True,False):raise RuntimeError('Cannot build arm LODs')
E.set_metadata_tag(mesh,'SourceContract','V6 bare upperarms: V4 native weights/topology/grip; V5 unified physical skin; no animation changes')
save(mesh)

path=PROJECT/'Content/ColdSteelData/modular_outfits.json'
config=json.loads(path.read_text(encoding='utf-8-sig'));entry=config['profiles'][data['source']]
previous=entry['bare_arms_candidate'];entry['bare_arms_candidate']=mesh.get_path_name()
path.write_text(json.dumps(config,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
receipt={'mesh':mesh.get_path_name(),'previous_candidate':previous,'saved_assets':saved,
    'geometry_author_sha256':hashlib.sha256(data_bytes).hexdigest(),
    'material_source':V5+'/M_M4UnifiedSkin_Forearm','skin_coverage':'All upper and lower arm surfaces; no clothing mask',
    'physical_tile_cm':8,'preserved':['original skeleton and bind pose','all V4 vertex weights and face winding',
        'V4 distal forearms, wrists and hand grip','V5 hand material','original glove equipment restore path'],
    'scope':'M4 first-person bare-arm candidate without modular shirt/gloves',
    'runtime_tested':False,'visual_acceptance':'Pending user test'}
(ROOT/'saved.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('M4_BARE_UPPERARMS_V6_SAVED',mesh.get_path_name())
