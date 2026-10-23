"""Switch only the rune hammer HUD after its new material has been saved."""
from pathlib import Path
import json
P=Path(__file__).resolve().parent;ROOT=P.parents[2]
saved=json.loads((P/'import_receipt.json').read_text('utf-8-sig'))
if not saved.get('installed_to_main_project'):raise RuntimeError('Finish the actual saved HUD package first')
path=ROOT/'Source/FPSGAME/Production/RuneboundHammerTuning.h';before=path.read_bytes()
old=b'/HudMotesV2/M_RuneboundEnergyHud.M_RuneboundEnergyHud';new=b'/HudSymmetricCapsV3/M_RuneboundEnergyHud.M_RuneboundEnergyHud'
if old in before:
    backup=P/'Before/RuneboundHammerTuning.h';backup.parent.mkdir(parents=True,exist_ok=True)
    if not backup.exists():backup.write_bytes(before)
    if path.read_bytes()!=before:raise RuntimeError('Concurrent source change; preserve current header')
    path.write_bytes(before.replace(old,new,1))
elif new not in before:raise RuntimeError('HUD runtime path changed; preserve current header')
print('RUNEBOUND_SYMMETRIC_CAPS_PATH_APPLIED')
