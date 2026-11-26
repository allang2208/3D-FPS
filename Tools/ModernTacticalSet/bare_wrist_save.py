"""Fit a local mask on the original native skin graph, retaining every LOD and wrist morph."""
import gc
import hashlib
import json
import math
import os
from pathlib import Path

import unreal as ue

PROJECT = Path("D:/FPS3D/FPSGAME")
ROOT = PROJECT / "SourceAssets/ModernTacticalSet20261113/BareWrists20261118"
ROOT.mkdir(exist_ok=True)
DEST = "/Game/Characters/ModularOutfit20260924/ModernTacticalSet20261113/CombatShirtR4/BareWrists20261118"
LIB = ue.EditorAssetLibrary
ART = ue.AssetToolsHelpers.get_asset_tools()
MAT = ue.MaterialEditingLibrary
PROP = ue.MaterialProperty
RADIUS_CM = 11.5
revision = "NativeSkinVertexWristMask-v1"
graphs = {}


def wire(source, target, pin, output=""):
    if not MAT.connect_material_expressions(source, output, target, pin):
        raise RuntimeError("Cannot connect " + pin)


def node(mat, kind, **properties):
    result = MAT.create_material_expression(mat, kind)
    for key, value in properties.items():
        result.set_editor_property(key, value)
    return result


def native_graph(source):
    """Clone each inherited skin graph once. Keep its textures, parameters and lighting."""
    original = source.get_path_name()
    if original in graphs:
        return graphs[original]
    name = "WristBase_" + hashlib.sha256((original + revision).encode()).hexdigest()[:12]
    path = DEST + "/" + name
    result = ue.load_asset(path) if LIB.does_asset_exist(path) else None
    if result and LIB.get_metadata_tag(result, "WristSourceGraph") == original:
        graphs[original] = result
        return result
    if result:
        raise RuntimeError("Conflicting staged graph " + path)
    result = ART.duplicate_asset(name, DEST, source)
    if isinstance(result, ue.MaterialInstanceConstant):
        MAT.set_material_instance_parent(result, native_graph(source.get_editor_property("parent")))
        overrides = result.get_editor_property("base_property_overrides")
        overrides.set_editor_property("override_blend_mode", True)
        overrides.set_editor_property("blend_mode", ue.BlendMode.BLEND_MASKED)
        result.set_editor_property("base_property_overrides", overrides)
        MAT.update_material_instance(result)
    elif isinstance(result, ue.Material):
        attrs = result.get_editor_property("use_material_attributes")
        oldprop = PROP.MP_MATERIAL_ATTRIBUTES if attrs else PROP.MP_OPACITY_MASK
        old = MAT.get_material_property_input_node(result, oldprop)
        old_output = MAT.get_material_property_input_node_output_name(result, oldprop) if old else ""
        result.set_editor_property("blend_mode", ue.BlendMode.BLEND_MASKED)
        position = node(result, ue.MaterialExpressionPreSkinnedPosition)
        distance = node(result, ue.MaterialExpressionCustom, description="Native bare wrist band",
                        code=f"return {RADIUS_CM} - min(length(P-L), length(P-R));",
                        output_type=ue.CustomMaterialOutputType.CMOT_FLOAT1)
        pins = []
        for key in ["P", "L", "R"]:
            pin = ue.CustomInput()
            pin.set_editor_property("input_name", key)
            pins.append(pin)
        distance.set_editor_property("inputs", pins)
        wire(position, distance, "P")
        for k in ["L", "R"]:
            anchor = node(result, ue.MaterialExpressionVectorParameter, parameter_name="WristAnchor" + k)
            wire(anchor, distance, k, "RGB")
        band = node(result, ue.MaterialExpressionVertexInterpolator)
        wire(distance, band, str(MAT.get_material_expression_input_names(band)[0]))
        # The mask ends inside the sleeve. Evaluate rest coordinates on the vertices;
        # the material continues to follow the actual hand and its corrective morphs.
        if attrs:
            if not old:
                raise RuntimeError("Empty native material attributes " + original)
            outside = node(result, ue.MaterialExpressionMakeMaterialAttributes)
            wire(node(result, ue.MaterialExpressionConstant, r=0.0), outside, "OpacityMask")
            mask = node(result, ue.MaterialExpressionSaturate)
            wire(band, mask, str(MAT.get_material_expression_input_names(mask)[0]))
            blend = node(result, ue.MaterialExpressionBlendMaterialAttributes,
                         vertex_attribute_blend_type=ue.MaterialAttributeBlend.USE_B)
            wire(outside, blend, "A")
            wire(old, blend, "B", old_output)
            wire(mask, blend, "Alpha")
            output = blend
        elif old:
            output = node(result, ue.MaterialExpressionMultiply)
            wire(old, output, "A", old_output)
            wire(band, output, "B")
        else:
            output = band
        if not MAT.connect_material_property(output, "", oldprop):
            raise RuntimeError("Cannot connect final mask " + original)
        errors = MAT.recompile_material(result)
        if errors:
            raise RuntimeError("Skin surface compile: " + str(errors))
    else:
        raise RuntimeError("Unsupported skin surface " + original)
    LIB.set_metadata_tag(result, "WristSourceGraph", original)
    if not LIB.save_loaded_asset(result, False):
        raise RuntimeError("Cannot save original skin graph " + path)
    graphs[original] = result
    return result


def author(skin, slots, key):
    index = next(i for i, s in enumerate(slots) if s in ("BareLowerArms", "SkinArms", "Manny_S90_Skin_Forearm"))
    source = skin.materials[index].material_interface
    material = native_graph(source)
    mesh, status = ue.GeometryScript_AssetUtils.copy_mesh_from_skeletal_mesh(
        skin, ue.DynamicMesh(), ue.GeometryScriptCopyMeshFromAssetOptions(), ue.GeometryScriptMeshReadLOD())
    if status != ue.GeometryScriptOutcomePins.SUCCESS:
        raise RuntimeError("Cannot read current wrist frame: " + skin.get_path_name())
    _, bones = ue.GeometryScript_BoneWeights.get_all_bones_info(mesh)
    centers = {str(b.name): b.world_transform.translation for b in bones}
    name = "MI_Wrist_" + key
    path = DEST + "/" + name
    result = ue.load_asset(path) if LIB.does_asset_exist(path) else ART.create_asset(
        name, DEST, ue.MaterialInstanceConstant, ue.MaterialInstanceConstantFactoryNew())
    MAT.set_material_instance_parent(result, material)
    record = {}
    for side in "lr":
        wrist = centers["hand_" + side]
        record[side] = [wrist.x, wrist.y, wrist.z]
        MAT.set_material_instance_vector_parameter_value(result, "WristAnchor" + side.upper(),
                                                         ue.LinearColor(wrist.x, wrist.y, wrist.z, 1))
    MAT.update_material_instance(result)
    if not LIB.save_loaded_asset(result, False):
        raise RuntimeError("Cannot save fitted wrist material " + path)
    packages = []
    current = result
    while current and current.get_path_name().startswith(DEST + "/"):
        packages.append(current.get_path_name())
        current = current.get_editor_property("parent") if isinstance(current, ue.MaterialInstanceConstant) else None
    return dict(material=result.get_path_name(), slot=index, original_material=source.get_path_name(),
                wrist_centers=record, radius_cm=RADIUS_CM, packages=packages)


def wrist_sections(skin, slots):
    mesh, outcome = ue.GeometryScript_AssetUtils.copy_mesh_from_skeletal_mesh(
        skin, ue.DynamicMesh(), ue.GeometryScriptCopyMeshFromAssetOptions(),
        ue.GeometryScriptMeshReadLOD())
    if outcome != ue.GeometryScriptOutcomePins.SUCCESS:
        raise RuntimeError("Cannot read wrist cross sections " + skin.get_path_name())
    query = ue.GeometryScript_MeshQueries
    lists = ue.GeometryScript_List
    _, vertices, _ = query.get_all_vertex_positions(mesh, False)
    _, triangles, _ = query.get_all_triangle_indices(mesh, False)
    _, mids, _ = ue.GeometryScript_Materials.get_all_triangle_material_i_ds(mesh)
    _, bones = ue.GeometryScript_BoneWeights.get_all_bones_info(mesh)
    poses = {str(b.name): b.world_transform.translation for b in bones}
    points = [(v.x,v.y,v.z) for v in lists.convert_vector_list_to_array(vertices)]
    sets = [set() for s in slots]
    for face, material in zip(lists.convert_triangle_list_to_array(triangles), lists.convert_index_list_to_array(mids)):
        sets[material].update((face.x, face.y, face.z))
    mat_hand = next(i for i, s in enumerate(slots) if "hand" in s.lower() and "wrist" not in s.lower())
    mat_arm = next(i for i, s in enumerate(slots) if s in ("BareLowerArms", "SkinArms", "Manny_S90_Skin_Forearm"))
    result = {}
    for side in "lr":
        w, e = poses["hand_"+side], poses["lowerarm_"+side]
        wrist = (w.x,w.y,w.z)
        axis = [e.x-w.x, e.y-w.y, e.z-w.z]
        scale = math.sqrt(sum(q*q for q in axis))
        unit = [q/scale for q in axis]
        old = sets[mat_hand]
        if "WristUnderlapSkin" in slots:
            extension = sets[slots.index("WristUnderlapSkin")]
        else:
            extension = [i for i in sets[mat_arm] if math.dist(points[i], wrist) <= RADIUS_CM-1]
        def extent(ids):
            return max(sum((v-x)*q for v,x,q in zip(points[i],wrist,unit)) for i in ids
                       if math.dist(points[i],wrist) < 16)
        result[side] = {"old_hand_extent_cm": extent(old), "with_underlap_extent_cm": extent(set(extension)|old)}
    return result


def main():
    config = json.loads((PROJECT / "Content/ColdSteelData/modular_outfits.json").read_text(encoding="utf-8-sig"))
    jobs = {}
    for sex, branch in [("Jason", config), ("Kaitlin", config["body_variants"]["kaitlin"])]:
        for p in branch["profiles"].values():
            path = p.get("native_bare_skin") or p["base"]
            jobs[path] = (sex, p["rig_profile"])
    record_path = ROOT / "saved-materials.json"
    data = json.loads(record_path.read_text()) if record_path.exists() else {}
    rows = data.get("skins", {}) if data.get("revision") == revision else {}
    for path, (sex, rig) in jobs.items():
        asset = PROJECT / "Content" / (path.split(".")[0].removeprefix("/Game/") + ".uasset")
        sha = hashlib.sha256(asset.read_bytes()).hexdigest()
        if rows.get(path, {}).get("sha256") == sha:
            continue
        skin = ue.load_asset(path)
        if not skin:
            raise RuntimeError("Missing native skin " + path)
        slots = [str(m.material_slot_name) for m in skin.materials]
        row = dict(sha256=sha, body=sex, rig=rig, slots=slots)
        if "WristUnderlapSkin" not in slots:
            row.update(author(skin, slots, sex + "_" + rig + "_" + sha[:10]))
        if rig in ("Jason", "Kaitlin", "Super90", "M4"):
            row["reference_extent"] = wrist_sections(skin, slots)
        rows[path] = row
        tmp = record_path.with_suffix(".tmp")
        tmp.write_text(json.dumps(dict(completed=len(rows)==len(jobs), revision=revision, skins=rows), indent=2))
        os.replace(tmp, record_path)
        del skin
        gc.collect()
        ue.SystemLibrary.collect_garbage()
        print("NATIVE_WRIST", path, row.get("material", "existing wrist section"), flush=True)


main()

