"""Build the intact Meshy wall and its nine fracture groups in a staged UE project."""
import gc
import hashlib
import json
import os
from pathlib import Path
import sys
import unreal as ue

PROJECT = Path(os.environ["HIGH_VILLAGE_PROJECT"])
RUN = Path(os.environ["STONE_RELIEF_GEOMETRY_WORK"])
DESIGN = PROJECT / "SourceAssets/HillsVillageHighWall20261120/Design01"
sys.path[:0] = [str(DESIGN), str(PROJECT / "Tools/WorldGeneration/VillageMasonry")]
import author_masonry as masonry
import author_wall_fracture as fracture
import wall_shard_geometry as rock
from stone_relief_geometry import scan_parameters
from stone_relief_geometry_bake import height_field, move_stone
from stone_reference import StoneReference, require

HILLS = "/Game/WorldGeneration/TemperateHills/"
EDITOR = (ue.get_editor_subsystem(ue.StaticMeshEditorSubsystem)
          or ue.get_default_object(ue.StaticMeshEditorSubsystem))
LIB = ue.EditorAssetLibrary


def intact_mesh(groups, slots):
    mesh = ue.DynamicMesh()
    for i, slot in enumerate(slots):
        positions, normals, uvs, faces = groups[slot]
        buf = ue.GeometryScriptSimpleMeshBuffers()
        buf.vertices = [ue.Vector(*p) for p in positions]
        buf.normals = [ue.Vector(*p) for p in normals]
        buf.uv0 = [ue.Vector2D(*uv) for uv in uvs]
        buf.uv1 = [ue.Vector2D(max(0., p[2]) / 170., 0.) for p in positions]
        buf.triangles = [ue.IntVector(*t) for t in faces]
        ue.GeometryScript_MeshEdits.append_buffers_to_mesh(mesh, buf, material_id=i)
    return mesh


def wall_collision(asset, boxes):
    body = asset.get_editor_property("body_setup")
    aggregate = body.get_editor_property("agg_geom")
    elements = []
    for box in boxes:
        elem = ue.KBoxElem()
        elem.set_editor_property("center", ue.Vector(*box["center"]))
        for axis, dimension in zip(("x", "y", "z"), box["size"]):
            elem.set_editor_property(axis, dimension)
        elements.append(elem)
    aggregate.set_editor_property("box_elems", elements)
    body.set_editor_property("agg_geom", aggregate)
    # Push the modified compound through BodySetup's native collision recook.
    shape = ue.GeometryScript_Collision.get_simple_collision_from_static_mesh(asset)
    ue.GeometryScript_Collision.set_simple_collision_of_static_mesh(
        shape, asset, ue.GeometryScriptSetSimpleCollisionOptions())


def relief_layers():
    fields, scales, cache = {}, {}, {}
    for material, params in scan_parameters().items():
        fields[material], scales[material] = [], []
        for layer in ("TS00", "TS01"):
            height = params["textures"][layer + "_BaseColor"].rsplit("_", 1)[0] + "_Height"
            if height not in cache:
                cache[height] = height_field(height)
            fields[material].append(cache[height])
            scales[material].append(params["scales"][layer + "_Triplanar_TileSize"])
    return fields, scales


def build():
    file = RUN / "Authored/SM_HighWall.meshzip"
    digest = hashlib.sha256(file.read_bytes()).hexdigest()
    spec, wall_groups = rock.read_wall(file)
    parts = rock.partition(file)
    reference = StoneReference()
    fields, scales = relief_layers()
    saved = []
    names = ["SM_HighWall"] + [f"SM_HighWallShard_{i:02d}" for i in range(len(parts))]
    for i, name in enumerate(names):
        raw_folder = "HighVillageDefense/" if i == 0 else "HighVillageDefense/Fracture/"
        raw, base, relief = [require(HILLS + folder + name) for folder in
                             (raw_folder, "VillageMasonry/", "VillageMasonry/ReliefMeshes/")]
        slots = [str(s.material_slot_name) for s in raw.static_materials]
        for asset in (base, relief):
            if [str(s.material_slot_name) for s in asset.static_materials] != slots:
                raise RuntimeError("Material section order changed on " + asset.get_path_name())
        dm = intact_mesh(wall_groups, slots) if i == 0 else fracture.mesh_from_groups(parts[i-1], slots)
        raw_count = dm.get_triangle_count()
        masonry.copy_to_asset(dm, raw)
        if i == 0:
            wall_collision(raw, spec["boxes"])
        else:
            EDITOR.remove_collisions(raw)
            if EDITOR.add_simple_collisions(raw, ue.ScriptCollisionShapeType.NDOP18) < 0:
                raise RuntimeError("Could not recook fracture collision: " + name)
        collision = ue.GeometryScript_Collision.get_simple_collision_from_static_mesh(raw)
        # Painting happens on the original vertex seams, before the relief baker
        # welds edges and adds its scan detail. Keep all existing material bindings.
        masonry.paint_existing(dm, reference, [masonry.replacement(slot, False) for slot in slots])
        masonry.copy_to_asset(dm, base)
        material_names = [s.material_interface.get_name() for s in base.static_materials]
        stats = move_stone(dm, name, material_names, fields, scales)
        masonry.copy_to_asset(dm, relief)
        for asset in (base, relief):
            ue.GeometryScript_Collision.set_simple_collision_of_static_mesh(
                collision, asset, ue.GeometryScriptSetSimpleCollisionOptions())
        relief.set_editor_property("complex_collision_mesh", base)
        tag = "VillageSourceSHA" if i == 0 else "VillageIntactWallSHA"
        rows = []
        for asset in (raw, base, relief):
            if i:
                fracture.set_fragment_lods(EDITOR, asset)
            LIB.set_metadata_tag(asset, tag, digest)
            if not LIB.save_loaded_asset(asset, False):
                raise RuntimeError("Could not save " + asset.get_path_name())
            rows.append(dict(path=asset.get_path_name(), nanite=asset.get_editor_property('nanite_settings').enabled,
                             lod_triangles=[asset.get_num_triangles(j) for j in range(asset.get_num_lods())]))
        saved.append(dict(name=name, raw_triangles=raw_count, stages=rows, relief=stats))
        ue.log("BATTLEMENT_SAVED " + name + " " + str(rows[-1]["lod_triangles"]))
        del dm, collision
        gc.collect()
        ue.SystemLibrary.collect_garbage()
    (RUN / "saved.json").write_text(json.dumps(dict(source_sha256=digest, boxes=spec["boxes"],
        materials=spec["materials"], meshes=saved), indent=2), encoding="utf-8")


build()
