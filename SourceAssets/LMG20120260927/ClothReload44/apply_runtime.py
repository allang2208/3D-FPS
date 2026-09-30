"""Point the 201 cloth-pouch reload at ClothReload44 and its contact clock.

Exact-string edits only (asserted), so parallel work elsewhere in these files is
kept.  Run after install.py has saved the ten clips; then build the module.
`--revert` restores the ClothFeed33 constants and path.
"""
import sys
from pathlib import Path

SRC = Path('D:/FPS3D/FPSGAME/Source/FPSGAME')
OLD_H = ('inline constexpr float ClothBoxOut=1.87f,ClothOldHidden=2.53f,ClothNewVisible=2.915f;\n'
         'inline constexpr float ClothBoxSeat=3.795f,ClothBeltSeat=4.62f,ClothCoverClose=5.302f;\n'
         'inline constexpr float ClothDuration=6.2f,ClothReturnStart=5.45f;')
NEW_H = ('// ClothReload44 source-time contacts (reference video phases; see SourceAssets ClothReload44).\n'
         'inline constexpr float ClothCoverOpen=1.12f,ClothBoxOut=2.10f,ClothOldHidden=2.45f,ClothNewVisible=2.80f;\n'
         'inline constexpr float ClothBoxSeat=3.35f,ClothBeltSeat=4.78f,ClothCoverClose=5.22f;\n'
         'inline constexpr float ClothDuration=6.2f,ClothReturnStart=5.45f;')
OLD_P = 'TEXT("/Game/Weapons/LMG201/ClothFeed33/Animations/%s/A_LMG201_%s_%s")'
NEW_P = 'TEXT("/Game/Weapons/LMG201/ClothReload44/Animations/%s/A_LMG201_%s_%s")'
OLD_C = 'MechanicalCueTimes={.715f,LMG201WeaponAssets::ClothBoxOut,'
NEW_C = 'MechanicalCueTimes={LMG201WeaponAssets::ClothCoverOpen,LMG201WeaponAssets::ClothBoxOut,'
OLD_N = '// Source-time contacts from ClothFeed33.'
NEW_N = '// Source-time contacts from ClothReload44.'
edits = [(SRC / 'Weapons/LMG201WeaponAssets.h', [(OLD_H, NEW_H), (OLD_P, NEW_P)]),
         (SRC / 'FPSGAMECharacter.cpp', [(OLD_C, NEW_C), (OLD_N, NEW_N)])]
revert = '--revert' in sys.argv
for path, pairs in edits:
    raw = path.read_bytes()
    crlf = b'\r\n' in raw
    s = raw.decode('utf-8-sig' if raw.startswith(b'\xef\xbb\xbf') else 'utf-8').replace('\r\n', '\n')
    for a, b in pairs:
        a, b = (b, a) if revert else (a, b)
        if b in s and a not in s:
            continue
        assert s.count(a) == 1, (path.name, a[:60])
        s = s.replace(a, b)
    out = s.replace('\n', '\r\n') if crlf else s
    bom = b'\xef\xbb\xbf' if raw.startswith(b'\xef\xbb\xbf') else b''
    path.write_bytes(bom + out.encode('utf-8'))
    print('RUNTIME_EDITED', path.name, 'reverted' if revert else 'applied')
