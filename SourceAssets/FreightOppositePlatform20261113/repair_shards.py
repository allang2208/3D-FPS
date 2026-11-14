"""Remove only broken glaze islands and exposed white shard sides at this corner. The original tile bed receives the local spall."""
from pathlib import Path
import gzip,json
import unreal as u
R=Path(__file__).resolve().parent
def apply(w,req):
    api=u.get_editor_subsystem(u.EditorActorSubsystem) or u.new_object(u.EditorActorSubsystem)
    actors={a.get_actor_label():a for a in u.GameplayStatics.get_all_actors_of_class(w,u.Actor)}
    a=actors['StationLine_AbandonedTransitStation_6'];comp=a.static_mesh_component
    origin='/Game/Dungeons/TransitStation20260928/Meshes/SM_Station_Tiles'
    source=comp.static_mesh
    if source.get_name()!='SM_Station_Tiles':
        inputs=json.loads((R.parent/'FreightStationSurfaces20261113/done-01.json').read_text('utf8'))
        source=u.load_asset(next(i['mesh'] for i in inputs if i['label']==a.get_actor_label()))
    dst='/Game/SceneTests/FreightOppositePlatform20261113/Meshes/SM_StationTiles_WestRepair'
    lib=u.EditorAssetLibrary;clone=u.load_asset(dst) if lib.does_asset_exist(dst) else lib.duplicate_asset(source.get_path_name().split('.')[0],dst)
    mesh=u.DynamicMesh();lod=u.GeometryScriptMeshReadLOD();lod.lod_type=u.GeometryScriptLODType.SOURCE_MODEL
    u.GeometryScript_AssetUtils.copy_mesh_from_static_mesh(source,mesh,u.GeometryScriptCopyMeshFromAssetOptions(),lod)
    ids=json.loads((R/'shard-ids.json').read_text())
    idlist=u.GeometryScript_List.convert_array_to_index_list(ids)
    result=u.GeometryScript_MeshEdits.delete_triangles_from_mesh(mesh,idlist,False)
    count=next(k for k in result if isinstance(k,int))
    if count!=len(ids):raise RuntimeError('Mismatch in local repair triangle IDs')
    options=u.GeometryScriptCopyMeshToAssetOptions();options.set_editor_property('emit_transaction',False)
    res=u.GeometryScript_AssetUtils.copy_mesh_to_static_mesh(mesh,clone,options,u.GeometryScriptMeshWriteLOD())
    if 'FAILURE' in str(res).upper():raise RuntimeError(str(res))
    if len(clone.static_materials)!=len(source.static_materials):raise RuntimeError('Changed tile material slots')
    for i,s in enumerate(source.static_materials):
        if clone.static_materials[i].material_interface!=s.material_interface:raise RuntimeError('Original ceramic slot changed')
    if not lib.save_loaded_asset(clone,False):raise RuntimeError('Tile mesh not saved')
    a.modify();comp.modify();comp.set_static_mesh(clone)
    repair=actors.get('OppositePlatform_CeramicRepairs')
    if repair:api.destroy_actor(repair)
    return {'removed_triangles':count,'original_slots':[s.material_interface.get_path_name() for s in clone.static_materials]}
