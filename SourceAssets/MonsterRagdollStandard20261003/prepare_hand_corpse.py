"""Produce and save a separate connected hand corpse asset; no game or preview."""
import json
from pathlib import Path
import unreal as u

ROOT = Path("D:/FPS3D/FPSGAME/SourceAssets/MonsterRagdollStandard20261003")
DEST = "/Game/Monsters/FleshHand/PA_FleshHand_Corpse"
REVISION = "MonsterRagdollStandard20261003"
LIB = u.EditorAssetLibrary

blueprint = u.load_asset("/Game/Monsters/FleshHand/BP_FleshHand")
if blueprint is None:
    raise RuntimeError("Missing the current FleshHand blueprint")
defaults = u.get_default_object(blueprint.generated_class())
mesh = defaults.get_editor_property("visual_mesh")
if mesh is None:
    raise RuntimeError("Missing the current hand visual mesh")
source = mesh.get_editor_property("physics_asset")
if source is None:
    raise RuntimeError("Missing the hand's original query physics")

asset = u.load_asset(DEST)
if asset is not None and LIB.get_metadata_tag(asset, "Monster.CorpseRevision") != REVISION:
    raise RuntimeError("Preserving independent asset at " + DEST)
if asset is None:
    asset = LIB.duplicate_asset(source.get_path_name(), DEST)
if asset is None:
    raise RuntimeError("Could not duplicate the original hand collision shapes")
if not u.FleshHandMonster.build_corpse_physics(mesh, asset):
    raise RuntimeError("Could not connect the dedicated hand corpse rig")
LIB.set_metadata_tag(asset, "Monster.CorpseRevision", REVISION)
if not LIB.save_loaded_asset(asset, False):
    raise RuntimeError("Could not save the hand corpse physics")

report = {
    "status": "HandCorpsePhysicsSaved",
    "mesh": mesh.get_path_name(),
    "original_query_asset": source.get_path_name(),
    "saved_asset": asset.get_path_name(),
    "live_mesh_and_query_asset_modified": False,
    "runtime_tested": False,
}
(ROOT / "Receipts" / "hand-physics-saved.json").write_text(
    json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
print("HAND_CORPSE_PHYSICS_SAVED " + json.dumps(report, ensure_ascii=False))
