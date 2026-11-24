"""Save the three rest meshes using the same two surface materials and cord material as R2."""
from pathlib import Path
import json
import os
import unreal as ue

source=Path(__file__).resolve().parent
batch=Path(os.environ['FRONTIER_REST_BATCH'])
root='/Game/Weapons/FrontierCompoundBow'
destination=root+'/ArrowRestVariantsR1'
specs=json.loads((source/'rests.json').read_text(encoding='utf8'))
materials={key:ue.load_asset(root+'/'+path) for key,path in {
    'M_Frontier_Surface':'M_Frontier_Surface','M_Frontier_Cord':'M_Frontier_Cord',
    'M_FrontierMods_Surface':'CommonModsR1/M_FrontierMods_Surface'}.items()}
ue.SystemLibrary.execute_console_command(None,'Interchange.FeatureFlags.Import.FBX 0')
editor=ue.get_editor_subsystem(ue.StaticMeshEditorSubsystem) or ue.new_object(ue.StaticMeshEditorSubsystem)
tools=ue.AssetToolsHelpers.get_asset_tools()
saved={}
for key,design in specs.items():
    name=design['mesh']
    options=ue.FbxImportUI()
    options.automated_import_should_detect_type=False
    options.mesh_type_to_import=ue.FBXImportType.FBXIT_STATIC_MESH
    options.import_as_skeletal=False
    options.import_mesh=True
    options.import_materials=False
    options.import_textures=False
    data=options.static_mesh_import_data
    data.combine_meshes=True
    data.auto_generate_collision=False
    data.generate_lightmap_u_vs=False
    data.normal_import_method=ue.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS
    task=ue.AssetImportTask()
    task.filename=str(source/'Export'/(name+'.fbx'))
    task.destination_path=destination
    task.destination_name=name
    task.automated=True
    task.replace_existing=True
    task.options=options
    tools.import_asset_tasks([task])
    mesh=ue.load_asset(destination+'/'+name)
    if not mesh:raise RuntimeError('Missing imported rest '+name)
    slots=list(mesh.static_materials)
    for slot in slots:
        material=materials.get(str(slot.material_slot_name))
        if not material:raise RuntimeError(f'{name}: cannot bind {slot.material_slot_name}')
        slot.material_interface=material
    mesh.static_materials=slots
    lod=ue.StaticMeshReductionOptions()
    lod.auto_compute_lod_screen_size=True
    levels=[]
    for fraction in (1.,.60,.32):
        level=ue.StaticMeshReductionSettings()
        level.percent_triangles=fraction
        levels.append(level)
    lod.reduction_settings=levels
    if editor.set_lods(mesh,lod)<1:raise RuntimeError('Unable to create LODs for '+name)
    if not ue.EditorLoadingAndSavingUtils.save_packages([mesh.get_outermost()],False):
        raise RuntimeError('Unable to save '+name)
    saved[key]=mesh.get_path_name()
(batch/'imported.json').write_text(json.dumps({'meshes':saved},indent=2),encoding='utf8')
