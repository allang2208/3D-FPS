import hashlib
import json
import os
import unreal

PNG_PATH = r"D:/FPS3D/FPSGAME/Content/ColdSteelData/Skills/absolute_zero_cold_steel.png"
DEST_PATH = "/Game/ColdSteelData/Skills"
ASSET_NAME = "absolute_zero_cold_steel"
ASSET_PATH = f"{DEST_PATH}/{ASSET_NAME}"
RECEIPT_PATH = r"F:/FPSGAMEData/ArtProduction/AbsoluteZero/AbsoluteZeroV1-20261126/published.json"


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    assert os.path.exists(PNG_PATH), f"Missing icon PNG: {PNG_PATH}"
    task = unreal.AssetImportTask()
    task.filename = PNG_PATH
    task.destination_path = DEST_PATH
    task.destination_name = ASSET_NAME
    task.automated = True
    task.replace_existing = True
    task.save = False
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])

    tex = unreal.EditorAssetLibrary.load_asset(ASSET_PATH)
    assert tex is not None, f"Failed to load imported texture: {ASSET_PATH}"
    ref = unreal.EditorAssetLibrary.load_asset("/Game/ColdSteelData/Skills/blizzard_cold_steel")
    if ref is not None:
        for prop in ("compression_settings", "lod_group", "srgb", "never_stream", "mip_gen_settings"):
            tex.set_editor_property(prop, ref.get_editor_property(prop))
    else:
        tex.set_editor_property("compression_settings", unreal.TextureCompressionSettings.TC_EDITOR_ICON)
        tex.set_editor_property("lod_group", unreal.TextureGroup.TEXTUREGROUP_UI)
        tex.set_editor_property("srgb", True)
        tex.set_editor_property("never_stream", True)
        tex.set_editor_property("mip_gen_settings", unreal.TextureMipGenSettings.TMGS_NO_MIPMAPS)
    assert unreal.EditorAssetLibrary.save_loaded_asset(tex, False), f"Failed to save {ASSET_PATH}"

    uasset_path = r"D:/FPS3D/FPSGAME/Content/ColdSteelData/Skills/absolute_zero_cold_steel.uasset"
    os.makedirs(os.path.dirname(RECEIPT_PATH), exist_ok=True)
    receipt = {
        "feature": "AbsoluteZero",
        "revision": "AbsoluteZeroV1-20261126",
        "skillId": "absoluteZero",
        "iconPng": PNG_PATH,
        "iconPngSha256": sha256(PNG_PATH),
        "iconAsset": ASSET_PATH,
        "iconUasset": uasset_path,
        "iconUassetSha256": sha256(uasset_path) if os.path.exists(uasset_path) else "",
        "reusedApprovedAssets": [
            "/Game/Skills/Blizzard/IndoorV5/M_BlizzardGroundFrost.M_BlizzardGroundFrost",
            "/Game/Skills/Blizzard/IndoorV5/M_BlizzardAimPreview.M_BlizzardAimPreview",
            "/Game/Skills/IceWall/FabIceV3/M_IceWall.M_IceWall",
            "/Game/Skills/IceSpike/FrostV2/M_IceShell.M_IceShell",
            "/Game/Skills/IceSpike/FrostV2/M_IceHeart.M_IceHeart",
            "/Game/Skills/IceSpike/FrostV2/SM_IceSpike_01.SM_IceSpike_01",
            "/Game/Skills/IceSpike/FrostV2/SM_IceSpike_02.SM_IceSpike_02",
            "/Game/Skills/IceSpike/FrostV2/SM_IceSpike_03.SM_IceSpike_03",
            "/Game/Skills/IceSpike/SM_IceShard.SM_IceShard",
            "/Game/Skills/IceWall/SlamV3/NS_IceWallLanding.NS_IceWallLanding",
            "/Game/Skills/IceSpike/FrostV2/NS_FrostCrystals.NS_FrostCrystals",
            "/Game/Skills/IceArmor20261017/CrystalV2/NS_IceArmor_Condensation.NS_IceArmor_Condensation",
            "/Game/Skills/IceSpike/P_IceSpikeImpact.P_IceSpikeImpact",
            "/Game/Skills/Blizzard/StormV2/S_BlizzardIceLanding.S_BlizzardIceLanding",
            "/Game/Skills/IceSpike/S_IceImpact.S_IceImpact",
            "/Game/Skills/IceWall/BlockV1/S_IceWallCast.S_IceWallCast",
            "/Game/Skills/IceWall/FabIceV3/SM_IceBlock_01.SM_IceBlock_01",
        ],
    }
    with open(RECEIPT_PATH, "w", encoding="utf-8") as f:
        json.dump(receipt, f, ensure_ascii=False, indent=2)
    unreal.log(f"ABSOLUTE_ZERO_ICON_IMPORT_OK {ASSET_PATH} sha256={receipt['iconUassetSha256']}")


main()
