"""Boot-specific distance LOD policy, also used by future reimports."""
import hashlib,json,shutil,sys
from pathlib import Path
import unreal as u
sys.path.insert(0,str(Path(__file__).parent))
from boot_paths import P,R,DEST,read,write
REVISION='boots-distance-v1';RATIOS=(1.,.45,.18);SCREENS=(1.,.18,.075)
E=u.EditorAssetLibrary;G=u.GeometryScript_AssetUtils;Q=u.GeometryScript_MeshQueries;L=u.GeometryScript_List
def geometry(mesh,lod):
    spec=u.GeometryScriptMeshReadLOD(lod_type=u.GeometryScriptLODType.RENDER_DATA,lod_index=lod)
    dm,status=G.copy_mesh_from_skeletal_mesh(mesh,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(),spec)
    if status!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Cannot read LOD '+str(lod))
    _,vs,_=Q.get_all_vertex_positions(dm,False);_,fs,_=Q.get_all_triangle_indices(dm,False)
    ps=[[v.x,v.y,v.z] for v in L.convert_vector_list_to_array(vs)];ts=[[v.x,v.y,v.z] for v in L.convert_triangle_list_to_array(fs)]
    return dm,dict(vertices=len(ps),triangles=len(ts),geometry_sha256=hashlib.sha256(json.dumps([ps,ts],separators=(',',':')).encode()).hexdigest())
def apply(mesh):
    if not mesh.get_path_name().startswith(DEST+'/ue_leather_boots/'):raise RuntimeError('Outside tailored boot scope')
    author_sha=E.get_metadata_tag(mesh,'GarmentSleeveSHA')
    if E.get_metadata_tag(mesh,'BootDistanceLODRevision')==REVISION and E.get_metadata_tag(mesh,'BootDistanceAuthorSHA')==author_sha:return
    sub=u.get_editor_subsystem(u.SkeletalMeshEditorSubsystem);before_lods=[geometry(mesh,lod)[1] for lod in range(3)];before=before_lods[0]
    disk=P/'Content'/(mesh.get_path_name().split('.')[0][6:]+'.uasset');backup=R/'Audit/DistanceLODs/Before'/disk.relative_to(P)
    if not backup.exists():backup.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(disk,backup)
    path=mesh.get_path_name().split('.')[0]+'_DistanceLODPolicy';factory=u.DataAssetFactory();factory.set_editor_property('data_asset_class',u.SkeletalMeshLODSettings)
    policy=u.load_asset(path) or u.AssetToolsHelpers.get_asset_tools().create_asset(path.rsplit('/',1)[1],path.rsplit('/',1)[0],u.SkeletalMeshLODSettings,factory)
    groups=[]
    for ratio,screen in zip(RATIOS,SCREENS):
        group=u.SkeletalMeshLODGroupSettings();settings=group.get_editor_property('reduction_settings')
        for key,value in dict(num_of_triangles_percentage=ratio,num_of_vert_percentage=ratio,base_lod=0,max_bones_per_vertex=8,lock_edges=True,lock_color_bounaries=False,enforce_bone_boundaries=True,merge_coincident_vert_bones=True,welding_threshold=0.,recalc_normals=False).items():settings.set_editor_property(key,value)
        group.set_editor_property('reduction_settings',settings);group.set_editor_property('screen_size',u.PerPlatformFloat(default=screen));groups.append(group)
    policy.set_editor_property('lod_groups',groups);assert E.save_loaded_asset(policy,False)
    mesh.set_editor_property('lod_settings',policy);models=list(mesh.get_editor_property('source_models'))
    for i,model in enumerate(models):model.set_editor_property('reduction_settings',groups[min(i,2)].get_editor_property('reduction_settings'))
    mesh.set_editor_property('source_models',models)
    if not sub.regenerate_lod(mesh,3,True,False):raise RuntimeError('Distance LOD generation failed')
    for lod in range(3):
        build=sub.get_lod_build_settings(mesh,lod);build.set_editor_property('use_full_precision_u_vs',True);sub.set_lod_build_settings(mesh,lod,build)
    rows=[geometry(mesh,lod)[1] for lod in range(3)]
    assert rows[0]==before,'LOD0 must remain identical'
    assert rows[2]['triangles']<rows[1]['triangles']<rows[0]['triangles'],rows
    E.set_metadata_tag(mesh,'BootDistanceLODRevision',REVISION);E.set_metadata_tag(mesh,'BootDistanceAuthorSHA',author_sha);assert E.save_loaded_asset(mesh,False)
    receipt=R/'Audit/DistanceLODs/saved.json';data=read(receipt) if receipt.exists() else dict(revision=REVISION,meshes={},rendered=False)
    data['meshes'][mesh.get_path_name()]=dict(lods=rows,before_lods=before_lods,policy=policy.get_path_name(),ratios=RATIOS,screens=SCREENS,lod0_unchanged=True,backup=str(backup));write(receipt,data)
    print('BOOT_DISTANCE_LODS_SAVED',mesh.get_path_name(),[r['triangles'] for r in rows],flush=True)
def main():
    if '-run=' not in u.SystemLibrary.get_command_line().lower():
        ed=u.get_editor_subsystem(u.LevelEditorSubsystem)
        if ed and ed.is_in_play_in_editor():raise RuntimeError('End PIE before updating boot LODs')
    saved=read(R/'saved_assets.json')
    for profile in ('Jason','Jason_RobeInner'):apply(u.load_asset(saved['saved']['ue_leather_boots/'+profile]['asset']))
if __name__=='__main__':main()
