"""Save nine wall-space rigid groups from the intact wall's exact authored corner buffers."""
import hashlib
import json
import importlib.util
from pathlib import Path

import unreal as ue


HERE = Path(__file__).resolve().parent
ROOT = "/Game/WorldGeneration/TemperateHills/HighVillageDefense"
DEST = ROOT + "/Fracture"
WALL = ROOT + "/SM_HighWall"


def mesh_from_groups(groups, slots):
    mesh = ue.DynamicMesh()
    for i,slot in enumerate(slots):
        group = groups.get(slot)
        if not group or not group.indices:
            continue
        buf = ue.GeometryScriptSimpleMeshBuffers()
        buf.vertices = [ue.Vector(*p) for p,n,uv in group.corners]
        buf.normals = [ue.Vector(*n) for p,n,uv in group.corners]
        buf.uv0 = [ue.Vector2D(*uv) for p,n,uv in group.corners]
        buf.uv1 = [ue.Vector2D(max(0.,p[2])/170.,0.) for p,n,uv in group.corners]
        buf.triangles = [ue.IntVector(*tri) for tri in group.indices]
        ue.GeometryScript_MeshEdits.append_buffers_to_mesh(mesh,buf,material_id=i)
    return mesh


def set_fragment_lods(editor, asset):
    options = ue.StaticMeshReductionOptions()
    options.auto_compute_lod_screen_size = False
    options.reduction_settings = [
        ue.StaticMeshReductionSettings(percent_triangles=ratio, screen_size=screen)
        for ratio, screen in ((1., 1.), (.48, .17), (.18, .065))
    ]
    if editor.set_lods(asset, options) != len(options.reduction_settings):
        raise RuntimeError('Could not build fragment LODs for ' + asset.get_path_name())


def build():
    geom_spec = importlib.util.spec_from_file_location("wall_shard_geometry", HERE/"wall_shard_geometry.py")
    geometry = importlib.util.module_from_spec(geom_spec)
    geom_spec.loader.exec_module(geometry)

    library = ue.EditorAssetLibrary
    source = ue.load_asset(WALL)
    file = HERE/"Authored/SM_HighWall.meshzip"
    digest = hashlib.sha256(file.read_bytes()).hexdigest()
    if not source or str(library.get_metadata_tag(source,"VillageSourceSHA")) != digest:
        raise RuntimeError("Import the authored SM_HighWall before baking its fracture.")
    bindings = {str(s.material_slot_name): s.material_interface for s in source.static_materials}
    # Resolve the actual repaired-wall slots, including its weather-aware receivers.
    repaired = ue.load_asset("/Game/WorldGeneration/TemperateHills/VillagePerimeter/SM_VillageWallRepairedA")
    if not repaired:
        raise RuntimeError("Cannot resolve the repaired wall for the fracture's interior stone.")
    for slot in repaired.static_materials:
        bindings.setdefault(str(slot.material_slot_name),slot.material_interface)
    parts = geometry.partition(file)
    slots = list(dict.fromkeys(slot for part in parts for slot in part))
    if any(not bindings.get(slot) for slot in slots):
        raise RuntimeError(f"Missing fracture material binding: {set(slots)-bindings.keys()}")
    library.make_directory(DEST)
    mesh_editor = (ue.get_editor_subsystem(ue.StaticMeshEditorSubsystem)
                   or ue.get_default_object(ue.StaticMeshEditorSubsystem))
    saved = []
    for index, groups in enumerate(parts):
        piece = mesh_from_groups(groups, slots)
        name = f"{DEST}/SM_HighWallShard_{index:02d}"
        if not piece.get_triangle_count():
            raise RuntimeError(f"Empty wall fragment {index}")
        asset = ue.load_asset(name) if library.does_asset_exist(name) else None
        if not asset:
            options = ue.GeometryScriptCreateNewStaticMeshAssetOptions(
                enable_recompute_normals=False, enable_recompute_tangents=True,
                enable_collision=True, enable_nanite=False)
            asset, outcome = ue.GeometryScript_NewAssetUtils.create_new_static_mesh_asset_from_mesh(
                piece, name, options)
            if not asset or outcome != ue.GeometryScriptOutcomePins.SUCCESS:
                raise RuntimeError(f"Could not create {name}")
        write = ue.GeometryScriptCopyMeshToAssetOptions(
            replace_materials=True, new_materials=[bindings[s] for s in slots],
            new_material_slot_names=slots, enable_recompute_normals=False, enable_recompute_tangents=True)
        _, outcome = ue.GeometryScript_AssetUtils.copy_mesh_to_static_mesh(
            piece, asset, write, ue.GeometryScriptMeshWriteLOD(lod_index=0))
        if outcome != ue.GeometryScriptOutcomePins.SUCCESS:
            raise RuntimeError(f"Could not write fracture surface to {name}")
        mesh_editor.remove_collisions(asset)
        mesh_editor.add_simple_collisions(asset, ue.ScriptCollisionShapeType.NDOP18)
        asset.get_editor_property("body_setup").set_editor_property(
            "collision_trace_flag", ue.CollisionTraceFlag.CTF_USE_SIMPLE_AND_COMPLEX)
        set_fragment_lods(mesh_editor, asset)
        library.set_metadata_tag(asset,"VillageIntactWallSHA",digest)
        if not library.save_loaded_asset(asset, False):
            raise RuntimeError(f"Could not save {name}")
        saved.append({"mesh": asset.get_path_name(), "triangles": piece.get_triangle_count(),
                      "intact_source_sha256": digest})
    (HERE/"Authored/fracture-saved.json").write_text(json.dumps(saved,indent=2), encoding="utf-8")
    ue.log("HIGH_VILLAGE_FRACTURE_SAVED " + str(len(saved)))


if __name__ == "__main__":
    build()
