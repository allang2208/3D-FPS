"""Record this review's scoped edits against its local before copies."""
from pathlib import Path
import difflib, hashlib, json
R=Path('D:/FPS3D/FPSGAME'); O=Path(__file__).parent
pairs={
 'Source/FPSGAME/FPSGAMECharacterProfile.cpp':'FPSGAMECharacterProfile.cpp',
 'Source/FPSGAME/Production/ProductionBluntAuthority.cpp':'ProductionBluntAuthority.cpp',
 'Source/FPSGAME/Production/ThunderHammerIntentAudit.cpp':'ThunderHammerIntentAudit.cpp',
 'Source/FPSGAME/Production/ProductionToolComponent.h':'ProductionToolComponent.h',
 'Source/FPSGAME/Multiplayer/ColdSteelPlayerState.h':'Multiplayer_ColdSteelPlayerState.h',
 'Source/FPSGAME/Multiplayer/ColdSteelPlayerState.cpp':'Multiplayer_ColdSteelPlayerState.cpp',
 'Source/FPSGAME/Multiplayer/ColdSteelInventoryRequests.cpp':'Multiplayer_ColdSteelInventoryRequests.cpp',
 'Source/FPSGAME/Multiplayer/ColdSteelCampfireRequests.cpp':'Multiplayer_ColdSteelCampfireRequests.cpp',
 'Source/FPSGAME/Weapons/GunsmithSystem.cpp':'Weapons_GunsmithSystem.cpp',
 'Source/FPSGAME/UI/ColdSteelAcquisitionAuditCommandlet.cpp':'UI_ColdSteelAcquisitionAuditCommandlet.cpp',
 'Source/FPSGAME/Weapons/Kukri/HatchetDualChopRhythm.h':'HatchetDualChopRhythm.h',
 'SourceAssets/HatchetChop20261102/author_hatchet_dual_chop.py':'author_hatchet_dual_chop.py',
 'Source/FPSGAME/Weapons/Kukri/HatchetSprintRhythm.h':'HatchetSprintRhythm.h',
 'SourceAssets/HatchetSprint20261103/author_hatchet_sprint.py':'author_hatchet_sprint.py',
 'Source/FPSGAME/Development/ThunderHammerClosureAudit.h':None,
 'Source/FPSGAME/Development/ThunderHammerClosureAudit.cpp':None,
}
patch=[];rows=[]
for relative,backup in pairs.items():
 p=R/relative; old=O/'Before'/backup if backup else None
 before=old.read_text(encoding='utf-8-sig').splitlines(keepends=True) if old else []
 after=p.read_text(encoding='utf-8-sig').splitlines(keepends=True)
 patch.extend(difflib.unified_diff(before,after,fromfile='a/'+relative if old else '/dev/null',tofile='b/'+relative))
 rows.append({'file':relative,'before':str(old.relative_to(O)) if old else None,
  'before_sha256':hashlib.sha256(old.read_bytes()).hexdigest() if old else None,
  'after_sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
(O/'review-source-changes.patch').write_text(''.join(patch),encoding='utf-8')
(O/'review-source-changes.json').write_text(json.dumps({'scope':'local before copies, not a clean published git revision','files':rows},indent=2),encoding='utf-8')
print('Recorded',len(rows),'owned change paths')
