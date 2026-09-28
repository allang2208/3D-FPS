"""Apply resource budgets to this noninteractive background mesh only."""
import json
from pathlib import Path
import unreal as u

def apply(mesh):
    # FBX atomic reimport can preserve the asset's old build options despite
    # FbxStaticMeshImportData overrides. Persist budgets on the actual LOD.
    editor=u.get_editor_subsystem(u.StaticMeshEditorSubsystem) or u.new_object(u.StaticMeshEditorSubsystem)
    settings=editor.get_lod_build_settings(mesh,0)
    settings.set_editor_property('distance_field_resolution_scale',0.)
    settings.set_editor_property('generate_lightmap_u_vs',False)
    editor.set_lod_build_settings(mesh,0,settings)
    mesh.set_editor_property('support_ray_tracing',False)
    mesh.set_editor_property('allow_cpu_access',False)
    spectrum=json.loads(Path(__file__).with_name('Receipts').joinpath('ocean-reused-spectrum.json').read_text(encoding='utf8'))
    bound=max(1500.,spectrum['absolute_displacement_bound_cm']+100.)
    mesh.set_editor_property('positive_bounds_extension',u.Vector(0,0,bound))
    mesh.set_editor_property('negative_bounds_extension',u.Vector(0,0,bound))

if __name__=='__main__':
    root=Path(__file__).parent
    u.SystemLibrary.execute_console_command(None,'Interchange.FeatureFlags.Import.FBX 0')
    opt=u.FbxImportUI();opt.automated_import_should_detect_type=False;opt.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
    opt.import_as_skeletal=False;opt.import_mesh=True;opt.import_materials=False;opt.import_textures=False;opt.import_animations=False
    d=opt.static_mesh_import_data;d.combine_meshes=True;d.auto_generate_collision=False;d.import_uniform_scale=1
    d.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS;d.reorder_material_to_fbx_order=True
    d.set_editor_property('distance_field_resolution_scale',0.);d.set_editor_property('generate_lightmap_u_vs',False)
    t=u.AssetImportTask();t.filename=str(root/'Exported/SM_GodSpaceDistantOcean.fbx');t.destination_path='/Game/Props/GodSpaceLayout20260927/Meshes';t.destination_name='SM_GodSpaceDistantOcean'
    t.automated=True;t.replace_existing=True;t.replace_existing_settings=True;t.save=False;t.options=opt
    u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([t])
    mesh=u.load_asset('/Game/Props/GodSpaceLayout20260927/Meshes/SM_GodSpaceDistantOcean')
    if not mesh:raise RuntimeError('Ocean mesh missing')
    mat=u.load_asset('/Game/Props/GodSpaceLayout20260927/Materials/MI_GodSpaceDistantOcean')
    far=u.load_asset('/Game/Props/GodSpaceLayout20260927/Materials/MI_GodSpaceOceanFar')
    for index,slot in enumerate(mesh.get_editor_property('static_materials')):
        name=str(slot.get_editor_property('imported_material_slot_name')).lower()
        mesh.set_material(index,far if 'far' in name else mat)
    apply(mesh)
    u.SystemLibrary.execute_console_command(None,'Editor.AsyncAssetCompilationFinishAll')
    if not u.EditorAssetLibrary.save_loaded_asset(mesh,False):raise RuntimeError('Mesh budget save failed')
    Path(__file__).with_name('Receipts').joinpath('ocean-mesh-budget.json').write_text(json.dumps(dict(saved=mesh.get_path_name(),distance_field_resolution_scale=0,lightmap_uvs=False,ray_tracing_geometry=False,cpu_access=False,runtime_tested=False),indent=2),encoding='utf8')
    print('GODSPACE_OCEAN_MESH_BUDGET_SAVED')
