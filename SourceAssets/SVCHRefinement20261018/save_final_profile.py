"""Save the final finger-order refinement after the native build completes."""
import json,hashlib
from pathlib import Path
import unreal as u
O=Path(__file__).parent
rp=O/'install_receipt.json';receipt=json.loads(rp.read_text())
profile=u.load_asset(receipt['profile'])
if not profile:raise RuntimeError('Missing saved SVCH profile')
source=(O/'shared_profile.json').read_bytes()
if not profile.set_shared_clips_from_json(source.decode('utf-8')):raise RuntimeError('Cannot apply final profile')
if not u.EditorAssetLibrary.save_loaded_asset(profile,False):raise RuntimeError('Cannot save final profile')
receipt['profile_source_sha256']=hashlib.sha256(source).hexdigest()
receipt['finger_order_refined']=True
rp.write_text(json.dumps(receipt,indent=1))
print('SVCH_FINAL_PROFILE_SAVED',receipt['profile_source_sha256'],flush=True)
