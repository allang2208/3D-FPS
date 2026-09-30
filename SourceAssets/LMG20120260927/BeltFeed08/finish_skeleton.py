"""Keep common native-arm animation compatibility on the private rig only."""
import unreal as u,json
from pathlib import Path
O=Path(__file__).parent
asset=u.load_asset('/Game/Weapons/LMG201/BeltFeed08/SK_LMG201_FeedSkeleton')
source=u.load_asset('/Game/Weapons/LMG201/Production20260927/SK_LMG201_Manny').skeleton
asset.add_compatible_skeleton(source)
if not u.EditorAssetLibrary.save_loaded_asset(asset,False):raise RuntimeError('Private skeleton save failed')
(O/'skeleton_finish_receipt.json').write_text(json.dumps({'asset':asset.get_path_name(),'compatible_native_arm_skeleton':source.get_path_name(),'saved':True,'shared_skeleton_modified':False},indent=2),encoding='utf8')
print('201_PRIVATE_SKELETON_FINISHED')
