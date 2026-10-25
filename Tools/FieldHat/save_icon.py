"""Save the field hat live-preview icon mesh and UI texture."""
import hashlib
import json
import shutil
from pathlib import Path

import unreal as u

P = Path("D:/FPS3D/FPSGAME")
SRC = P / "SourceAssets/FieldHat20261019"
DEST = "/Game/Characters/ModularOutfit20260924/FieldHat20261019"
E = u.EditorAssetLibrary
A = u.AssetToolsHelpers.get_asset_tools()
G = u.GeometryScript_AssetUtils


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def dynamic(d):
    positions = []
    normals = []
    uv = []
    triangles = []
    lookup = {}
    for fi, face in enumerate(d["triangles"]):
        row = []
        for ci, vi in enumerate(face):
            n = d["normals"][fi][ci]
            tex = d["uv"][fi][ci]
            key = (vi, *[round(v, 7) for v in n + tex])
            if key not in lookup:
                lookup[key] = len(positions)
                positions.append(u.Vector(*d["positions"][vi]))
                normals.append(u.Vector(*n))
                uv.append(u.Vector2D(*tex))
            row.append(lookup[key])
        triangles.append(u.IntVector(*row))
    dm = u.DynamicMesh()
    u.GeometryScript_MeshEdits.append_buffers_to_mesh(
        dm, u.GeometryScriptSimpleMeshBuffers(vertices=positions, normals=normals, uv0=uv, triangles=triangles), 0, True)
    for fi, slot in enumerate(d["triangle_materials"]):
        u.GeometryScript_Materials.set_triangle_material_id(dm, fi, slot, True)
    return dm


def apply_item(key, item=None):
    if "-run=" not in u.SystemLibrary.get_command_line().lower():
        level = u.get_editor_subsystem(u.LevelEditorSubsystem)
        if level and level.is_in_play_in_editor():
            raise RuntimeError("Preserve currently loaded UI assets during PIE")
    saved = read(SRC / "saved_assets.json")
    item = item or read(P / "Content/ColdSteelData/items.json")[key]
    fallback = P / "Content/ColdSteelData/Icons" / (key + ".png")
    fallback.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(SRC / (key + ".png"), fallback)
    raw = (SRC / (key + "-display.json")).read_bytes()
    d = json.loads(raw)
    mesh = u.load_asset(saved["icon"])
    if not mesh:
        raise RuntimeError("Icon placeholder was not created: " + str(saved["icon"]))
    old_slots = list(mesh.static_materials)
    dm = dynamic(d)
    pose = u.Rotator(pitch=item.get("ue_icon_pitch", 0), yaw=item.get("ue_icon_yaw", -90), roll=item.get("ue_icon_roll", 0))
    u.GeometryScript_MeshTransforms.inverse_transform_mesh(dm, u.Transform(rotation=pose))
    _, status = G.copy_mesh_to_static_mesh(
        dm, mesh, u.GeometryScriptCopyMeshToAssetOptions(enable_recompute_normals=False, enable_recompute_tangents=True),
        u.GeometryScriptMeshWriteLOD())
    if status != u.GeometryScriptOutcomePins.SUCCESS:
        raise RuntimeError("Cannot save display geometry " + key)
    mesh.set_editor_property("static_materials", old_slots)
    options = u.StaticMeshReductionOptions()
    options.auto_compute_lod_screen_size = False
    options.reduction_settings = [u.StaticMeshReductionSettings(percent_triangles=p, screen_size=s)
                                  for p, s in ((1.0, 1.0), (0.55, 0.18), (0.3, 0.07))]
    subsystem = u.get_editor_subsystem(u.StaticMeshEditorSubsystem) or u.new_object(u.StaticMeshEditorSubsystem)
    subsystem.set_lods(mesh, options)
    E.set_metadata_tag(mesh, "InventoryIconRevision", "FieldHatStandard20261019")
    E.set_metadata_tag(mesh, "InventoryDisplaySHA", hashlib.sha256(raw).hexdigest())
    if not E.save_loaded_asset(mesh, False):
        raise RuntimeError("Display asset was not saved " + key)
    texture_path = saved["icon_texture"].split(".")[0]
    folder, name = texture_path.rsplit("/", 1)
    task = u.AssetImportTask()
    task.filename = str(SRC / (key + ".png"))
    task.destination_path = folder
    task.destination_name = name
    task.automated = True
    task.replace_existing = True
    task.save = False
    A.import_asset_tasks([task])
    tex = u.load_asset(texture_path)
    for prop, value in dict(lod_group=u.TextureGroup.TEXTUREGROUP_UI,
                            compression_settings=u.TextureCompressionSettings.TC_EDITOR_ICON,
                            mip_gen_settings=u.TextureMipGenSettings.TMGS_NO_MIPMAPS,
                            srgb=True).items():
        tex.set_editor_property(prop, value)
    if not E.save_loaded_asset(tex, False):
        raise RuntimeError("UI texture was not saved " + key)
    receipt = SRC / "saved_icons.json"
    result = read(receipt) if receipt.exists() else {}
    result[key] = dict(display_mesh=mesh.get_path_name(), texture=tex.get_path_name(),
                       png_sha256=hashlib.sha256((SRC / (key + ".png")).read_bytes()).hexdigest(),
                       runtime_fallback=str(fallback), catalog_rotation=[pose.pitch, pose.yaw, pose.roll],
                       runtime_tested=False)
    receipt.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print("FIELD_HAT_UI_ASSETS_SAVED", key, flush=True)
    return result[key]