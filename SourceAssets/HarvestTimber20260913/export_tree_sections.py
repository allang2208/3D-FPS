"""Export source trunk geometry and its material table for local cut authoring."""
import unreal as u,json
from pathlib import Path
root=Path(__file__).parent/'FellingCut';root.mkdir(exist_ok=True)
options=u.FbxExportOption();options.ascii=False;options.level_of_detail=False;options.collision=False
report={}
for kind in 'ABCD':
    mesh=u.load_asset('/Game/WorldGeneration/TemperateHills/SK_BlackPoplarPCG_'+kind)
    read=u.GeometryScriptMeshReadLOD();read.lod_type=u.GeometryScriptLODType.SOURCE_MODEL
    dynamic,outcome=u.GeometryScript_AssetUtils.copy_mesh_from_skeletal_mesh(mesh,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(),read)
    if outcome!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Cannot extract '+kind)
    create=u.GeometryScriptCreateNewStaticMeshAssetOptions();create.enable_collision=False
    static,outcome=u.GeometryScript_NewAssetUtils.create_new_static_mesh_asset_from_mesh(dynamic,'/Game/Developers/TimberAuthoring/SM_MatchedSource_'+kind,create)
    if outcome!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Cannot create '+kind)
    # Creating a static asset without material slots clamps the source face IDs.
    # Copy again with the original material table before exporting its geometry.
    write=u.GeometryScriptCopyMeshToAssetOptions();write.replace_materials=True
    write.new_materials=[s.material_interface for s in mesh.materials]
    write.new_material_slot_names=[s.material_interface.get_name() for s in mesh.materials]
    write.generate_lightmap_u_vs=u.GeometryScriptGenerateLightmapUVOptions.DO_NOT_GENERATE_LIGHTMAP_U_VS
    _,outcome=u.GeometryScript_AssetUtils.copy_mesh_to_static_mesh(dynamic,static,write,u.GeometryScriptMeshWriteLOD())
    if outcome!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Cannot preserve source materials '+kind)
    task=u.AssetExportTask();task.object=static;task.filename=str(root/('SourceTree_'+kind+'.fbx'))
    task.automated=True;task.prompt=False;task.replace_identical=True;task.options=options
    if not u.Exporter.run_asset_export_task(task):raise RuntimeError('Cannot export '+kind)
    report[kind]={'source':mesh.get_path_name(),'materials':[m.get_path_name() for m in write.new_materials]}
(root/'sources.json').write_text(json.dumps(report,indent=2))
u.log('MATCHED_TREE_SOURCES_EXPORTED')
