"""Kukri FBX authoring import: persistent source LOD and explicit section binding."""
from pathlib import Path
import unreal as u

def require_authoring_context():
    if '-run=pythonscript' in u.SystemLibrary.get_command_line().lower():return
    level=u.get_editor_subsystem(u.LevelEditorSubsystem)
    if level and level.is_in_play_in_editor():
        raise RuntimeError('Kukri authoring import requires PIE to be stopped; no assets changed.')

def import_mesh(filename,package,material):
    require_authoring_context()
    editor=u.get_editor_subsystem(u.StaticMeshEditorSubsystem) or u.new_object(u.StaticMeshEditorSubsystem)
    previous=u.SystemLibrary.get_console_variable_int_value('Interchange.FeatureFlags.Import.FBX')
    try:
        # Runtime/PIE Interchange imports can omit persistent source MeshDescription data.
        # This authoring task explicitly uses FbxFactory and rejects PIE above.
        u.SystemLibrary.execute_console_command(None,'Interchange.FeatureFlags.Import.FBX 0')
        options=u.FbxImportUI();options.import_mesh=True;options.import_as_skeletal=False
        options.import_materials=False;options.import_textures=False;options.import_animations=False
        options.automated_import_should_detect_type=False;options.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
        settings=options.static_mesh_import_data
        settings.combine_meshes=True;settings.auto_generate_collision=False;settings.generate_lightmap_u_vs=True
        settings.convert_scene=True;settings.convert_scene_unit=True
        settings.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS
        task=u.AssetImportTask();task.filename=str(filename)
        task.destination_path,task.destination_name=package.split('.')[0].rsplit('/',1)
        task.automated=True;task.replace_existing=True;task.replace_existing_settings=True;task.save=False
        task.options=options;task.factory=u.FbxFactory()
        u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
        if not task.imported_object_paths:raise RuntimeError('FBX import produced no mesh: '+package)
        mesh=u.load_asset(package)
        if not mesh or not mesh.get_static_mesh_description(0):raise RuntimeError('FBX import produced no persistent LOD0 source: '+package)
        slot=material.get_name()
        imported=list(mesh.get_editor_property('static_materials'))
        binding=next((s for s in imported if str(s.get_editor_property('imported_material_slot_name'))==slot),imported[0])
        binding.set_editor_property('material_interface',material)
        binding.set_editor_property('material_slot_name',slot)
        mesh.set_editor_property('static_materials',[binding])
        mesh.set_minimum_lod_for_platforms({});mesh.set_min_lod_for_quality_levels({},0)
        nanite=mesh.get_editor_property('nanite_settings');nanite.enabled=False;mesh.set_editor_property('nanite_settings',nanite)
        build=editor.get_lod_build_settings(mesh,0)
        build.recompute_normals=False;build.recompute_tangents=True;build.use_mikk_t_space=True
        build.use_high_precision_tangent_basis=True;build.use_full_precision_u_vs=True
        editor.set_lod_build_settings(mesh,0,build)
        for lod in range(mesh.get_num_lods()):
            for section in range(mesh.get_num_sections(lod)):editor.set_lod_material_slot(mesh,0,lod,section)
        u.EditorAssetLibrary.set_metadata_tag(mesh,'Kukri.MeshImportContract','Persistent FBX source LOD0; no PIE; stable material slot; section material index 0')
        return mesh
    finally:
        u.SystemLibrary.execute_console_command(None,'Interchange.FeatureFlags.Import.FBX '+str(previous))
