"""Retire only the superseded forge full-body clip bindings; preserve any later replacements."""
import json
from pathlib import Path
from config_transaction import commit

def main():
    root = Path(__file__).resolve().parents[2]
    path = root / "Content/ColdSteelData/player_body.json"
    before = path.read_bytes()
    data = json.loads(before.decode("utf-8-sig"))
    retired = {}
    for keys, rig in [(("clips",), "Jason"), (("body_variants", "kaitlin", "clips"), "Kaitlin")]:
        clips = data
        for key in keys:
            clips = clips[key]
        for action in ("Ready", "Strike", "Quench", "Enter", "Exit", "QuenchExit"):
            role = "Forge." + action
            old = f"/Game/Characters/ForgeWorldBody20261029/FootSupportV2/{rig}/A_Forge_{action}.A_Forge_{action}"
            if role in clips:
                if clips[role] != old:
                    raise ValueError(f"Unexpected current asset for {keys}/{role}")
                retired[keys + (role,)] = clips.pop(role)
    result = commit(path, before, data, owned_paths=retired, retired_clips=retired, producer=__file__)
    print(result["status"], len(retired))

if __name__ == "__main__":
    main()
