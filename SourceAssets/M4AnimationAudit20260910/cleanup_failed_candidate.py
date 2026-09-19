import unreal,json
from pathlib import Path
O=Path(__file__).parent;p='/Game/Weapons/M4AnimationAuditFinal/CR_M4_AnimationAudit';refs=unreal.EditorAssetLibrary.find_package_referencers_for_asset(p,True);assert not refs,refs
ok=unreal.EditorAssetLibrary.delete_asset(p);assert ok
(O/'candidate_cleanup.json').write_text(json.dumps({'removed_failed_unused_rig':p,'referencers':list(refs),'deleted':ok}));unreal.log('AUDIT_FAILED_CANDIDATE_CLEANED')
