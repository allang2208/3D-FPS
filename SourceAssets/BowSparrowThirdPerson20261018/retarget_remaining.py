"""Save the remaining Sparrow candidate packages, then finish production reads."""
import json
from pathlib import Path
import unreal as u
O=Path(__file__).parent;ROOT=O.parents[1]
D='/Game/Characters/JasonPlayer20261003/BowSparrow20261018'
B='/Game/ParagonSparrow/Characters/Heroes/Sparrow'
cfg=json.loads((ROOT/'Content/ColdSteelData/player_body.json').read_text(encoding='utf-8-sig'))
lib=u.EditorAssetLibrary;target=u.load_asset(cfg['body_mesh'])
for name in ('RMB_Fire','Primary_Fire_Slow'):
 path=D+'/Retargeted/J_Sparrow_'+name
 if not lib.does_asset_exist(path):
  p=u.IKRetargetBatchOperationInputs();p.assets_to_retarget=[lib.find_asset_data(B+'/Animations/'+name)]
  p.source_mesh=u.load_asset(B+'/Meshes/Sparrow');p.target_mesh=target
  p.ik_retarget_asset=u.load_asset(D+'/Rig/RTG_Sparrow_Jason_Bow')
  p.prefix='J_Sparrow_';p.target_path=D+'/Retargeted';p.include_referenced_assets=False;p.overwrite_existing_files=False
  u.IKRetargetBatchOperation.run_batch_retarget(p)
 clip=u.load_asset(path)
 if not clip:raise RuntimeError('Missing retarget '+name)
 if not u.WeaponAnimationAuthoring.finalize_authored_animation(clip):raise RuntimeError('Finalize '+name)
 if not lib.save_loaded_asset(clip,False):raise RuntimeError('Save '+name)
 print('SPARROW_REMAINING_SAVED',name,flush=True)
exec(compile((O/'read_retargeted.py').read_text(encoding='utf-8'),'read_retargeted.py','exec'))
