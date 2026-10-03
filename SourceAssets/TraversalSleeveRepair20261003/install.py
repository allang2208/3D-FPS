"""Build and save the isolated traversal chainmail repair, without running play."""
import json,sys
from pathlib import Path
import unreal as u
P=Path('D:/FPS3D/FPSGAME');R=Path(__file__).resolve().parent
sys.path.insert(0,str(P/'Tools/ModularOutfit'))
from garment_pipeline import read,write,digest,asset_file
from garment_ue import source_snapshot
if '-run=' not in u.SystemLibrary.get_command_line().lower() and u.EditorLevelLibrary.get_pie_worlds(False):
    raise RuntimeError('Stop PIE before saving the traversal sleeve')
d=read(R/'authored.json');before=read(R/'Before/ue_chainmail_shirt.json')
if digest(asset_file(before['source']))!=before['asset_sha256']:raise RuntimeError('Active source changed during authoring')
source=u.load_asset(before['source']);binding=u.load_asset(d['binding_source'])
native,_=source_snapshot(binding);B=u.GeometryScript_BoneWeights;G=u.GeometryScript_AssetUtils
_,bones=B.get_all_bones_info(native);ids={str(b.name):b.index for b in bones}
vertices=[];normals=[];uv=[];colors=[];weights=[];triangles=[];lookup={}
for fi,row in enumerate(d['triangles']):
    out=[]
    for ci,vi in enumerate(row):
        n=d['normals'][fi][ci];t=d['uv'][fi][ci]
        key=(vi,d['triangle_materials'][fi],*[round(v,7) for v in n+t])
        if key not in lookup:
            lookup[key]=len(vertices);vertices.append(u.Vector(*d['positions'][vi]));normals.append(u.Vector(*n))
            uv.append(u.Vector2D(*t));colors.append(u.LinearColor(*d['colors'][vi]));weights.append(d['weights'][vi])
        out.append(lookup[key])
    triangles.append(u.IntVector(*out))
dm=u.DynamicMesh()
u.GeometryScript_MeshEdits.append_buffers_to_mesh(dm,u.GeometryScriptSimpleMeshBuffers(
    vertices=vertices,normals=normals,uv0=uv,vertex_colors=colors,triangles=triangles),0,True)
if dm.get_triangle_count()!=len(triangles):raise RuntimeError('Unreal rejected authored triangles')
B.copy_bones_from_mesh(native,dm);B.mesh_create_bone_weights(dm)
for i,w in enumerate(weights):
    _,ok=B.set_vertex_bone_weights(dm,i,[u.GeometryScriptBoneWeight(bone_index=ids[n],weight=v) for n,v in w.items()])
    if not ok:raise RuntimeError('Cannot write native weights')
for i,m in enumerate(d['triangle_materials']):u.GeometryScript_Materials.set_triangle_material_id(dm,i,m,True)
destination='/Game/Characters/ModularOutfit20260924/TraversalSleeveRepair20261003/SK_Traversal_ChainmailShirt'
E=u.EditorAssetLibrary
asset=u.load_asset(destination) or E.duplicate_asset(binding.get_path_name(),destination)
slots=list(source.materials)
options=u.GeometryScriptCopyMeshToAssetOptions(replace_materials=True,
    new_materials=[m.material_interface for m in slots],new_material_slot_names=[m.material_slot_name for m in slots],
    enable_recompute_normals=False,enable_recompute_tangents=True,
    bone_hierarchy_mismatch_handling=u.GeometryScriptBoneHierarchyMismatchHandling.REMAP_GEOMETRY_TO_REFERENCE_SKELETON)
_,outcome=G.copy_mesh_to_skeletal_mesh(dm,asset,options,u.GeometryScriptMeshWriteLOD())
if outcome!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Cannot build traversal sleeve')
asset.set_editor_property('physics_asset',None)
subsystem=u.get_editor_subsystem(u.SkeletalMeshEditorSubsystem) or u.new_object(u.SkeletalMeshEditorSubsystem)
if not u.FPSModularOutfitComponent.configure_outfit_lods(asset):raise RuntimeError('Cannot configure sleeve LODs')
policy_path=destination+'_LODPolicy';policy=u.load_asset(policy_path)
if not policy:
    factory=u.DataAssetFactory();factory.set_editor_property('data_asset_class',u.SkeletalMeshLODSettings)
    policy=u.AssetToolsHelpers.get_asset_tools().create_asset(policy_path.rsplit('/',1)[1],policy_path.rsplit('/',1)[0],u.SkeletalMeshLODSettings,factory)
lods=[]
for i in range(3):
    info=u.SkeletalMeshLODGroupSettings();settings=info.get_editor_property('reduction_settings')
    for name,value in {'num_of_triangles_percentage':1.,'max_bones_per_vertex':8,'lock_edges':True,
        'enforce_bone_boundaries':True,'merge_coincident_vert_bones':False,'welding_threshold':0.,
        'improve_triangles_for_cloth':True}.items():settings.set_editor_property(name,value)
    info.set_editor_property('reduction_settings',settings)
    info.set_editor_property('screen_size',u.PerPlatformFloat(default=[1.,.2,.08][i]));lods.append(info)
policy.set_editor_property('lod_groups',lods)
if not E.save_loaded_asset(policy,False):raise RuntimeError('LOD policy save failed')
asset.set_editor_property('lod_settings',policy)
models=list(asset.get_editor_property('source_models'))
for i,model in enumerate(models):model.set_editor_property('reduction_settings',lods[i].get_editor_property('reduction_settings'))
asset.set_editor_property('source_models',models)
settings=subsystem.get_lod_build_settings(asset,0);settings.set_editor_property('use_full_precision_u_vs',True)
subsystem.set_lod_build_settings(asset,0,settings)
if not subsystem.regenerate_lod(asset,3,True,False):raise RuntimeError('Sleeve LOD build failed')
E.set_metadata_tag(asset,'SourceContract',d['contract']);E.set_metadata_tag(asset,'AuthorSource',str(R/'author.py'))
if not E.save_loaded_asset(asset,False):raise RuntimeError('Sleeve save failed')
write(R/'saved.json',{'asset':asset.get_path_name(),'asset_sha256':digest(asset_file(asset.get_path_name())),
    'author_sha256':digest(R/'authored.json'),'saved':True,'runtime_tested':False,
    'lod_policy':[1.,1.,1.],'max_bone_influences':8,'render_lods_read':False})
print('TRAVERSAL_CHAINMAIL_SAVED '+asset.get_path_name(),flush=True)
