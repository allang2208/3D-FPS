"""Re-apply the revision metadata tag on the ten repaired animations and save."""
import json
from pathlib import Path
import unreal as u

O = Path(__file__).parent
receipt = json.loads((O / 'import_receipt.json').read_text())
E = u.EditorAssetLibrary
TAG = ('20260925 reload tail: support-arm root relocated outside the eye volume; '
       'wrist contact, bone lengths, grip and mechanical timing preserved (frames 274-344)')
for key, info in receipt.items():
    anim = u.load_asset(info['asset'])
    if not anim:
        continue
    E.set_metadata_tag(anim, 'LeftArmCameraProtection', TAG)
    E.save_loaded_asset(anim, False)
print('SVD_LEFT_ARM_TAG_COMPLETE', len(receipt), flush=True)
