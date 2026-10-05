"""Archive user-supplied M-14 Meshy source and create an editable Blender source.
Run with Blender --background --factory-startup --python-exit-code 1 --python.
This preparation does not alter geometry, reduce polygons, rig, render, or import UE assets.
"""
from pathlib import Path
import json
import struct
import shutil
import hashlib
import bpy

PROJECT = Path("D:/FPS3D/FPSGAME")
INPUT = Path("C:/Users/allan/Downloads/Meshy_AI_Veiled_Maw_M_14_1004025810_texture.glb")
DEST = PROJECT / "SourceAssets/SpiralPillarM14Meshy20261004"
RAW = DEST / "Original" / INPUT.name
BLEND = DEST / "Authoring/M14_Meshy_Source_v01.blend"
TEXTURES = DEST / "Textures"
REPORT = DEST / "source_manifest.json"

def main():
    for directory in (RAW.parent, BLEND.parent, TEXTURES):
        directory.mkdir(parents=True, exist_ok=True)
    if RAW.exists() or BLEND.exists() or REPORT.exists():
        raise RuntimeError("Preparation output already exists; keep it and choose a new revision.")
    shutil.copy2(INPUT, RAW)
    data = RAW.read_bytes()
    magic, version, total_bytes = struct.unpack_from("<4sII", data, 0)
    if magic != b"glTF" or version != 2:
        raise ValueError("Unsupported source container.")
    offset = 12
    gltf = None
    binary = None
    while offset < total_bytes:
        length, kind = struct.unpack_from("<II", data, offset)
        offset += 8
        chunk = data[offset:offset + length]
        offset += length
        if kind == 0x4E4F534A:
            gltf = json.loads(chunk.decode("utf-8"))
        elif kind == 0x004E4942:
            binary = chunk
    if gltf is None or binary is None:
        raise ValueError("Source is missing glTF JSON or embedded binary data.")
    (DEST / "source_gltf.json").write_text(json.dumps(gltf, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    texture_roles = {}
    def register(texture_info, role):
        if texture_info is not None:
            tex = gltf["textures"][texture_info["index"]]
            texture_roles.setdefault(tex["source"], []).append(role)
    for material in gltf.get("materials", []):
        pbr = material.get("pbrMetallicRoughness", {})
        register(pbr.get("baseColorTexture"), "BaseColor")
        register(pbr.get("metallicRoughnessTexture"), "MetallicRoughness")
        register(material.get("normalTexture"), "Normal")
        register(material.get("occlusionTexture"), "Occlusion")
    extracted = []
    for index, image in enumerate(gltf.get("images", [])):
        view = gltf["bufferViews"][image["bufferView"]]
        start = view.get("byteOffset", 0)
        payload = binary[start:start + view["byteLength"]]
        roles = texture_roles.get(index, [f"Image{index:02d}"])
        ext = {"image/jpeg": ".jpg", "image/png": ".png"}[image["mimeType"]]
        output = TEXTURES / ("T_M14_" + "_".join(roles) + ext)
        output.write_bytes(payload)
        extracted.append({"image_index": index, "roles": roles,
                          "file": output.relative_to(DEST).as_posix(),
                          "mime_type": image["mimeType"], "bytes": len(payload)})

    primitive_inventory = []
    for mesh_index, mesh in enumerate(gltf.get("meshes", [])):
        for primitive_index, primitive in enumerate(mesh["primitives"]):
            accessor = gltf["accessors"][primitive["attributes"]["POSITION"]]
            indices = gltf["accessors"][primitive["indices"]]["count"]
            primitive_inventory.append({
                "mesh": mesh_index, "primitive": primitive_index,
                "position_accessor_vertices": accessor["count"],
                "triangles": indices // 3 if primitive.get("mode", 4) == 4 else None,
                "material": primitive.get("material"),
                "source_position_min": accessor.get("min"),
                "source_position_max": accessor.get("max"),
                "attributes": list(primitive["attributes"]),
            })

    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(RAW), merge_vertices=False, import_pack_images=True)
    mesh_objects = [obj for obj in bpy.context.scene.objects if obj.type == "MESH"]
    inventory = []
    for index, obj in enumerate(mesh_objects):
        obj.name = f"M14_Meshy_Original_{index:02d}"
        obj["source_asset"] = RAW.relative_to(PROJECT).as_posix()
        obj["authoring_stage"] = "unaltered_source"
        obj["semantic_split_complete"] = False
        inventory.append({
            "object": obj.name,
            "vertices": len(obj.data.vertices),
            "polygons": len(obj.data.polygons),
            "dimensions_blender": list(obj.dimensions),
            "material_slots": len(obj.material_slots),
        })
    images = []
    for image in bpy.data.images:
        if image.type == "IMAGE":
            if not image.packed_file:
                image.pack()
            images.append({"name": image.name, "size_pixels": list(image.size)})
    bpy.context.scene["asset_id"] = "SpiralPillarM14"
    bpy.context.scene["source_notes"] = "User-provided Meshy high-poly; original import scale retained. Not rigged or semantically split."
    bpy.ops.wm.save_as_mainfile(filepath=str(BLEND))
    manifest = {
        "asset_id": "SpiralPillarM14", "display_name": "M-14 螺柱者",
        "date_local": "2026-10-04", "timezone": "Asia/Shanghai",
        "source": {
            "provided_by": "user", "provider_label": "Meshy",
            "original_path": str(INPUT), "archived_file": RAW.relative_to(DEST).as_posix(),
            "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest(),
            "generator": gltf.get("asset", {}).get("generator"),
            "rights": "User-supplied local asset; generation plan and redistribution rights not established."
        },
        "gltf": {
            "meshes": len(gltf.get("meshes", [])), "materials": len(gltf.get("materials", [])),
            "skins": len(gltf.get("skins", [])), "animations": len(gltf.get("animations", [])),
            "primitives": primitive_inventory,
            "alpha_mode": [m.get("alphaMode", "OPAQUE") for m in gltf.get("materials", [])],
            "double_sided": [m.get("doubleSided", False) for m in gltf.get("materials", [])],
        },
        "textures": extracted,
        "texture_channel_notes": {
            "BaseColor": "sRGB source color",
            "MetallicRoughness": "Linear data: G=roughness, B=metallic; source has no occlusionTexture binding, so R is not declared AO.",
            "Normal": "glTF tangent-space normal; preserve source and perform target convention conversion only during UE material preparation."
        },
        "authoring": {
            "blend": BLEND.relative_to(DEST).as_posix(), "blender_version": bpy.app.version_string,
            "geometry_modified": False, "scale_modified": False, "textures_packed": True,
            "objects": inventory, "images": images,
        },
        "status": {
            "source_archived": True, "editable_blender_source_saved": True,
            "semantic_parts_created": False, "retopology_done": False, "rig_created": False,
            "animations_created": False, "ue_assets_imported": False, "runtime_integrated": False,
            "rendered": False, "tested": False
        },
        "plan": "../../Docs/Monsters/SpiralPillarM14Plan20261004.md"
    }
    REPORT.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("M14_SOURCE_PREPARED " + json.dumps({
        "blend": str(BLEND), "manifest": str(REPORT),
        "triangles": sum(p["triangles"] or 0 for p in primitive_inventory),
        "textures": images
    }, ensure_ascii=True))

if __name__ == "__main__":
    main()
