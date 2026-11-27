"""Hills (L_ForestPathVillage) GPU / VSM / VRAM optimization pass (R50).

Addresses the root bottlenecks captured in F6 PIE exports + engine.utrace:
  Pass A: Disable Nanite Tessellation (bEnableTessellation=False) on Hills Nanite terrain masters
          (eliminates SW Rasterize Patches in VisBuffer & VSM ShadowDepths while preserving
           bUsedWithNanite=True, normal maps, parallax relief, and baked height relief).
  Pass B: Cap missed 8K/4K resident textures across SpringGrass, CommonHazel/EuropeanHornbeam masks,
          ForestPathStudy/ForestFloor, PN_FoliageCollection, and UnrealNormandy.
  Pass C: Set bUsedWithInstancedStaticMeshes=True on 5 village prop materials logging shader recompiles.
"""
import datetime
import hashlib
import json
import os
import shutil
from pathlib import Path

import unreal as u

PROJECT_ROOT = Path("D:/FPS3D/FPSGAME")
CONTENT_ROOT = PROJECT_ROOT / "Content"
BATCH_DIR = Path(os.environ.get("FPS_HILLS_R50_BATCH", "F:/FPSGAMEData/ArtProduction/HillsForestPath/HillsPerfOpt-R50"))
BEFORE_CONTENT = BATCH_DIR / "Before" / "Content"

lib = u.EditorAssetLibrary
mat_ed = u.MaterialEditingLibrary

TERRAIN_MASTERS = [
    "/Game/ForestPathStudy/VillageRegion/Reference/M_ForestReferenceMesh",
    "/Game/ForestPathStudy/VillageRegion/Reference/TrailCover/M_ForestVillageLandscape",
    "/Game/ForestPathStudy/VillageRegion/SurfaceSample/M_ForestVillageFringe",
    "/Game/ForestPathStudy/VillageRegion/WildGrass/M_ForestPathRoadVerge",
    "/Game/WorldGeneration/TemperateHills/EastRiverRoad/M_EastRoad_Sensei",
]

TERRAIN_INSTANCES = [
    "/Game/ForestPathStudy/VillageRegion/Reference/MI_ForestReference",
    "/Game/ForestPathStudy/VillageRegion/Reference/Terrain/MI_ForestTilePacked",
    "/Game/ForestPathStudy/VillageRegion/Reference/TrailCover/MI_ForestVillageLandscape",
    "/Game/ForestPathStudy/VillageRegion/SurfaceSample/MI_ForestVillageFringe",
    "/Game/ForestPathStudy/VillageRegion/SurfaceSample/MI_ForestSamplePalette",
    "/Game/ForestPathStudy/VillageRegion/Reference/MI_ForestVillageMudRoad",
    "/Game/WorldGeneration/TemperateHills/EastRiverRoad/MI_EastRiverRoad",
]

SPECIES_INSPECT_INSTANCES = [
    "/Game/WorldGeneration/TemperateHills/ForestSpecies20261110/Materials/MI_Common_Hazel_Bark_01",
    "/Game/WorldGeneration/TemperateHills/ForestSpecies20261110/Materials/MI_Common_Hazel_Foliage_01",
    "/Game/WorldGeneration/TemperateHills/ForestSpecies20261110/Materials/MI_European_Beech_Bark_01",
    "/Game/WorldGeneration/TemperateHills/ForestSpecies20261110/Materials/MI_European_Beech_Foliage_01",
]

EXPLICIT_TEX_CAPS = [
    ("/Game/PN_GrassLibrary/Textures/grassTextures/MasterTextures/springGrass_Albedo_8k_I", 2048, True),
    ("/Game/PN_GrassLibrary/Textures/grassTextures/MasterTextures/springGrass_Normal_springGrass_8k", 2048, True),
    ("/Game/PN_GrassLibrary/Textures/grassTextures/MasterTextures/springGrass_Opacity_8k", 4096, False),
    ("/Game/ForestPathStudy/Materials/T_rbpir_BaseOpacity", 1024, False),
    ("/Game/ForestPathStudy/Materials/T_rbcuh_BaseOpacity", 1024, False),
    ("/Game/ForestPathStudy/Materials/T_tjtjfinia_BaseOpacity", 2048, False),
    ("/Game/ForestPathStudy/Materials/T_NordicForestGroundRootsCoarse_Normal", 2048, False),
    ("/Game/ForestPathStudy/VillageRegion/ForestFloor/T_ForestFloor_Normal", 2048, False),
    ("/Game/ForestPathStudy/VillageRegion/ForestFloor/T_ForestFloor_ARH", 2048, False),
    ("/Game/ForestPathStudy/VillageRegion/ForestFloor/T_ForestFloor_Color", 2048, False),
    ("/Game/PN_FoliageCollection/Textures/FlowerTextures/MasterTextures/Combined_Flowers_A", 2048, True),
    ("/Game/PN_FoliageCollection/Textures/FlowerTextures/MasterTextures/Combined_Flowers_N", 2048, True),
    ("/Game/PN_FoliageCollection/Textures/groundPlantTextures/MasterTextures/Foilage_Ground_Main_A", 2048, True),
    ("/Game/PN_FoliageCollection/Textures/groundPlantTextures/MasterTextures/Foilage_Ground_Main_N", 2048, True),
]

ISM_PROP_MATERIALS = [
    "/Game/Items/Consumables/Baguette20261003/Materials/M_Baguette",
    "/Game/Items/Consumables/Bread20261003/Materials/M_Bread",
    "/Game/Props/GamedevTreasureChestV3_20261004/Materials/M_TreasureV3_Gold",
    "/Game/Props/GamedevTreasureChestV3_20261004/Materials/M_TreasureV3_Iron",
    "/Game/Props/GamedevTreasureChestV3_20261004/Materials/M_TreasureV3_Wood",
]


def pkg_to_disk(pkg_path: str) -> Path:
    clean = pkg_path.split(".")[0]
    if not clean.startswith("/Game/"):
        raise ValueError(f"Expected /Game/ path: {pkg_path}")
    return CONTENT_ROOT / (clean[6:] + ".uasset")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while True:
            chunk = f.read(1024 * 1024)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


class ReceiptRecorder:
    def __init__(self):
        self.backed_up = {}

    def backup_before(self, pkg_path: str) -> dict:
        clean = pkg_path.split(".")[0]
        src = pkg_to_disk(clean)
        if not src.exists():
            raise FileNotFoundError(f"Asset file missing on disk: {src}")
        rel = clean[6:] + ".uasset"
        dst = BEFORE_CONTENT / rel
        if clean not in self.backed_up:
            before_sha = sha256_file(src)
            if not dst.exists():
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dst)
                for ext in (".uexp", ".ubulk", ".uptnl"):
                    side_src = src.with_suffix(ext)
                    if side_src.exists():
                        shutil.copy2(side_src, dst.with_suffix(ext))
            self.backed_up[clean] = {
                "package": clean,
                "disk_path": str(src),
                "backup_path": str(dst),
                "before_sha256": before_sha,
            }
        return self.backed_up[clean]

    def finalize_hashes(self):
        records = []
        for dst in sorted(BEFORE_CONTENT.rglob("*.uasset")):
            rel = dst.relative_to(BEFORE_CONTENT)
            clean = "/Game/" + rel.with_suffix("").as_posix()
            src = CONTENT_ROOT / rel
            records.append({
                "package": clean,
                "disk_path": str(src),
                "backup_path": str(dst),
                "before_sha256": sha256_file(dst),
                "after_sha256": sha256_file(src) if src.exists() else None,
            })
        return records


def save_asset(obj):
    if not lib.save_loaded_asset(obj, False):
        raise RuntimeError(f"Failed to save asset: {obj.get_path_name()}")


def read_displacement_scaling(mat) -> dict:
    ds = mat.get_editor_property("displacement_scaling")
    return {
        "magnitude": float(ds.get_editor_property("magnitude")),
        "center": float(ds.get_editor_property("center")),
    }


def pass_a_terrain_tessellation(recorder: ReceiptRecorder) -> dict:
    masters_report = []
    for path in TERRAIN_MASTERS:
        if not lib.does_asset_exist(path):
            raise RuntimeError(f"Missing required terrain master material: {path}")
        mat = u.load_asset(path)
        if not isinstance(mat, u.Material):
            raise RuntimeError(f"Not a UMaterial: {path}")

        before = {
            "enable_tessellation": bool(mat.get_editor_property("enable_tessellation")),
            "used_with_nanite": bool(mat.get_editor_property("used_with_nanite")),
            "displacement_scaling": read_displacement_scaling(mat),
        }
        disp = before["displacement_scaling"]
        if disp["center"] < 0.4 or disp["center"] > 0.6:
            if abs(disp["magnitude"]) >= 10.0:
                raise RuntimeError(
                    f"Unexpected displacement center={disp['center']} magnitude={disp['magnitude']} on {path}"
                )

        changed = False
        if before["enable_tessellation"]:
            recorder.backup_before(path)
            mat.modify()
            mat.set_editor_property("enable_tessellation", False)
            errors = mat_ed.recompile_material(mat)
            if errors:
                raise RuntimeError(f"Material recompile error on {path}: {errors}")
            save_asset(mat)
            changed = True

        after = {
            "enable_tessellation": bool(mat.get_editor_property("enable_tessellation")),
            "used_with_nanite": bool(mat.get_editor_property("used_with_nanite")),
            "displacement_scaling": read_displacement_scaling(mat),
        }
        if after["enable_tessellation"] or not after["used_with_nanite"]:
            raise RuntimeError(f"Post-save validation failed on {path}: {after}")

        masters_report.append({"package": path, "changed": changed, "before": before, "after": after})
        u.log(f"[R50-PASS-A] Master {path} changed={changed} tess={before['enable_tessellation']}->{after['enable_tessellation']} nanite={after['used_with_nanite']} disp={before['displacement_scaling']}")

    instances_report = []
    for path in TERRAIN_INSTANCES:
        if not lib.does_asset_exist(path):
            instances_report.append({"package": path, "exists": False})
            continue
        mi = u.load_asset(path)
        if not isinstance(mi, u.MaterialInstance):
            instances_report.append({"package": path, "exists": True, "type": str(type(mi)), "skipped": True})
            continue
        overrides = mi.get_editor_property("base_property_overrides")
        override_disp = bool(overrides.get_editor_property("override_displacement_scaling"))
        changed = False
        if override_disp:
            recorder.backup_before(path)
            mi.modify()
            overrides.set_editor_property("override_displacement_scaling", False)
            mi.set_editor_property("base_property_overrides", overrides)
            mat_ed.update_material_instance(mi)
            save_asset(mi)
            changed = True
        else:
            mat_ed.update_material_instance(mi)
        instances_report.append({
            "package": path,
            "exists": True,
            "override_displacement_scaling_before": override_disp,
            "changed": changed,
            "parent": mi.parent.get_path_name() if mi.parent else None,
        })

    species_inspect = []
    for path in SPECIES_INSPECT_INSTANCES:
        if not lib.does_asset_exist(path):
            species_inspect.append({"package": path, "exists": False})
            continue
        mi = u.load_asset(path)
        base = mi.get_base_material() if isinstance(mi, u.MaterialInterface) else None
        base_tess = bool(base.get_editor_property("enable_tessellation")) if isinstance(base, u.Material) else None
        species_inspect.append({
            "package": path,
            "exists": True,
            "base_material": base.get_path_name() if base else None,
            "base_enable_tessellation": base_tess,
        })
        u.log(f"[R50-INSPECT] {path} -> base={base.get_path_name() if base else None} base_tess={base_tess}")

    return {
        "masters": masters_report,
        "instances": instances_report,
        "species_inspect": species_inspect,
    }


def cap_texture(recorder: ReceiptRecorder, asset_path: str, target_max: int, ensure_stream_mips: bool = False):
    clean = asset_path.split(".")[0]
    if not lib.does_asset_exist(clean):
        return {"package": clean, "exists": False}
    tex = u.load_asset(clean)
    if not isinstance(tex, u.Texture2D):
        return {"package": clean, "exists": True, "skipped": "not_texture2d"}

    sx = int(tex.blueprint_get_size_x())
    sy = int(tex.blueprint_get_size_y())
    cur_max = int(tex.get_editor_property("max_texture_size"))
    cur_ns = bool(tex.get_editor_property("never_stream"))
    cur_mip = tex.get_editor_property("mip_gen_settings")

    need_cap = max(sx, sy) > target_max and (cur_max == 0 or cur_max > target_max)
    need_stream = ensure_stream_mips and cur_ns
    need_mips = ensure_stream_mips and (cur_mip == u.TextureMipGenSettings.TMGS_NO_MIPMAPS)

    if not (need_cap or need_stream or need_mips):
        return {
            "package": clean,
            "exists": True,
            "changed": False,
            "size": [sx, sy],
            "max_texture_size": cur_max,
            "never_stream": cur_ns,
        }

    recorder.backup_before(clean)
    tex.modify()
    if need_cap:
        tex.set_editor_property("max_texture_size", target_max)
    if need_stream:
        tex.set_editor_property("never_stream", False)
    if need_mips:
        tex.set_editor_property("mip_gen_settings", u.TextureMipGenSettings.TMGS_SIMPLE_AVERAGE)
    save_asset(tex)

    after_max = int(tex.get_editor_property("max_texture_size"))
    after_ns = bool(tex.get_editor_property("never_stream"))
    u.log(f"[R50-PASS-B] {clean} ({sx}x{sy}) max:{cur_max}->{after_max} ns:{cur_ns}->{after_ns}")
    return {
        "package": clean,
        "exists": True,
        "changed": True,
        "size": [sx, sy],
        "before": {"max_texture_size": cur_max, "never_stream": cur_ns, "mip_gen": str(cur_mip)},
        "after": {
            "max_texture_size": after_max,
            "never_stream": after_ns,
            "mip_gen": str(tex.get_editor_property("mip_gen_settings")),
        },
    }


def normandy_cap_for(asset_path: str):
    clean = asset_path.split(".")[0]
    lo = clean.split("/")[-1].lower()
    if any(k in lo for k in ("height", "cloud", "lookup", "lut", "splat", "noise", "mask")):
        return None
    if lo.startswith(("t_planttypea_", "t_planttypeb_", "t_planttypec_")):
        return 1024
    if (
        lo.endswith(("_normal", "_detailnormal_00a", "_rhaom", "_orm", "_roughness", "_ao", "_metallic"))
        or "_normal_" in lo
        or "detailnormal" in lo
    ):
        return 2048
    return None


def pass_b_texture_caps(recorder: ReceiptRecorder) -> dict:
    groups = {
        "explicit": [],
        "foliage_masks": [],
        "unreal_normandy": [],
    }

    for path, target_max, ensure_stream_mips in EXPLICIT_TEX_CAPS:
        groups["explicit"].append(cap_texture(recorder, path, target_max, ensure_stream_mips))

    for folder in ("/Game/CommonHazel/Textures", "/Game/EuropeanHornbeam/Textures"):
        if not lib.does_directory_exist(folder):
            continue
        for apath in sorted(lib.list_assets(folder, recursive=True, include_folder=False)):
            clean = apath.split(".")[0]
            name_lo = clean.split("/")[-1].lower()
            if "mask" not in name_lo:
                continue
            target_max = 2048 if "twosided" in clean.lower() else 1024
            groups["foliage_masks"].append(cap_texture(recorder, clean, target_max, False))

    normandy_dir = "/Game/UnrealNormandy/Textures"
    if lib.does_directory_exist(normandy_dir):
        for apath in sorted(lib.list_assets(normandy_dir, recursive=True, include_folder=False)):
            clean = apath.split(".")[0]
            cap = normandy_cap_for(clean)
            if cap is None:
                continue
            groups["unreal_normandy"].append(cap_texture(recorder, clean, cap, False))

    summary = {k: {"checked": len(v), "changed": sum(1 for item in v if item.get("changed"))} for k, v in groups.items()}
    u.log(f"[R50-PASS-B-SUMMARY] {json.dumps(summary)}")
    return {"summary": summary, "details": groups}


def pass_c_ism_usage(recorder: ReceiptRecorder) -> list:
    report = []
    for path in ISM_PROP_MATERIALS:
        if not lib.does_asset_exist(path):
            report.append({"package": path, "exists": False})
            continue
        mat = u.load_asset(path)
        if not isinstance(mat, u.Material):
            report.append({"package": path, "exists": True, "skipped": str(type(mat))})
            continue
        before = bool(mat.get_editor_property("used_with_instanced_static_meshes"))
        changed = False
        if not before:
            recorder.backup_before(path)
            mat.modify()
            mat.set_editor_property("used_with_instanced_static_meshes", True)
            errors = mat_ed.recompile_material(mat)
            if errors:
                raise RuntimeError(f"ISM material recompile error on {path}: {errors}")
            save_asset(mat)
            changed = True
        after = bool(mat.get_editor_property("used_with_instanced_static_meshes"))
        if not after:
            raise RuntimeError(f"Failed setting used_with_instanced_static_meshes on {path}")
        report.append({"package": path, "exists": True, "changed": changed, "before": before, "after": after})
        u.log(f"[R50-PASS-C] {path} ism={before}->{after} changed={changed}")
    return report


def main():
    BATCH_DIR.mkdir(parents=True, exist_ok=True)
    BEFORE_CONTENT.mkdir(parents=True, exist_ok=True)
    recorder = ReceiptRecorder()

    pass_a = pass_a_terrain_tessellation(recorder)
    pass_b = pass_b_texture_caps(recorder)
    pass_c = pass_c_ism_usage(recorder)
    backups = recorder.finalize_hashes()

    receipt = {
        "batch": "HillsPerfOpt-R50",
        "timestamp_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "script": "Tools/WorldGeneration/ForestVillage/optimize_hills_perf_r50.py",
        "pass_a_terrain_tessellation": pass_a,
        "pass_b_texture_caps": pass_b,
        "pass_c_ism_usage": pass_c,
        "modified_asset_count": len(backups),
        "backups_and_hashes": backups,
    }
    receipt_path = BATCH_DIR / "published.json"
    receipt_path.write_text(json.dumps(receipt, indent=2, ensure_ascii=False), encoding="utf-8")
    u.log(f"[R50-DONE] modified={len(backups)} receipt={receipt_path}")


if __name__ == "__main__":
    main()
