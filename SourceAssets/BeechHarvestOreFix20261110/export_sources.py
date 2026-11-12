"""Export the four active beech trunks; repair only the ore usage flag."""
import json, shutil
from pathlib import Path
from datetime import datetime
import unreal as u

ROOT=Path(__file__).parent
PROJECT=ROOT.parent.parent
E=u.EditorAssetLibrary
L=u.MaterialEditingLibrary
def backup(obj):
    rel=obj.get_path_name().split('.')[0].removeprefix('/Game/')
    for ext in ('.uasset','.uexp','.ubulk'):
        src=PROJECT/'Content'/(rel+ext);dst=ROOT/'Backups/Content'/(rel+ext)
        if src.exists() and not dst.exists():
            dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dst)
def save(obj):
    if not E.save_loaded_asset(obj,False):raise RuntimeError('Save failed: '+obj.get_path_name())

ore='/Game/WorldGeneration/TemperateHills/OreRocks/'
master=u.load_asset(ore+'M_HillsOreRock')
ore_report={'before_instanced_usage':master.get_editor_property('used_with_instanced_static_meshes'),'saved':[]}
backup(master)
master.set_editor_property('used_with_instanced_static_meshes',True)
L.recompile_material(master);save(master);ore_report['saved'].append(master.get_path_name())
for kind in ('Iron','Copper','Silver','Gold'):
    mi=u.load_asset(ore+'MI_HillsOre_'+kind);backup(mi)
    L.update_material_instance(mi);save(mi);ore_report['saved'].append(mi.get_path_name())
ore_report['finished_at']=datetime.now().astimezone().isoformat()
(ROOT/'Receipts/ore-saved.json').write_text(json.dumps(ore_report,indent=2),encoding='utf-8')

options=u.FbxExportOption();options.ascii=False;options.level_of_detail=False;options.collision=False
report={}
for kind in 'ABCD':
    mesh=u.load_asset('/Game/WorldGeneration/TemperateHills/ForestSpecies20261110/Meshes/SK_Beech_'+kind)
    read=u.GeometryScriptMeshReadLOD();read.lod_type=u.GeometryScriptLODType.SOURCE_MODEL
    dynamic,outcome=u.GeometryScript_AssetUtils.copy_mesh_from_skeletal_mesh(mesh,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(),read)
    if outcome!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Cannot extract '+kind)
    create=u.GeometryScriptCreateNewStaticMeshAssetOptions();create.enable_collision=False
    static,outcome=u.GeometryScript_NewAssetUtils.create_new_static_mesh_asset_from_mesh(dynamic,'/Game/Developers/BeechHarvestAuthoring/SM_Source_'+kind,create)
    if outcome!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Cannot create '+kind)
    write=u.GeometryScriptCopyMeshToAssetOptions();write.replace_materials=True
    write.new_materials=[s.material_interface for s in mesh.materials]
    write.new_material_slot_names=[s.material_slot_name for s in mesh.materials]
    write.generate_lightmap_u_vs=u.GeometryScriptGenerateLightmapUVOptions.DO_NOT_GENERATE_LIGHTMAP_U_VS
    _,outcome=u.GeometryScript_AssetUtils.copy_mesh_to_static_mesh(dynamic,static,write,u.GeometryScriptMeshWriteLOD())
    if outcome!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Cannot preserve materials '+kind)
    task=u.AssetExportTask();task.object=static;task.filename=str(ROOT/'FellingCut'/('SourceTree_'+kind+'.fbx'))
    task.automated=True;task.prompt=False;task.replace_identical=True;task.options=options
    if not u.Exporter.run_asset_export_task(task):raise RuntimeError('Cannot export '+kind)
    b=mesh.get_bounds()
    report[kind]={'source':mesh.get_path_name(),'height_cm':b.origin.z+b.box_extent.z,'trunk_triangles':dynamic.get_triangle_count(),
        'slots':[str(s.material_slot_name) for s in mesh.materials],
        'materials':[{'path':m.get_path_name(),'parent':m.get_editor_property('parent').get_path_name(),
          'switches':{str(p):L.get_material_instance_static_switch_parameter_value(m,p) for p in L.get_static_switch_parameter_names(m)}} for m in write.new_materials]}
    (ROOT/'FellingCut/sources.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
u.log('BEECH_TRUNKS_EXPORTED_AND_ORE_USAGE_SAVED')
