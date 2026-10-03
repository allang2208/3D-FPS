"""Author the current Witch's independent staff collision; no game/preview run."""
import json
from pathlib import Path
import unreal as u

ROOT = Path("D:/FPS3D/FPSGAME/SourceAssets/WitchStaffDrop20261002")
CURRENT_RECEIPTS = Path("D:/FPS3D/FPSGAME/SourceAssets/WitchPhysicalSettle20261003/Receipts")
SOURCE = "/Game/Monsters/WitchMeshy/Props/SM_Witch_Staff"
DEST = "/Game/Monsters/WitchRebuilt/Props/SM_WitchRebuilt_StaffPhysics"
MATERIAL = "/Game/Monsters/WitchRebuilt/Props/PM_WitchRebuilt_Staff"
LIB = u.EditorAssetLibrary

def stage(name, **details):
    CURRENT_RECEIPTS.mkdir(parents=True, exist_ok=True)
    report = {"stage": name, **details}
    (CURRENT_RECEIPTS / "staff-authoring-progress.json").write_text(
        json.dumps(report, indent=2), encoding="utf-8")
    print("WITCH_STAFF_AUTHORING " + json.dumps(report), flush=True)

stage("LoadStaff")
mesh = u.load_asset(DEST)
if mesh is None:
    mesh = LIB.duplicate_asset(SOURCE, DEST)
if mesh is None:
    raise RuntimeError("Could not create the Witch staff physics asset")

# One compound rigid body: separate convexes follow the crooked shaft and skull.
# A full-height bounding box would hold the visible shaft above the floor.
stage("ReadSourceGeometry")
dynamic, outcome = u.GeometryScript_AssetUtils.copy_mesh_from_static_mesh(
    mesh, u.DynamicMesh(), u.GeometryScriptCopyMeshFromAssetOptions(),
    u.GeometryScriptMeshReadLOD(lod_type=u.GeometryScriptLODType.SOURCE_MODEL))
if outcome != u.GeometryScriptOutcomePins.SUCCESS:
    raise RuntimeError("Could not read staff source geometry for collision: " + str(outcome))
components_before = u.GeometryScript_MeshQueries.get_num_connected_components(dynamic)
stage("WeldCollisionProxy", source_components=components_before)
# Source render seams produce thousands of disconnected patches. Rejoin only
# coincident edges on the temporary physics proxy, preserving the visual asset.
dynamic = u.GeometryScript_MeshRepair.weld_mesh_edges(
    dynamic, u.GeometryScriptWeldEdgesOptions(tolerance=.001, only_unique_pairs=True))
components_after = u.GeometryScript_MeshQueries.get_num_connected_components(dynamic)
stage("CollisionProxyWelded", components=components_after)
options = u.GeometryScriptCollisionFromMeshOptions(
    emit_transaction=False, method=u.GeometryScriptCollisionGenerationMethod.CONVEX_HULLS,
    auto_detect_spheres=False, auto_detect_boxes=False, auto_detect_capsules=False,
    min_thickness=.25, max_convex_hulls_per_mesh=8, convex_hull_target_face_count=32,
    convex_decomposition_search_factor=1., convex_decomposition_min_part_thickness=.25,
    max_shape_count=0)
stage("GenerateCompleteHulls")
collision = u.GeometryScript_Collision.generate_collision_from_mesh(dynamic, options)
raw_shape_count = u.GeometryScript_Collision.get_simple_collision_shape_count(collision)
if raw_shape_count > 512:
    raise RuntimeError("Staff collision proxy still has too many disconnected hulls: " + str(raw_shape_count))
# GenerateCollisionFromMesh's MaxShapeCount filters by volume. On this mesh it
# discarded the entire slender shaft and kept only eight skull fragments.
# Merge complete hulls instead: all source support geometry remains present.
stage("MergeCompleteHulls", raw_shape_count=raw_shape_count)
collision, has_merged = u.GeometryScript_Collision.merge_simple_collision_shapes(
    collision, u.GeometryScriptMergeSimpleCollisionOptions(
        max_shape_count=8, consider_all_possible_merges=True,
        compute_negative_space=False))
shape_count = u.GeometryScript_Collision.get_simple_collision_shape_count(collision)
if shape_count <= 0:
    raise RuntimeError("Staff convex collision authoring produced no shapes")

def vector(v):
    return [v.x, v.y, v.z]

stage("ReadProducedCoverage", shape_count=shape_count)
collision_mesh = u.GeometryScript_Primitives.append_simple_collision_shapes(
    u.DynamicMesh(), u.GeometryScriptPrimitiveOptions(), u.Transform(), collision,
    u.GeometryScriptSimpleCollisionTriangulationOptions())
collision_mesh, positions, gaps = u.GeometryScript_MeshQueries.get_all_vertex_positions(
    collision_mesh, True)
points = [vector(v) for v in u.GeometryScript_List.convert_vector_list_to_array(positions)]
collision_bounds = {
    "min": [min(v[i] for v in points) for i in range(3)],
    "max": [max(v[i] for v in points) for i in range(3)],
}
visual_box = mesh.get_bounding_box()
visible_bounds = {"min": vector(visual_box.min), "max": vector(visual_box.max)}
if (collision_bounds["min"][2] > visible_bounds["min"][2] + 1.0 or
        collision_bounds["max"][2] < visible_bounds["max"][2] - 1.0):
    raise RuntimeError("Complete staff collision was not produced: " + str(collision_bounds))
stage("ApplyCollision", shape_count=shape_count, bounds=collision_bounds)
u.GeometryScript_Collision.set_simple_collision_of_static_mesh(
    collision, mesh, u.GeometryScriptSetSimpleCollisionOptions(emit_transaction=False))
body = mesh.get_editor_property("body_setup")
body.set_editor_property("collision_trace_flag", u.CollisionTraceFlag.CTF_USE_SIMPLE_AND_COMPLEX)
material = u.load_asset(MATERIAL)
if material is None:
    material = u.AssetToolsHelpers.get_asset_tools().create_asset(
        MATERIAL.rsplit("/", 1)[1], MATERIAL.rsplit("/", 1)[0],
        u.PhysicalMaterial, u.PhysicalMaterialFactoryNew())
if material is None:
    raise RuntimeError("Could not create staff physical material")
material.set_editor_property("friction", .65)
material.set_editor_property("restitution", .08)
material.set_editor_property("density", .7)
body.set_editor_property("phys_material", material)
LIB.set_metadata_tag(mesh, "Source", SOURCE + "; original visual mesh and materials preserved")
LIB.set_metadata_tag(mesh, "Physics", "Complete shaft and skull convex collision; merge to 8 hulls without volume filtering; natural gravity release")
stage("SaveAssets")
if not LIB.save_loaded_asset(material, False):
    raise RuntimeError("Staff physical material save failed")
if not LIB.save_loaded_asset(mesh, False):
    raise RuntimeError("Staff physics mesh save failed")
receipt = {
    "source": SOURCE, "asset": mesh.get_path_name(),
    "physical_material": material.get_path_name(),
    "convex_hulls": shape_count, "unmerged_convex_hulls": raw_shape_count,
    "collision_merged": has_merged,
    "source_components_before_weld": components_before,
    "collision_components_after_weld": components_after,
    "collision_proxy_weld_tolerance_cm": .001,
    "collision_bounds": collision_bounds, "visible_bounds": visible_bounds,
    "collision_recipe": "All components first; merge hulls, never filter by largest volume",
    "mass_kg_runtime": 2.5, "friction": .65, "restitution": .08,
    "saved": True, "runtime_tested": False, "editor_gui_launched": False,
}
(ROOT / "Receipts/assets.json").write_text(json.dumps(receipt, indent=2), encoding="utf-8")
CURRENT_RECEIPTS.mkdir(parents=True, exist_ok=True)
(CURRENT_RECEIPTS / "staff-collision.json").write_text(json.dumps(receipt, indent=2), encoding="utf-8")
print("WITCH_STAFF_ASSETS " + json.dumps(receipt))
stage("Saved", shape_count=shape_count, bounds=collision_bounds)
