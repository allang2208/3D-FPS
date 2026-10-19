"""Save the repaired native sleeve family to isolated packages, then publish."""
import json,hashlib,gc,sys,runpy
from pathlib import Path
import unreal as u
P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/GarmentSleeveRepair20261018';DEST='/Game/Characters/ModularOutfit20260924/GarmentSleeveRepair20261018'
E=u.EditorAssetLibrary;A=u.AssetToolsHelpers.get_asset_tools();L=u.MaterialEditingLibrary;G=u.GeometryScript_AssetUtils;B=u.GeometryScript_BoneWeights;S=u.get_editor_subsystem(u.SkeletalMeshEditorSubsystem)
receipt_path=R/'saved_assets.json';receipt=json.loads(receipt_path.read_text()) if receipt_path.exists() else dict(saved={},runtime_tested=False)
receipt['saved']={k:v for k,v in receipt['saved'].items() if '/' in k}
def record():receipt_path.write_text(json.dumps(receipt,indent=2),encoding='utf-8')
def load(path):
    asset=u.load_asset(path)
    if not asset:raise RuntimeError('Missing production input '+path)
    return asset
def save(asset):
    if not asset.get_path_name().startswith(DEST+'/'):raise RuntimeError('Outside sleeve repair scope')
    asset.modify()
    if not E.save_loaded_asset(asset,False):raise RuntimeError('Cannot save '+asset.get_path_name())
def dynamic(d,ref):
    _,bones=B.get_all_bones_info(ref);ids={str(b.name):b.index for b in bones};ps=[];ns=[];uv=[];ws=[];cs=[];fs=[];lookup={}
    for fi,face in enumerate(d['triangles']):
        tri=[]
        for ci,vi in enumerate(face):
            normal=d['normals'][fi][ci];tex=d['uv'][fi][ci];color=d['colors'][vi] if d.get('colors') else [1.,1.,1.,1.];key=(vi,*[round(x,7) for x in normal+tex+color])
            if key not in lookup:lookup[key]=len(ps);ps.append(u.Vector(*d['positions'][vi]));ns.append(u.Vector(*normal));uv.append(u.Vector2D(*tex));ws.append(d['weights'][vi]);cs.append(u.LinearColor(*color))
            tri.append(lookup[key])
        fs.append(u.IntVector(*tri))
    dm=u.DynamicMesh();u.GeometryScript_MeshEdits.append_buffers_to_mesh(dm,u.GeometryScriptSimpleMeshBuffers(vertices=ps,normals=ns,uv0=uv,vertex_colors=cs,triangles=fs),0,True)
    if dm.get_triangle_count()!=len(fs):raise RuntimeError('Rejected triangles '+d['profile'])
    B.copy_bones_from_mesh(ref,dm);B.mesh_create_bone_weights(dm)
    for i,bindings in enumerate(ws):
        _,ok=B.set_vertex_bone_weights(dm,i,[u.GeometryScriptBoneWeight(bone_index=ids[n],weight=w) for n,w in bindings.items()])
        if not ok:raise RuntimeError('Missing weight '+d['profile'])
    for i,slot in enumerate(d['triangle_materials']):u.GeometryScript_Materials.set_triangle_material_id(dm,i,slot,True)
    return dm
def write_mesh(row):
    profile=row['profile'];item=row['item'];route_key=item+'/'+profile
    file=R/'Authored'/item/(profile+'.json');raw=file.read_bytes();sha=hashlib.sha256(raw).hexdigest()
    path=DEST+'/'+item+'/'+profile+'/SK_'+profile+'_'+item
    old=json.loads(Path(row['file']).read_text());mats=[load(p) for p in old['materials']]
    asset=u.load_asset(path)
    d=json.loads(raw)
    if asset and E.get_metadata_tag(asset,'GarmentSleeveSHA')==sha:
        # Persist UE's post-load section normalization for the generated LODs.
        save(asset)
        receipt['saved'][route_key]=dict(asset=asset.get_path_name(),author_sha256=sha,native=d['binding_source'],triangles=len(d['triangles']),lod_count=S.get_lod_count(asset));record();print('GARMENT_SLEEVE_ALREADY_SAVED',route_key,flush=True);return
    source=load(d['binding_source']);ref,status=G.copy_mesh_from_skeletal_mesh(source,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD())
    if status!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Native source read failed '+profile)
    dm=dynamic(d,ref);asset=asset or A.duplicate_asset(path.rsplit('/',1)[1],path.rsplit('/',1)[0],source)
    opts=u.GeometryScriptCopyMeshToAssetOptions(replace_materials=True,new_materials=mats,new_material_slot_names=old['material_slots'],enable_recompute_normals=False,enable_recompute_tangents=True,bone_hierarchy_mismatch_handling=u.GeometryScriptBoneHierarchyMismatchHandling.REMAP_GEOMETRY_TO_REFERENCE_SKELETON)
    _,status=G.copy_mesh_to_skeletal_mesh(dm,asset,opts,u.GeometryScriptMeshWriteLOD())
    if status!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Mesh write failed '+profile)
    u.FPSModularOutfitComponent.configure_outfit_lods(asset);factory=u.DataAssetFactory();factory.set_editor_property('data_asset_class',u.SkeletalMeshLODSettings);policy=u.load_asset(path+'_LODPolicy') or A.create_asset(path.rsplit('/',1)[1]+'_LODPolicy',path.rsplit('/',1)[0],u.SkeletalMeshLODSettings,factory);groups=[]
    for screen in (1.,.18,.075):
        group=u.SkeletalMeshLODGroupSettings();settings=group.get_editor_property('reduction_settings')
        for key,value in dict(num_of_triangles_percentage=1.,num_of_vert_percentage=1.,max_bones_per_vertex=8,lock_edges=True,enforce_bone_boundaries=True,merge_coincident_vert_bones=False,welding_threshold=0.,recalc_normals=False).items():settings.set_editor_property(key,value)
        group.set_editor_property('reduction_settings',settings);group.set_editor_property('screen_size',u.PerPlatformFloat(default=screen));groups.append(group)
    policy.set_editor_property('lod_groups',groups);save(policy);asset.set_editor_property('lod_settings',policy);models=list(asset.get_editor_property('source_models'))
    for i,model in enumerate(models):model.set_editor_property('reduction_settings',groups[min(i,2)].get_editor_property('reduction_settings'))
    asset.set_editor_property('source_models',models)
    if not S.regenerate_lod(asset,3,True,False):raise RuntimeError('LOD save failed '+profile)
    asset.set_editor_property('physics_asset',None);E.set_metadata_tag(asset,'GarmentSleeveSHA',sha);E.set_metadata_tag(asset,'SourceContract',d['contract']);save(asset)
    receipt['saved'][route_key]=dict(asset=asset.get_path_name(),author_sha256=sha,native=d['binding_source'],triangles=len(d['triangles']),lod_count=S.get_lod_count(asset));record();print('GARMENT_SLEEVE_SAVED',route_key,flush=True)
def main():
    receipt['completed']=False;record()
    if '-run=' not in u.SystemLibrary.get_command_line().lower():
        level=u.get_editor_subsystem(u.LevelEditorSubsystem)
        if level and level.is_in_play_in_editor():raise RuntimeError('Do not replace clothing during PIE')
    rows=json.loads((R/'inventory.json').read_text())['rows']
    selected=[row for row in rows if row['item'] in ('ue_field_sweater','ue_chainmail_shirt') or row['profile'] in ('SVD','Super90')]
    for row in selected:
        file=R/'Authored'/row['item']/(row['profile']+'.json')
        if not file.exists():raise RuntimeError('Missing intended repair '+str(file))
        skin=json.loads(Path(row['native_file']).read_text())
        source=P/'Content'/(skin['source'].split('.')[0][6:]+'.uasset')
        if hashlib.sha256(source.read_bytes()).hexdigest()!=skin['asset_sha256']:raise RuntimeError('Native source changed after capture '+row['profile'])
    for row in selected:
        write_mesh(row);gc.collect();u.SystemLibrary.collect_garbage()
    receipt['completed']=True;record()
    runpy.run_path(str(P/'Tools/GarmentSleeveRepair/publish.py'),run_name='__main__')
    print('GARMENT_SLEEVES_SAVED_COMPLETE',len(selected),flush=True)
if __name__=='__main__':main()
