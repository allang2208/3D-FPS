"""Upgrade the placed mill keeper's Blueprint while reusing the saved outfit and idle."""
import json
from pathlib import Path
import sys

import unreal as u

sys.path.insert(0, str(Path(__file__).resolve().parent))
from import_keeper import ROOT, save_keeper_blueprint

previous = json.loads((ROOT / "saved.json").read_text())
target = previous["character"].split(".")[0]
editor = u.get_editor_subsystem(u.UnrealEditorSubsystem)
if editor and editor.get_game_world():
    raise RuntimeError("The editor is in play.")
if any(p.get_name() == target for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()):
    raise RuntimeError("The keeper Blueprint has unsaved edits.")
mesh, idle = (u.load_asset(previous[key]) for key in ("mesh", "idle"))
if not mesh or not idle:
    raise RuntimeError("Missing mill keeper outfit or idle.")
bp = save_keeper_blueprint(mesh, idle)
receipt = {"blueprint": bp.get_path_name(), "parent": u.VillageMillKeeper.static_class().get_path_name(),
           "mesh": mesh.get_path_name(), "idle": idle.get_path_name(), "runtime_tested": False}
(ROOT / "dialogue_r1.json").write_text(json.dumps(receipt, indent=2), encoding="utf-8")
