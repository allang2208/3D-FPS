"""Export the four existing tree sources for local stump cutting. No scene run."""
import unreal as u,json
from pathlib import Path
root=Path(__file__).parent/'OriginalStumps';root.mkdir(exist_ok=True)
report={}
options=u.FbxExportOption()
options.set_editor_property('ascii',False)
options.set_editor_property('level_of_detail',False)
options.set_editor_property('collision',False)
for kind in 'ABCD':
    path='/Game/WorldGeneration/TemperateHills/SK_BlackPoplarPCG_'+kind
    mesh=u.load_asset(path)
    # Export the editor source geometry. The ordinary skeletal exporter selects
    # imported fallback triangles for these Nanite trees and loses their roots.
    dynamic=u.DynamicMesh()
    read=u.GeometryScriptMeshReadLOD();read.lod_type=u.GeometryScriptLODType.SOURCE_MODEL;read.lod_index=0
    dynamic,outcome=u.GeometryScript_AssetUtils.copy_mesh_from_skeletal_mesh(mesh,dynamic,u.GeometryScriptCopyMeshFromAssetOptions(),read)
    if outcome!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Cannot extract source geometry '+path)
    static_path='/Game/Developers/TimberAuthoring/SM_SourceTree_'+kind
    static=u.load_asset(static_path)
    if static is None:
        create=u.GeometryScriptCreateNewStaticMeshAssetOptions();create.enable_collision=False
        static,outcome=u.GeometryScript_NewAssetUtils.create_new_static_mesh_asset_from_mesh(dynamic,static_path,create)
        if outcome!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Cannot create authoring mesh '+path)
    static.set_editor_property('static_materials',[u.StaticMaterial(material_interface=slot.material_interface,material_slot_name=slot.material_interface.get_name()) for slot in mesh.materials])
    task=u.AssetExportTask();task.object=static;task.filename=str(root/('SourceTree_'+kind+'.fbx'))
    task.automated=True;task.prompt=False;task.replace_identical=True;task.options=options
    if not u.Exporter.run_asset_export_task(task):raise RuntimeError('Cannot export '+path)
    report[kind]={'source':path,'materials':[slot.material_interface.get_path_name() if slot.material_interface else None for slot in mesh.materials]}
(root/'sources.json').write_text(json.dumps(report,indent=2))
u.log('ORIGINAL_STUMP_SOURCES_EXPORTED')
