"""Cut the cookhouse flue through its own copy of the Normandy roof bay."""
import unreal as u


ROOF = '/Game/WorldGeneration/VillageTavern/KitchenRoof/SM_TavernFlueRoof'


def flue_roof(donor, tile):
    # The cook hearth faces west, with a 30 cm open throat inside a 42 cm stack.
    # End the roof tile inside the thickness of the masonry on all four sides.
    low = u.MathLibrary.inverse_transform_location(tile,u.Vector(563.5, 61., 430.))
    high = u.MathLibrary.inverse_transform_location(tile,u.Vector(598.5, 97., 710.))
    bounds = high-low
    centre = (low+high)*.5
    stamp = ','.join(f'{v:.4f}' for v in (low.x,low.y,low.z,high.x,high.y,high.z))
    assets = u.EditorAssetLibrary
    saved = assets.load_asset(ROOF) if assets.does_asset_exist(ROOF) else None
    if saved and assets.get_metadata_tag(saved, 'TavernFlueCut') == stamp:
        return ROOF

    api = u.GeometryScript_AssetUtils
    result, status = api.copy_mesh_from_static_mesh(
        donor,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD())
    if status != u.GeometryScriptOutcomePins.SUCCESS:
        raise RuntimeError('Cannot read the tavern roof slopes')
    cutter = u.DynamicMesh()
    u.GeometryScript_Primitives.append_box(
        cutter,u.GeometryScriptPrimitiveOptions(),u.Transform(location=centre),
        abs(bounds.x),abs(bounds.y),abs(bounds.z),origin=u.GeometryScriptPrimitiveOriginMode.CENTER)
    u.GeometryScript_MeshBooleans.apply_mesh_boolean(
        result,u.Transform(),cutter,u.Transform(),u.GeometryScriptBooleanOperation.TRIM_INSIDE,
        u.GeometryScriptMeshBooleanOptions(fill_holes=False,simplify_output=False))

    if not saved:
        saved,status = u.GeometryScript_NewAssetUtils.create_new_static_mesh_asset_from_mesh(
            result,ROOF,u.GeometryScriptCreateNewStaticMeshAssetOptions(enable_collision=True,
                enable_nanite=True,enable_recompute_normals=False,enable_recompute_tangents=True))
        if not saved or status != u.GeometryScriptOutcomePins.SUCCESS:
            raise RuntimeError('Cannot create the roof bay for the kitchen')
    slots = donor.static_materials
    nanite = donor.get_editor_property('nanite_settings')
    nanite.enabled = True
    nanite.fallback_percent_triangles = 1.
    nanite.fallback_relative_error = 0.
    options = u.GeometryScriptCopyMeshToAssetOptions(
        replace_materials=True,new_materials=[s.material_interface for s in slots],
        new_material_slot_names=[s.material_slot_name for s in slots],apply_nanite_settings=True,
        new_nanite_settings=nanite,enable_recompute_normals=False,enable_recompute_tangents=True)
    _,status = api.copy_mesh_to_static_mesh(result,saved,options,u.GeometryScriptMeshWriteLOD())
    if status != u.GeometryScriptOutcomePins.SUCCESS:
        raise RuntimeError('Cannot write the cut slate bay')
    saved.get_editor_property('body_setup').set_editor_property(
        'collision_trace_flag',u.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE)
    assets.set_metadata_tag(saved,'TavernFlueCut',stamp)
    if not assets.save_loaded_asset(saved,False):
        raise RuntimeError('Cannot save '+ROOF)
    return ROOF
