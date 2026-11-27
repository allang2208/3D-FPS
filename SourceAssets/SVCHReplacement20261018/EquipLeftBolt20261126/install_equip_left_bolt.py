"""Headless UE 5.8 installer for SVCh Left-Bolt Equip across all 5 UWeaponGripProfile assets.

Preserves all 11 non-equip clips (including QuickMeleeGripR7_20261020 and reload_empty)
losslessly via live extract -> single-clip swap -> readback identity check -> save.
"""
from pathlib import Path
import hashlib
import json
import shutil
import unreal as u

OUT_DIR = Path(__file__).resolve().parent
PROJ_DIR = Path(u.Paths.project_dir()).resolve()
E = u.EditorAssetLibrary

EQUIP_CLIP = "/Game/Weapons/SVDDragunov20260922/Complete20260923/Animations/A_SVD_equip"
ART_DIR = Path(r"F:\FPSGAMEData\ArtProduction\SVCHReplacement20261018\EquipLeftBolt-20261126")
BEFORE_DIR = ART_DIR / "Before"
PUB_DIR = ART_DIR / "PublishedUAssets"
READBACK_DIR = OUT_DIR / "SavedReadback"

TARGETS = {
    "base": {
        "path": "/Game/Weapons/SVCH/Replacement20261018/SightsR2/ElbowFit/DA_SVCH_ElbowFitGrip",
        "expected_r7_sha256": "71136c7209b8c66bafa0b730be427cf12b5b76ca14feaa518efb520840a4e71d",
    },
    "angled": {
        "path": "/Game/Weapons/SVCH/Replacement20261018/ForegripFit20261019/DA_SVCH_Grip_angled",
        "expected_r7_sha256": "4ede4ac8395d95438f9cae63a4051a4ea6f34572c26dc1109e5422b3aea1ec77",
    },
    "vertical": {
        "path": "/Game/Weapons/SVCH/Replacement20261018/ForegripFit20261019/DA_SVCH_Grip_vertical",
        "expected_r7_sha256": "2e508675aea53bdd0deec1cf12720c3ddb6d32c4c0cabf8165ba10bee9384026",
    },
    "canted": {
        "path": "/Game/Weapons/SVCH/Replacement20261018/ForegripFit20261019/DA_SVCH_Grip_canted",
        "expected_r7_sha256": "0af503fcf5f61ea37347cb2c619a643d9b329b8d841cc77e09a47bc8619d1174",
    },
    "prism": {
        "path": "/Game/Weapons/SVCH/Replacement20261018/ForegripFit20261019/DA_SVCH_Grip_prism",
        "expected_r7_sha256": "a9991659b063cbb9182979f433ac6925e7c4c94d8870add91fcc8ad88b87d16a",
    },
}

SHARED_PROTECTED = [
    "/Game/Weapons/SVDDragunov20260922/Complete20260923/Animations/A_SVD_equip",
    "/Game/Weapons/SVDDragunov20260922/Complete20260923/Animations/A_SVD_reload_empty",
    "/Game/Weapons/SVCH/Replacement20261018/RealSights20261019/SK_SVCH_RealFoldingSights",
]


def disk_path(pkg_path: str) -> Path:
    return PROJ_DIR / "Content" / (pkg_path.split(".")[0].removeprefix("/Game/") + ".uasset")


def sha256_file(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def extract(asset) -> dict:
    result = {"family": str(asset.get_editor_property("family")), "clips": []}
    for c in asset.get_editor_property("clips"):
        r = c.get_editor_property("retained")
        result["clips"].append(
            {
                "base": c.get_editor_property("base").get_path_name().split(".")[0],
                "retained": r.get_path_name().split(".")[0] if r else None,
                "duration": c.get_editor_property("duration"),
                "tracks": [
                    {
                        "bone": str(t.get_editor_property("bone")),
                        "times": list(t.get_editor_property("times")),
                        "values": list(t.get_editor_property("values")),
                    }
                    for t in c.get_editor_property("tracks")
                ],
            }
        )
    return result


es = u.get_editor_subsystem(u.UnrealEditorSubsystem)
if es and es.get_game_world():
    raise RuntimeError("PIE active; aborting install.")

dirty = {p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
BEFORE_DIR.mkdir(parents=True, exist_ok=True)
PUB_DIR.mkdir(parents=True, exist_ok=True)
READBACK_DIR.mkdir(parents=True, exist_ok=True)

protected_before = {p: sha256_file(disk_path(p)) for p in SHARED_PROTECTED}

receipt_path = ART_DIR / "install_receipt.json"
prior_receipt = json.loads(receipt_path.read_text()) if receipt_path.exists() else {}

receipt = {
    "complete": False,
    "revision": "SVCHEquipLeftBolt_20261126",
    "target_clip": EQUIP_CLIP,
    "assets": {},
    "shared_sequences_written": False,
    "V9_written": False,
    "other_11_clips_written": False,
    "runtime_tested": False,
}

for fam, spec in TARGETS.items():
    pkg = spec["path"]
    fp = disk_path(pkg)
    if pkg in dirty:
        raise RuntimeError(f"Unsaved editor package: {pkg}")
    cur_sha = sha256_file(fp)
    prior_after = prior_receipt.get("assets", {}).get(fam, {}).get("after_sha256")
    allowed = {spec["expected_r7_sha256"]}
    if prior_after:
        allowed.add(prior_after)
    if cur_sha not in allowed:
        raise RuntimeError(f"Unexpected on-disk SHA for {pkg}: {cur_sha}")

    # Backup before modifying
    bak = BEFORE_DIR / f"{fp.stem}_{cur_sha[:12]}.uasset"
    if not bak.exists():
        shutil.copy2(fp, bak)

    asset = u.load_asset(pkg)
    if not asset:
        raise RuntimeError(f"Failed to load {pkg}")
    before = extract(asset)
    if any(c["retained"] for c in before["clips"]):
        raise RuntimeError(f"Retained clips present in {pkg}; refusing lossy JSON import.")

    src_json_path = OUT_DIR / "Profiles" / f"{fam}.json"
    src_data = json.loads(src_json_path.read_text())
    replacement = next(c for c in src_data["clips"] if c["base"] == EQUIP_CLIP)

    after = dict(before)
    after["clips"] = [replacement if c["base"] == EQUIP_CLIP else c for c in before["clips"]]

    if not asset.set_shared_clips_from_json(json.dumps(after)):
        raise RuntimeError(f"set_shared_clips_from_json failed for {fam}")

    readback = extract(asset)
    before_others = [c for c in before["clips"] if c["base"] != EQUIP_CLIP]
    after_others = [c for c in readback["clips"] if c["base"] != EQUIP_CLIP]
    if before_others != after_others:
        raise RuntimeError(f"Non-equip clip changed during import for {fam}!")

    E.set_metadata_tag(asset, "SVCHEquipLeftBoltRevision", receipt["revision"])
    E.set_metadata_tag(
        asset,
        "SVCHEquipLeftBoltNote",
        "Left-side charging handle pull reusing reload_empty pose + C1 smooth entry/return + right hand pistol-grip lock",
    )
    if not E.save_loaded_asset(asset, False):
        raise RuntimeError(f"save_loaded_asset failed for {fam}")

    after_sha = sha256_file(fp)
    shutil.copy2(fp, PUB_DIR / fp.name)
    (READBACK_DIR / f"{fam}.json").write_text(json.dumps(readback, separators=(",", ":")))

    receipt["assets"][fam] = {
        "package": pkg,
        "disk_path": str(fp),
        "before_sha256": cur_sha,
        "after_sha256": after_sha,
        "backup": str(bak),
        "source_json_sha256": sha256_file(src_json_path),
        "clips_count": len(readback["clips"]),
        "other_11_clips_identical": True,
    }
    print(f"SVCH_EQUIP_LEFT_BOLT_SAVED {fam} sha={after_sha[:12]}", flush=True)

# Verify shared protected assets untouched
for p, h0 in protected_before.items():
    if sha256_file(disk_path(p)) != h0:
        raise RuntimeError(f"Protected shared asset changed: {p}")

receipt["complete"] = True
receipt_path.write_text(json.dumps(receipt, indent=2))
(OUT_DIR / "install_receipt.json").write_text(json.dumps(receipt, indent=2))
print("SVCH_EQUIP_LEFT_BOLT_ALL_5_SAVED", flush=True)
