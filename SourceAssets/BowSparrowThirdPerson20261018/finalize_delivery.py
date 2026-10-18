"""Record saved Sparrow bow production outputs; does not run UE or tests."""
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TASK = Path(__file__).resolve().parent


def read(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rel(path):
    return path.relative_to(ROOT).as_posix()


sources = [
    "Source/FPSGAME/Characters/FPSBodyBowMotion.h",
    "Source/FPSGAME/Characters/FPSBodyBowPose.inl",
    "Source/FPSGAME/Characters/FPSPlayerBodyAnimInstance.cpp",
    "Source/FPSGAME/Characters/FPSPlayerBodyComponent.h",
    "Source/FPSGAME/Characters/FPSPlayerBodyConsumable.cpp",
    "Source/FPSGAME/Characters/FPSPlayerBodyBow.cpp",
]
saved = read(TASK / "assets-saved.json")
published = read(TASK / "published.json")
config = ROOT / "Content/ColdSteelData/player_body.json"
current_clips = read(config)["clips"]
review_file = TASK / "NetworkReview/review.json"
review = read(review_file) if review_file.exists() else None
pending_file = TASK / "NetworkReview/pending.json"
pending_review = read(pending_file) if pending_file.exists() and not review else None
assets = {}
for key, asset in saved["clips"].items():
    package = asset.split(".")[0]
    path = ROOT / "Content" / (package.removeprefix("/Game/") + ".uasset")
    assets[key] = {
        "asset": asset,
        "file": rel(path),
        "sha256": sha(path),
        "configured_asset": current_clips.get(key),
    }
builds = {}
for kind in ("Game", "Editor"):
    attempts = sorted(TASK.glob(f"Build-*-{kind}"))
    if attempts:
        attempt = attempts[-1]
        receipt = attempt / "result.json"
        builds[kind] = {
            "status": read(receipt) if receipt.exists() else "No success receipt",
            "receipt": rel(receipt) if receipt.exists() else None,
            "console_log": rel(attempt / "console.log"),
        }

delivery = {
    "recorded_at_utc": datetime.now(timezone.utc).isoformat(),
    "request": "Adapt imported Paragon Sparrow to third-person bow draw, hold, release and let-down with native hand/string contact.",
    "source_url": saved["source_url"],
    "source_mesh": "/Game/ParagonSparrow/Characters/Heroes/Sparrow/Meshes/Sparrow",
    "source_actions": {
        "Carry": "Travel_Mode_Idle_BowDown",
        "Ready": "RMB_Drawback fitted first pose",
        "Draw": "RMB_Drawback",
        "Hold": "RMB_Loop",
        "Release": "RMB_Fire source seconds 0..0.65, followed by a blend to Carry",
        "LetDown": "Fitted Draw evaluated in reverse from current draw fraction",
    },
    "target_mesh": "/Game/Characters/ModularOutfit20260924/JasonPlayer20261003/EquipmentFit20261003/SK_Jason_Base",
    "source_files": {p: {"sha256": sha(ROOT / p)} for p in sources},
    "authoring_sha256": saved["authoring_sha256"],
    "authoring_details": rel(TASK / "authoring.json"),
    "skin_contact_fitting": rel(TASK / "contact-correction.json"),
    "assets_saved_complete": saved["complete"],
    "asset_save_receipt": rel(TASK / "save-commandlet.json"),
    "active_assets": assets,
    "config": {"path": rel(config), "sha256": sha(config)},
    "publication_receipt": rel(TASK / "published.json"),
    "initial_candidate_assets": "Retired Animations/J_SparrowBow_* and AnimationsV2/J_SparrowBowV2_* are archived under trash/bow-food-closeout-20261018/Content/Characters/JasonPlayer20261003/BowSparrow20261018; the network review publishes AnimationsV3/J_SparrowBowV3_*.",
    "integration": [
        "Native upper-body sequence evaluator; live pelvis and locomotion remain in the base pose.",
        "Native bone lengths, anatomical finger mapping, weighted helper bones and paired hand reach fitting.",
        "Physical grip and string-marker curves consumed after the final body pose.",
        "Partial draw release/cancel and source string rebound maintain the displayed contact history.",
        "Existing local and replicated bow state selects the same native clips; gameplay shot and ammunition rules are unchanged.",
    ],
    "builds": builds,
    "editor_build_pending": read(TASK / "editor-build-pending.json") if (TASK / "editor-build-pending.json").exists() else None,
    "documentation": "Docs/Characters/third-person-weapon-grips-20261003.md",
    "gui_editor_launched": False,
    "game_run": review is not None,
    "game_run_mode": "headless local UDP audit fixture" if review else None,
    "runtime_tests_run": review is not None or pending_review is not None,
    "network_review": rel(review_file) if review is not None else rel(pending_file) if pending_review else None,
    "review_complete": review is not None,
    "visual_acceptance": "Not performed. User to assess hand/string contact, arm clipping, fingers, transitions and aim angles in game.",
    "multiplayer_acceptance": "See network review for controlled local UDP results and limits; visual and Internet acceptance not performed." if review else "Not complete; see pending review. No socket fixture result yet." if pending_review else "Not performed.",
}
(TASK / "delivery.json").write_text(json.dumps(delivery, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print("SPARROW_BOW_DELIVERY_SAVED", rel(TASK / "delivery.json"))
