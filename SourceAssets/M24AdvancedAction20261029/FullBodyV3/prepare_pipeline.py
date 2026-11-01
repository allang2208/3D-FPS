from pathlib import Path
import shutil
O=Path(__file__).resolve().parent;V=O.parent/'DetailV2';P=O.parents[2]
(O/'Before/Icons').mkdir(parents=True,exist_ok=True)
for name in ('textures.py','bake_masks.py','author_icons.py','run_assets.ps1','install.py'):
    s=(V/name).read_text(encoding='utf-8').replace('DetailV2','FullBodyV3').replace('T_M24_AAS_V2','T_M24_AAS_V3')
    (O/name).write_text(s,encoding='utf-8')
s=(O/'bake_masks.py').read_text().replace('M24_AdvancedAction_FullBodyV3.blend','M24_AdvancedAction_BipodSeatV3.blend')
s=s.replace('M24_AdvancedAction_DetailBody','M24_Bipod_SeatV3').replace('T_M24_AAS_V3_SurfaceMask','T_M24_AAS_V3_BipodMask')
s=s.replace("'bake_receipt.json'","'bipod_bake_receipt.json'")
(O/'bake_bipod.py').write_text(s,encoding='utf-8')
paths=['Content/Weapons/M24/MotionMagazine20261027/SK_M24_MotionV9.uasset',
       'Content/Weapons/M24/AdvancedAction20261029/Meshes/SM_M24_m24_advanced_action.uasset',
       'Content/Weapons/M24/Bipod20261029/SM_M24_Bipod_Base.uasset',
       'Source/FPSGAME/Weapons/M24ChassisAssetTools.cpp','Source/FPSGAME/Weapons/M24ChassisAssetTools.h',
       'Source/FPSGAME/Weapons/M24Attachments.cpp','Source/FPSGAME/Weapons/M4HandstopVisual.cpp']
for rel in paths:
    src=P/rel;dst=O/'Before'/rel;dst.parent.mkdir(parents=True,exist_ok=True)
    if src.exists() and not dst.exists():shutil.copy2(src,dst)
print('V3 pipeline prepared')
