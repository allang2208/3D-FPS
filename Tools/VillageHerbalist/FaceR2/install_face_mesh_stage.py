"""Reimport the existing mesh inside a disposable project at its production package path."""
import hashlib
import json
import os
from pathlib import Path

import unreal as ue


NAME = "SK_VillageHerbalist"
DIRECTORY = "/Game/Characters/VillageHerbalist"
PACKAGE = f"{DIRECTORY}/{NAME}"
HOST = Path(os.environ["HERBALIST_MESH_HOST"]).resolve()
SOURCE = HOST / f"SourceAssets/VillageHerbalist/FullBody/FaceR2/{NAME}.fbx"
if Path(ue.Paths.convert_relative_path_to_full(ue.Paths.project_dir())).resolve() != HOST:
    raise RuntimeError("Mesh authoring must run in the disposable project")


def contract(mesh):
    component = ue.new_object(ue.SkeletalMeshComponent)
    component.set_skeletal_mesh_asset(mesh)
    bones = [component.get_bone_name(i) for i in range(component.get_num_bones())]
    tree = [[str(name), str(component.get_parent_bone(name))] for name in bones]
    subsystem = (ue.get_editor_subsystem(ue.SkeletalMeshEditorSubsystem)
                 or ue.new_object(ue.SkeletalMeshEditorSubsystem))
    lods = []
    for index in range(subsystem.get_lod_count(mesh)):
        sections = subsystem.get_num_sections(mesh, index)
        lods.append({"vertices": subsystem.get_num_verts(mesh, index),
                     "section_materials": [subsystem.get_lod_material_slot(mesh, index, section)
                                           for section in range(sections)]})
    tags = ue.AssetRegistryHelpers.create_asset_data(mesh)
    return {
        "mesh": mesh.get_path_name(), "skeleton": mesh.skeleton.get_path_name(),
        "bone_count": len(bones),
        "bone_tree_sha256": hashlib.sha256(json.dumps(tree).encode()).hexdigest(),
        "physics_asset": mesh.physics_asset.get_path_name() if mesh.physics_asset else None,
        "materials": [[str(slot.material_slot_name), slot.material_interface.get_path_name()]
                      for slot in mesh.materials],
        "lods": lods, "triangles": tags.get_tag_value("Triangles"),
    }


mesh = ue.load_asset(PACKAGE)
before = contract(mesh)
options = ue.FbxImportUI()
options.automated_import_should_detect_type = False
options.mesh_type_to_import = ue.FBXImportType.FBXIT_SKELETAL_MESH
options.import_mesh = options.import_as_skeletal = True
options.import_materials = options.import_textures = options.import_animations = False
options.create_physics_asset = False
options.skeleton = mesh.skeleton
options.skeletal_mesh_import_data = mesh.get_editor_property("asset_import_data")
task = ue.AssetImportTask()
task.filename = str(SOURCE)
task.destination_path = DIRECTORY
task.destination_name = NAME
task.options = options
task.factory = ue.FbxFactory()
task.automated = task.replace_existing = True
task.save = task.replace_existing_settings = False
ue.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
results = task.get_objects()
if len(results) != 1 or results[0].get_path_name() != before["mesh"]:
    raise RuntimeError(f"Unexpected FBX reimport result {results}")
mesh = results[0]
after = contract(mesh)
if after != before:
    raise RuntimeError(f"Mesh structure changed. Before {before}. After {after}")
if not ue.EditorAssetLibrary.save_loaded_asset(mesh, False):
    raise RuntimeError("Could not save the staged skeletal mesh")
data = ue.AssetRegistryHelpers.create_asset_data(mesh)
source_data = json.loads(data.get_tag_value("AssetImportData"))
if not any(row["FileMD5"].lower() == hashlib.md5(SOURCE.read_bytes()).hexdigest()
           and (HOST / "Content/Characters/VillageHerbalist" / row["RelativeFilename"]).resolve() == SOURCE
           for row in source_data):
    raise RuntimeError(f"Saved mesh source record does not match the requested FBX: {source_data}")
(HOST / "staged.json").write_text(json.dumps({"contract": after, "fbx_source": source_data}, indent=2),
                                   encoding="utf-8")
