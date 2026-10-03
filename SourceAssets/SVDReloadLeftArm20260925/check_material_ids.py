"""Cross-check each profile's arm material ids against the native source export."""
import json
from pathlib import Path

V6 = Path(r'D:\FPS3D\FPSGAME\SourceAssets\ModularOutfit20260925\BareArmsFamilyV6')
CFG = Path(r'D:\FPS3D\FPSGAME\Content\ColdSteelData\modular_outfits.json')
cfg = json.loads(CFG.read_text(encoding='utf-8-sig'))
print('top-level keys', list(cfg.keys()))
for path, profile in cfg['profiles'].items():
    name = profile.get('rig_profile')
    if name == 'Body':
        continue
    src = V6 / 'Sources' / f'{name}.json'
    arm_materials = None
    if src.exists():
        arm_materials = json.loads(src.read_text(encoding='utf-8-sig')).get('arm_materials')
    print(f"{name:11s} hide_source_materials={profile.get('hide_source_materials')} "
          f"native_arm_materials={arm_materials} "
          f"native_bare_arms={profile.get('native_bare_arms')} shirt={profile.get('shirt_covers')} "
          f"glove={profile.get('glove_covers')}")
