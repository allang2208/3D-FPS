"""Produce and save M-07 anatomical physics assets; no runtime simulation."""

import json
from pathlib import Path

import unreal


DESTINATION = "/Game/Monsters/BlindSupplicantM07"
RECEIPT = Path(
    "D:/FPS3D/FPSGAME/SourceAssets/BlindSupplicantM07Meshy20261001/Authoring/"
    "body_physics_delivery.json"
)


def author_and_save():
    project_file = unreal.Paths.get_project_file_path().replace("\\", "/").lower()
    if not project_file.endswith("/fpsgame/fpsgame.uproject"):
        raise RuntimeError("M-07 body physics authoring belongs to the FPSGAME host.")

    mesh = unreal.load_asset(DESTINATION + "/SK_M07")
    if mesh is None:
        raise RuntimeError("Import SK_M07 before producing its body physics asset.")

    receipt = json.loads(unreal.BlindSupplicantPhysicsAuthoring.build_body_physics(mesh))
    if not receipt.get("success"):
        raise RuntimeError(receipt.get("error", "M-07 physics authoring failed."))

    asset = unreal.load_asset(receipt["physics_asset"])
    if asset is None:
        raise RuntimeError("The produced M-07 physics asset could not be saved.")

    receipt["physics_saved"] = bool(unreal.EditorAssetLibrary.save_loaded_asset(asset, False))
    receipt["mesh_saved"] = bool(unreal.EditorAssetLibrary.save_loaded_asset(mesh, False))
    receipt["saved"] = receipt["physics_saved"] and receipt["mesh_saved"]
    receipt["caller_must_save_packages"] = not receipt["saved"]
    RECEIPT.parent.mkdir(parents=True, exist_ok=True)
    RECEIPT.write_text(json.dumps(receipt, ensure_ascii=False, indent=2), encoding="utf-8")
    if not receipt["saved"]:
        raise RuntimeError("M-07 body physics was produced, but its packages were not both saved.")

    unreal.log(
        "M07_BODY_PHYSICS_SAVED asset={} bodies={} constraints={}".format(
            receipt["physics_asset"], receipt["bodies"], receipt["constraints"]
        )
    )
    return receipt


if __name__ == "__main__":
    author_and_save()
