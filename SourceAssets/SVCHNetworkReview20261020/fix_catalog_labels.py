"""Correct the SVCH factory optic label without changing parts or stats."""
from pathlib import Path
import hashlib
import json

root = Path("D:/FPS3D/FPSGAME")
path = root / "Content/ColdSteelData/gunsmith.json"
before = path.read_bytes()
text = before.decode("utf-8-sig")
decoder = json.JSONDecoder()
pos = text.index("[", text.index('"weapons"')) + 1
while True:
    while text[pos].isspace() or text[pos] == ",":
        pos += 1
    if text[pos] == "]":
        raise RuntimeError("SVCH definition missing")
    weapon, end = decoder.raw_decode(text, pos)
    if weapon["id"] == "ue_svch":
        break
    pos = end
factory = next(o for o in weapon["options"]["optic"] if o["id"] == "false")
segment = text[pos:end]
optic_start = segment.index("[", segment.index('"optic"', segment.index('"options"'))) + 1
option_pos = optic_start
while segment[option_pos].isspace():
    option_pos += 1
option, option_end = decoder.raw_decode(segment, option_pos)
if option["id"] != "false":
    raise RuntimeError("Expected factory optic first; preserve current catalog")
fixed = segment[option_pos:option_end]
changes = {
    "name": "原厂机械瞄具",
    "description": "恢复 SVCh 导轨上的原厂折叠机械瞄具，使用无放大的机械瞄准。",
}
for key, value in changes.items():
    fixed = fixed.replace(json.dumps(option[key], ensure_ascii=False), json.dumps(value, ensure_ascii=False), 1)
after = text[:pos + option_pos] + fixed + text[pos + option_end:]
updated = json.loads(after)
new_weapon = next(w for w in updated["weapons"] if w["id"] == "ue_svch")
expected = json.loads(json.dumps(weapon))
next(o for o in expected["options"]["optic"] if o["id"] == "false").update(changes)
assert new_weapon == expected
if path.read_bytes() != before:
    raise RuntimeError("Catalog changed during edit; preserve parallel work")
backup = Path("D:/FPS3D/FPSGAME_Backups/SVCHNetworkReview20261020")
backup.mkdir(parents=True, exist_ok=True)
saved = backup / ("gunsmith_" + hashlib.sha256(before).hexdigest()[:12] + ".json")
if not saved.exists():
    saved.write_bytes(before)
path.write_bytes(after.encode("utf-8"))
Path(__file__).with_name("catalog-label-receipt.json").write_text(json.dumps({
    "complete": True, "definition": "ue_svch", "optic": "false",
    "fields": changes, "backup": str(saved), "stats_changed": False,
}, ensure_ascii=False, indent=2), encoding="utf-8")
print("SVCH_FACTORY_OPTIC_LABEL_SAVED")
