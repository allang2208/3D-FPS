"""Save the native skeletal boots and their material-driven robe variants at all three LODs."""
import gc
import hashlib
import json
from pathlib import Path
import sys

import unreal as u

sys.path.insert(0, str(Path(__file__).parent))
from coyote_glove_wear_bind import bones, extract
from coyote_glove_wear_save import io, remap_weights
from field_pants_wear_save import separate_sewn_sheets
import lower_seam_uv
import lower_wear_lods
from ridge_boots_wear import DEST, P, REV, ROOT, SLOTS, package_path, plan, read, sha, write

sys.path.insert(0, str(P / "Tools/BlueMageRobe"))
import hem_materials as hem

E = u.EditorAssetLibrary
A = u.AssetToolsHelpers.get_asset_tools()
S = u.get_editor_subsystem(u.SkeletalMeshEditorSubsystem) or u.new_object(u.SkeletalMeshEditorSubsystem)
PREFIX = DEST + "/Wear/"
POLICY = PREFIX + "DA_TS01_RidgeBoots_LOD"
LOD_REVISION = lower_wear_lods.REVISION
RECEIPT = ROOT / "wear-saved.json"


def persist(asset):
    if not asset.get_path_name().startswith(PREFIX) or not E.save_loaded_asset(asset, False):
        raise RuntimeError("Could not persist the boot package " + asset.get_path_name())


def settings():
    previous = u.load_asset(POLICY) if E.does_asset_exist(POLICY) else None
    if previous:
        if E.get_metadata_tag(previous, "TS01Revision") != REV:
            raise ValueError("Occupied LOD policy " + POLICY)
        if E.get_metadata_tag(previous, "RidgeBootLOD") == LOD_REVISION:
            return previous
    asset = previous
    if not asset:
        folder, name = POLICY.rsplit("/", 1)
        factory = u.DataAssetFactory()
        factory.set_editor_property("data_asset_class", u.SkeletalMeshLODSettings)
        asset = A.create_asset(name, folder, u.SkeletalMeshLODSettings, factory)
    groups = []
    for lod, screen in enumerate((1., .24, .085)):
        group = u.SkeletalMeshLODGroupSettings()
        reduction = group.get_editor_property("reduction_settings")
        for key, value in dict(base_lod=lod, num_of_triangles_percentage=1., num_of_vert_percentage=1.,
                               max_bones_per_vertex=8, lock_edges=True, enforce_bone_boundaries=True,
                               merge_coincident_vert_bones=False, welding_threshold=0., recalc_normals=False).items():
            reduction.set_editor_property(key, value)
        group.set_editor_property("reduction_settings", reduction)
        group.set_editor_property("screen_size", u.PerPlatformFloat(default=screen))
        groups.append(group)
    asset.set_editor_property("lod_groups", groups)
    E.set_metadata_tag(asset, "TS01Revision", REV)
    E.set_metadata_tag(asset, "RidgeBootLOD", LOD_REVISION)
    persist(asset)
    return asset


def target(path, donor):
    package = path.split(".")[0]
    if E.does_asset_exist(package):
        asset = u.load_asset(package)
        if E.get_metadata_tag(asset, "TS01Revision") != REV:
            raise RuntimeError("Another producer owns " + path)
        return asset
    folder, name = package.rsplit("/", 1)
    asset = A.duplicate_asset(name, folder, donor)
    if not asset:
        raise RuntimeError("Could not create " + path)
    E.set_metadata_tag(asset, "TS01Revision", REV)
    return asset


def import_lods(asset, dm, materials, slots, policy, distance_meshes):
    asset.set_editor_property("physics_asset", None)
    asset.set_editor_property("lod_settings", None)
    old_lods = S.get_lod_count(asset)
    if old_lods > 1 and not S.remove_lods(asset, list(range(old_lods - 1, 0, -1))):
        raise RuntimeError("Could not replace distance meshes on " + asset.get_name())
    build = S.get_lod_build_settings(asset, 0)
    build.set_editor_property("use_full_precision_u_vs", True)
    build.set_editor_property("recompute_normals", False)
    S.set_lod_build_settings(asset, 0, build)
    options = u.GeometryScriptCopyMeshToAssetOptions(replace_materials=True, new_materials=materials,
        new_material_slot_names=slots, enable_recompute_normals=False, enable_recompute_tangents=True,
        bone_hierarchy_mismatch_handling=u.GeometryScriptBoneHierarchyMismatchHandling.REMAP_GEOMETRY_TO_REFERENCE_SKELETON)
    _, status = u.GeometryScript_AssetUtils.copy_mesh_to_skeletal_mesh(dm, asset, options, u.GeometryScriptMeshWriteLOD())
    if status != u.GeometryScriptOutcomePins.SUCCESS:
        raise RuntimeError("Could not author " + asset.get_name())
    lower_wear_lods.write(asset, distance_meshes, options)
    asset.set_editor_property("lod_settings", policy)


def save_boot(row, policy):
    path = ROOT / row["source"]
    raw = path.read_bytes()
    fingerprint = hashlib.sha256(raw).hexdigest()
    data = json.loads(raw)
    lower_seam_uv.unfold_sidewalls(data, "RB_", 4.)
    del raw
    native = u.load_asset(row["previous"])
    if not native or sha(package_path(row["previous"])) != row["donor_sha256"]:
        raise RuntimeError("Native boot donor changed: " + row["previous"])
    reference = extract(native)
    skeleton = native.skeleton.get_path_name()
    remap_weights(data, {"skeleton": skeleton, "bones": bones(reference)})
    slots = data["material_slots"]
    materials = [u.load_asset(p) for p in data["materials"]]
    if set(slot for slot in slots if not slot.startswith("NATIVE:")) != set(SLOTS) or not all(materials):
        raise ValueError("Incomplete boot surfaces for " + path.name)
    skins = {s.material_interface.get_path_name() for s in native.materials if str(s.material_slot_name).startswith("NATIVE:")}
    if skins != {mat.get_path_name() for slot, mat in zip(slots, materials) if slot.startswith("NATIVE:")}:
        raise ValueError("Native lower-leg material changed on " + path.name)
    splits = separate_sewn_sheets(data)
    dm = io.dynamic(data, reference)
    if dm.get_triangle_count() != len(data["triangles"]):
        raise ValueError("Native import dropped triangles from " + path.name)
    asset = target(row["asset"], native)
    import_lods(asset, dm, materials, slots, policy, lower_wear_lods.meshes(data, reference, "RB_"))
    provenance = u.new_object(u.AssetImportData, outer=asset)
    provenance.scripted_add_filename(str(path), 0, "Ridge boots native pattern")
    asset.set_editor_property("asset_import_data", provenance)
    E.set_metadata_tag(asset, "PatternSHA256", fingerprint)
    E.set_metadata_tag(asset, "TS01NativeDonor", row["previous"])
    persist(asset)
    lods = [extract(asset, i).get_triangle_count() for i in range(3)]
    if not 0 < lods[2] < lods[1] < lods[0] or lods[0] != dm.get_triangle_count():
        raise RuntimeError("Reduced boot geometry could not be built: " + str(lods))
    return dict(asset=row["asset"], previous=row["previous"], source_file=row["source"], source_sha256=fingerprint,
                package_sha256=sha(package_path(row["asset"])), skeleton=skeleton, render_lods=lods,
                separated_sheet_triangles=splits, material_slots=slots, materials=data["materials"])


def boot_hem_surface(source):
    """Bind the two approved robe shaders to the boot's own MakeMaterialAttributes node."""
    key = hashlib.sha256((sha(package_path(source.get_path_name())) + hem.REV).encode()).hexdigest()
    path = PREFIX + "RobeMaterials/" + source.get_name() + "_RobeHem_" + key[:10]
    existing = u.load_asset(path) if E.does_asset_exist(path) else None
    if existing and E.get_metadata_tag(existing, "RidgeHemSource") == key:
        return existing
    if existing and E.get_metadata_tag(existing, "TS01Revision") != REV:
        raise RuntimeError("Another producer owns " + path)
    master = existing or E.duplicate_asset(source.get_path_name(), path)
    attrs = hem.L.get_material_property_input_node(master, u.MaterialProperty.MP_MATERIAL_ATTRIBUTES)
    if not isinstance(attrs, u.MaterialExpressionMakeMaterialAttributes):
        raise ValueError("Missing boot surface attributes on " + source.get_name())
    # Rebind only the hem nodes. Keep the copied albedo, ORM, tangent normal,
    # specular and cloth shading inputs on their original attribute channels.
    strength = hem.scalar(master, "RobeHemStrength", 0)
    shape = hem.vector(master, "RobeHemShape", (16, 2, 8))
    rings = [hem.vector(master, f"RobeHemPoint{i}") for i in range(64)]
    for masked, code, count, pin in ((False, hem.CODE, 64, "WorldPositionOffset"),
                                      (True, hem.MASK_CODE, 16, "OpacityMask")):
        props = {} if masked else {"world_position_shader_offset": u.WorldPositionIncludedOffsets.WPT_EXCLUDE_ALL_SHADER_OFFSETS}
        world = hem.node(master, u.MaterialExpressionWorldPosition, **props)
        local = hem.node(master, u.MaterialExpressionTransformPosition,
            transform_source_type=u.MaterialPositionTransformSource.TRANSFORMPOSSOURCE_WORLD,
            transform_type=u.MaterialPositionTransformSource.TRANSFORMPOSSOURCE_LOCAL)
        hem.wire(world, local, hem.first(local))
        rest = hem.node(master, u.MaterialExpressionPreSkinnedPosition)
        if masked:
            interpolated = hem.node(master, u.MaterialExpressionVertexInterpolator)
            hem.wire(rest, interpolated, hem.first(interpolated))
            rest = interpolated
        inputs = dict(Position=local, RestPosition=rest, Strength=strength, Shape=shape)
        inputs.update({f"P{i}": v for i, v in enumerate(rings[:count])})
        custom = hem.node(master, u.MaterialExpressionCustom, description="Ridge boot robe " + pin, code=code,
            output_type=u.CustomMaterialOutputType.CMOT_FLOAT1 if masked else u.CustomMaterialOutputType.CMOT_FLOAT3)
        pins = []
        for name in inputs:
            custom_pin = u.CustomInput()
            custom_pin.set_editor_property("input_name", name)
            pins.append(custom_pin)
        custom.set_editor_property("inputs", pins)
        for name, value in inputs.items():
            hem.wire(value, custom, name, "RGB" if isinstance(value, u.MaterialExpressionVectorParameter) else "")
        output = custom
        if not masked:
            output = hem.node(master, u.MaterialExpressionTransform,
                transform_source_type=u.MaterialVectorCoordTransformSource.TRANSFORMSOURCE_LOCAL,
                transform_type=u.MaterialVectorCoordTransform.TRANSFORM_WORLD)
            hem.wire(custom, output, hem.first(output))
        hem.wire(output, attrs, pin)
    master.set_editor_property("blend_mode", u.BlendMode.BLEND_MASKED)
    hem.L.set_base_material_usage(master, u.MaterialUsage.MATUSAGE_SKELETAL_MESH, True)
    if hem.L.recompile_material(master):
        raise RuntimeError("Could not compile the robe surface " + path)
    E.set_metadata_tag(master, "RidgeHemSource", key)
    E.set_metadata_tag(master, "TS01Revision", REV)
    E.set_metadata_tag(master, "RobeHemOriginalMaterial", source.get_path_name())
    persist(master)
    return master


def setup_robe_materials():
    # Reuse any existing envelope of this exact source and shader revision,
    # including the original body skin. New boot graphs stay in our own revision.
    production_make, common = hem.make, hem.DEST
    hem.DEST = PREFIX + "RobeMaterials"
    def get_or_make(source):
        key = source.get_path_name()
        if key not in hem.cache and key.startswith(DEST + "/Materials/"):
            hem.cache[key] = boot_hem_surface(source)
        if key not in hem.cache:
            suffix = hashlib.sha256((key + hem.REV).encode()).hexdigest()[:12]
            stem = "MI_" if isinstance(source, u.MaterialInstanceConstant) else "M_"
            for collection in (common, "/Game/Characters/ModularOutfit20260924/KaitlinPlayer20261023/Materials/Hem"):
                path = f"{collection}/{stem}RobeHem_{suffix}"
                if E.does_asset_exist(path):
                    existing = u.load_asset(path)
                    if E.get_metadata_tag(existing, "RobeHemShaderSHA") == hem.REV:
                        hem.cache[key] = existing
                        break
        return hem.cache[key] if key in hem.cache else production_make(source)
    hem.make = get_or_make


def save_robe(row, saved, policy, surface_hashes):
    base = u.load_asset(row["asset"])
    existed = E.does_asset_exist(row["robe_asset"].split(".")[0])
    asset = target(row["robe_asset"], base)
    materials = [hem.make(slot.material_interface) for slot in base.materials]
    slots = [f"RobeStairHidden_{i}" for i in range(len(materials))]
    if existed and (E.get_metadata_tag(asset, "PatternSHA256") != saved["source_sha256"]
                    or E.get_metadata_tag(asset, "RidgeBootLOD") != LOD_REVISION
                    or E.get_metadata_tag(asset, "SeamUV") != lower_seam_uv.REVISION):
        import_lods(asset, extract(base), materials, slots, policy, lower_wear_lods.source_lods(base))
    else:
        bindings = list(base.materials)
        for slot, name, mat in zip(bindings, slots, materials):
            slot.set_editor_property("material_slot_name", name)
            slot.set_editor_property("material_interface", mat)
        asset.set_editor_property("materials", bindings)
    E.set_metadata_tag(asset, "PatternSHA256", saved["source_sha256"])
    E.set_metadata_tag(asset, "RobeHemShaderSHA", hem.REV)
    E.set_metadata_tag(asset, "RidgeBootLOD", LOD_REVISION)
    E.set_metadata_tag(asset, "SeamUV", lower_seam_uv.REVISION)
    persist(asset)
    return dict(asset=row["robe_asset"], source_asset=row["asset"], source_sha256=saved["source_sha256"],
                package_sha256=sha(package_path(row["robe_asset"])), render_lods=saved["render_lods"],
                materials=[m.get_path_name() for m in materials], surface_hashes=surface_hashes, shader_revision=hem.REV)


def main():
    read(ROOT / "saved-surfaces.json")
    policy = settings()
    setup_robe_materials()
    rows = plan()
    saved = read(RECEIPT) if RECEIPT.exists() else dict(assets={}, robe_assets={})
    saved["policy"] = dict(asset=policy.get_path_name(), sha256=sha(package_path(POLICY)))
    saved["complete"] = False
    for body, row in rows.items():
        source = ROOT / row["source"]
        if not source.is_file():
            continue
        old = saved["assets"].get(body, {})
        package = package_path(row["asset"])
        if (old.get("seam_uv") != lower_seam_uv.REVISION or old.get("source_sha256") != sha(source) or old.get("lod_revision") != LOD_REVISION or not package.is_file()
                or old.get("package_sha256") != sha(package)):
            saved["assets"][body] = save_boot(row, policy)
            saved["assets"][body]["lod_revision"] = LOD_REVISION
            saved["assets"][body]["seam_uv"] = lower_seam_uv.REVISION
            write(RECEIPT, saved)
        gc.collect()
        u.SystemLibrary.collect_garbage()
    for body, row in rows.items():
        if body not in saved["assets"] or not (ROOT / row["source"]).is_file():
            continue
        old_robe = saved["robe_assets"].get(body, {})
        package = package_path(row["robe_asset"])
        surface_hashes = {path: sha(package_path(path)) for path in saved["assets"][body]["materials"]}
        if (old_robe.get("seam_uv") != lower_seam_uv.REVISION or old_robe.get("source_sha256") != saved["assets"][body]["source_sha256"]
                or old_robe.get("shader_revision") != hem.REV or old_robe.get("lod_revision") != LOD_REVISION or not package.is_file()
                or old_robe.get("surface_hashes") != surface_hashes
                or old_robe.get("package_sha256") != sha(package)):
            saved["robe_assets"][body] = save_robe(row, saved["assets"][body], policy, surface_hashes)
            saved["robe_assets"][body]["lod_revision"] = LOD_REVISION
            saved["robe_assets"][body]["seam_uv"] = lower_seam_uv.REVISION
            write(RECEIPT, saved)
        gc.collect()
        u.SystemLibrary.collect_garbage()
    saved["complete"] = all((ROOT / row["source"]).is_file() and body in saved["assets"] and body in saved["robe_assets"]
                            for body, row in rows.items())
    write(RECEIPT, saved)


if __name__ == "__main__":
    main()
