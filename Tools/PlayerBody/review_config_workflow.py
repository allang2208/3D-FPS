"""Explicit offline review of the shared-config failure modes; never edits live config."""
import copy
import hashlib
import json
from pathlib import Path
import runpy
import tempfile

ROOT = Path(__file__).resolve().parents[2]
API = runpy.run_path(str(ROOT / "Tools/PlayerBody/config_transaction.py"))
commit, Conflict = API["commit"], API["ConfigConflict"]


def main():
    live = ROOT / "Content/ColdSteelData/player_body.json"
    live_bytes = live.read_bytes()
    source = json.loads(live_bytes.decode("utf-8-sig"))
    results = []
    with tempfile.TemporaryDirectory(prefix="fps-body-workflow-") as name:
        root = Path(name)
        target = root / "Content/ColdSteelData/player_body.json"
        target.parent.mkdir(parents=True)

        def rejected(label, before, candidate, scopes):
            unchanged = target.read_bytes()
            try:
                commit(target, before, candidate, owned_paths=scopes, producer=__file__)
            except Conflict:
                assert target.read_bytes() == unchanged, label
                results.append(label)
            else:
                raise AssertionError("Expected rejection: " + label)

        target.write_bytes(live_bytes)
        candidate = copy.deepcopy(source)
        candidate["head_equipment"]["ue_steel_armet"]["first_person_overlay"] = "/Game/OfflineReview.OfflineReview"
        receipt = commit(target, live_bytes, candidate,
                         owned_paths=[("head_equipment", "ue_steel_armet", "first_person_overlay")], producer=__file__)
        current = target.read_bytes()
        a, b = API["_span"](live_bytes.decode("utf-8-sig"), ("clips",))
        x, y = API["_span"](current.decode("utf-8-sig"), ("clips",))
        assert live_bytes.decode("utf-8-sig")[a:b] == current.decode("utf-8-sig")[x:y]
        assert Path(receipt["receipt"]).with_name("before.json").read_bytes() == live_bytes
        results.append("helmet edit preserves complete clips text and records original bytes")
        rejected("stale read cannot overwrite a newer edit", live_bytes, candidate,
                 [("head_equipment", "ue_steel_armet")])

        target.write_bytes(live_bytes)
        old = copy.deepcopy(source)
        old["clips"] = {k: v for k, v in old["clips"].items() if not k.startswith("Warhammer.")}
        rejected("old 125-role snapshot cannot delete restored hammer routes", live_bytes, old,
                 [("head_equipment", "ue_steel_armet")])
        rejected("whole clip-library ownership is forbidden", live_bytes, source, [("clips",)])
        wrong = copy.deepcopy(source)
        wrong["clips"]["Warhammer.Idle"] = "/Game/OfflineReview.OfflineReview"
        rejected("helmet writer cannot change hammer animation", live_bytes, wrong,
                 [("head_equipment", "ue_steel_armet")])

        with API["_lock"](root / "Saved/PlayerBodyConfigWrites/writer.lock"):
            rejected("overlapping cooperative writer cannot enter", live_bytes, candidate,
                     [("head_equipment", "ue_steel_armet")])

        tiny = b'\xef\xbb\xbf{\r\n  "clips": {},\r\n  "note": "keep"\r\n}\r\n'
        target.write_bytes(tiny)
        commit(target, tiny, {"clips": {"Warhammer.Idle": "/Game/A.A"}, "note": "keep"},
               owned_paths=[("clips", "Warhammer.Idle")], producer=__file__)
        added = target.read_bytes()
        assert added.startswith(b"\xef\xbb\xbf") and b"\n" not in added.replace(b"\r\n", b"")
        assert b'  "note": "keep"\r\n}\r\n' in added
        results.append("empty clips insertion preserves BOM, CRLF and unrelated bytes")
        rejected("duplicate keys cannot hide overwritten data", added,
                 '{"clips":{"Warhammer.Idle":"a","Warhammer.Idle":"b"},"note":"keep"}',
                 [("clips", "Warhammer.Idle")])
        initial = b'{"clips":{},"note":"keep"}\n'
        target.write_bytes(initial)
        first_hat = {"clips": {}, "note": "keep", "head_equipment": {"hat": {"mesh": "/Game/Hat.Hat"}}}
        commit(target, initial, first_hat, owned_paths=[("head_equipment", "hat")], producer=__file__)
        assert json.loads(target.read_bytes()) == first_hat
        results.append("first equipment insertion creates only missing owned parents")
        invalid = copy.deepcopy(first_hat)
        invalid["head_equipment"]["hat"] = None
        rejected("object replacement cannot bypass implicit-deletion protection", target.read_bytes(), invalid,
                 [("head_equipment", "hat")])
    report = {
        "passed": len(results), "cases": results, "live_configuration_written": False,
        "live_sha256_at_start": hashlib.sha256(live_bytes).hexdigest(),
        "live_sha256_at_end": hashlib.sha256(live.read_bytes()).hexdigest(),
        "editor_launched": False, "game_tested": False,
    }
    out = ROOT / "Saved/AnimationHandoffReview20261021/config-workflow.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    main()
