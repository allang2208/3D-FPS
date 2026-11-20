"""Use two native Simple Wind saplings from Quixel's European Black Alder pack."""
import unreal as ue


SOURCE = "/Game/BlackAlder/Geometry/SimpleWind/SM_BlackAlder_Sapling_"
DEST = "/Game/WorldGeneration/TemperateHills/WetBank"
LIB = ue.EditorAssetLibrary


def copy_owned(source, path):
    if LIB.does_asset_exist(path):
        return ue.load_asset(path)
    result = LIB.duplicate_asset(source.get_path_name(), path)
    if not result:
        raise RuntimeError("Could not create " + path)
    return result


def hillside_leaves(source):
    material = copy_owned(source, DEST + "/MI_SaplingSimpleWind")
    editing = ue.MaterialEditingLibrary
    for parameter in editing.get_texture_parameter_names(source):
        texture = editing.get_material_instance_texture_parameter_value(source, parameter)
        if not texture:
            continue
        original = texture.get_path_name().split(".")[0]
        if not original.startswith("/Game/BlackAlder/Textures/TwoSided/"):
            continue
        # The installed City Sample alder uses the same UV atlas with smaller
        # source textures. Both age classes can share these six streamed maps.
        shared = ue.load_asset(original.replace("/Game/BlackAlder/", "/CitySamplePCG/BlackAlder/", 1))
        if not isinstance(shared, ue.Texture2D):
            raise RuntimeError("Missing shared alder atlas for " + str(parameter))
        editing.set_material_instance_texture_parameter_value(material, parameter, shared)
    editing.update_material_instance(material)
    if not LIB.save_loaded_asset(material, False):
        raise RuntimeError("Could not save alder foliage material")
    return material


def author_bank_lods(mesh, original, form):
    if LIB.get_metadata_tag(mesh, "HillsSaplingLods") == "1":
        return
    editor = ue.get_editor_subsystem(ue.StaticMeshEditorSubsystem) or ue.new_object(ue.StaticMeshEditorSubsystem)
    # Start with a native leaf-card LOD. UVs, wind weights and the branch shape
    # travel together. The source pack's Nanite fallback is unsuitable as LOD0 here.
    mesh.set_editor_property("static_materials", list(original.static_materials))
    nanite = mesh.get_editor_property("nanite_settings")
    nanite.enabled = False
    mesh.set_editor_property("nanite_settings", nanite)
    donor_lod = 1 if form == "01" else 2
    if editor.set_lod_from_static_mesh(mesh, 0, original, donor_lod, True) != 0:
        raise RuntimeError("Could not copy the authored alder LOD for " + form)
    options = ue.StaticMeshReductionOptions()
    options.auto_compute_lod_screen_size = False
    levels = []
    for fraction, screen in ((1., 1.), (.40, .12), (.17, .055), (.065, .022)):
        level = ue.StaticMeshReductionSettings()
        level.percent_triangles = fraction
        level.screen_size = screen
        levels.append(level)
    options.reduction_settings = levels
    if editor.set_lods(mesh, options) < 1:
        raise RuntimeError("Could not generate the alder LODs for " + form)
    counts = [mesh.get_num_triangles(i) for i in range(mesh.get_num_lods())]
    if len(counts) != 4 or counts[-1] <= 0 or any(a <= b for a, b in zip(counts, counts[1:])):
        raise RuntimeError("Unexpected alder LODs for " + form + ": " + str(counts))
    LIB.set_metadata_tag(mesh, "HillsSaplingLods", "1")


def apply_palette(assets):
    """Append the authored juvenile forms. The calling installer saves the data asset."""
    variants = list(assets.get_editor_property("wet_bank_saplings"))
    current = {mesh.get_path_name() for mesh in variants if mesh}
    LIB.make_directory(DEST)
    leaf = None
    rows = []
    for form in ("01", "03"):
        path = SOURCE + form
        original = ue.load_asset(path)
        if not isinstance(original, ue.StaticMesh):
            raise RuntimeError("Missing European Black Alder sapling at " + path)
        mesh = copy_owned(original, DEST + "/SM_ShoreAlderSapling_" + form)
        author_bank_lods(mesh, original, form)
        for index, slot in enumerate(original.static_materials):
            native_material = slot.material_interface
            if native_material and native_material.get_name() == "MI_BlackAlder_Sapling_TwoSided":
                if leaf is None:
                    leaf = hillside_leaves(native_material)
                mesh.set_material(index, leaf)
        if not LIB.save_loaded_asset(mesh, False):
            raise RuntimeError("Could not save " + mesh.get_path_name())
        lods = [mesh.get_num_triangles(index) for index in range(mesh.get_num_lods())]
        materials = [slot.material_interface for slot in mesh.static_materials]
        if not lods or not all(lods) or not materials or not all(materials):
            raise RuntimeError("Incomplete sapling geometry or materials at " + path)
        if mesh.get_path_name() not in current:
            variants.append(mesh)
            current.add(mesh.get_path_name())
        rows.append({"source": original.get_path_name(), "mesh": mesh.get_path_name(), "lod_triangles": lods,
                     "materials": [mat.get_path_name() for mat in materials]})
    assets.set_editor_property("wet_bank_saplings", variants)
    return rows
