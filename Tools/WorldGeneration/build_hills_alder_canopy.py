"""Build distance-only crowns from the installed Quixel Black Alder field trees."""
import unreal as u


FOLDER = '/Game/WorldGeneration/TemperateHills/Canopy'
SOURCE = '/CitySamplePCG/BlackAlder/Geometry/PivotPainter/SM_BlackAlder_Field_'


def apply_palette(assets):
    """Save the crown packages and extend the palette. The caller saves the data asset."""
    subsystem = u.get_editor_subsystem(u.StaticMeshEditorSubsystem) or u.new_object(u.StaticMeshEditorSubsystem)
    if "-run=pythonscript" in u.SystemLibrary.get_command_line().lower():
        editor = u.get_editor_subsystem(u.UnrealEditorSubsystem) or u.new_object(u.UnrealEditorSubsystem)
        u.SystemLibrary.execute_console_command(editor.get_editor_world(), "Editor.AsyncStaticMeshCompilation 0")
    library = u.EditorAssetLibrary
    library.make_directory(FOLDER)
    palette = list(assets.get_editor_property('backdrop_trees'))
    paths = {item.get_path_name() for item in palette if item}
    rows = []
    for form in ('01', '04'):
        original = u.load_asset(SOURCE + form + '_PP')
        if not isinstance(original, u.StaticMesh):
            raise RuntimeError('Missing Quixel Black Alder field tree ' + form)
        lod = original.get_num_lods() - 1
        if lod < 1 or original.get_num_sections(lod) != 1:
            raise RuntimeError('Expected one authored impostor section on ' + original.get_name())
        index = subsystem.get_lod_material_slot(original, lod, 0)
        material = original.get_material(index)
        if not material or material.get_name() != 'MI_Impostor_Field_' + form:
            raise RuntimeError('Impostor material does not match ' + original.get_name())

        target = FOLDER + '/SM_HillsAlderCrown_' + form
        mesh = library.load_asset(target) if library.does_asset_exist(target) else None
        if not mesh:
            read = u.GeometryScriptMeshReadLOD(lod_type=u.GeometryScriptLODType.RENDER_DATA, lod_index=lod)
            dynamic, outcome = u.GeometryScript_AssetUtils.copy_mesh_from_static_mesh(
                original, u.DynamicMesh(), u.GeometryScriptCopyMeshFromAssetOptions(), read)
            if (outcome != u.GeometryScriptOutcomePins.SUCCESS or dynamic.get_triangle_count() == 0
                    or dynamic.get_triangle_count() != original.get_num_triangles(lod)):
                raise RuntimeError('Cannot extract the rendered crown LOD from ' + original.get_name())
            u.GeometryScript_Materials.clear_material_i_ds(dynamic, 0)
            mesh, outcome = u.GeometryScript_NewAssetUtils.create_new_static_mesh_asset_from_mesh(
                dynamic, target, u.GeometryScriptCreateNewStaticMeshAssetOptions(enable_collision=False))
            if not mesh or outcome != u.GeometryScriptOutcomePins.SUCCESS:
                raise RuntimeError('Cannot create ' + target)
            mesh.set_material(0, material)
            mesh.set_editor_property("support_ray_tracing", False)
            # Camera-facing WPO billboards still need the donor's three-dimensional
            # bounds when seen side-on. Keep the donor pivot and the baked foliage atlas.
            wanted, actual = original.get_bounding_box(), mesh.get_bounding_box()
            for name, extra in (('positive_bounds_extension', wanted.max - actual.max),
                                ('negative_bounds_extension', actual.min - wanted.min)):
                mesh.set_editor_property(name, u.Vector(max(0., extra.x), max(0., extra.y), max(0., extra.z)))
            if not library.save_loaded_asset(mesh, False):
                raise RuntimeError('Cannot save ' + target)
        if mesh.get_path_name() not in paths:
            palette.append(mesh)
            paths.add(mesh.get_path_name())
        rows.append({'source': original.get_path_name(), 'lod': lod, 'crown': mesh.get_path_name(),
                     'material': material.get_path_name(), 'triangles': mesh.get_num_triangles(0)})
    assets.set_editor_property('backdrop_trees', palette)
    return rows
