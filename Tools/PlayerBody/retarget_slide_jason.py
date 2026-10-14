"""Bake FootOut to Jason using the existing aligned GASP rig; save new assets only."""
import json
from pathlib import Path
import unreal as u

ROOT = Path('D:/FPS3D/FPSGAME')
OUT = ROOT/'SourceAssets/ThirdPersonSlide20261005'
DEST = '/Game/Characters/JasonPlayer20261003/SlideGASP20261005/Animations'
donors = json.loads((OUT/'donors.json').read_text(encoding='utf-8'))
cfg = json.loads((ROOT/'Content/ColdSteelData/player_body.json').read_text(encoding='utf-8-sig'))
crouch = json.loads((ROOT/'SourceAssets/ThirdPersonCrouch20261005/assets-saved.json').read_text(encoding='utf-8'))
lib = u.EditorAssetLibrary
source = u.load_asset('/Game/Characters/UEFN_Mannequin/Meshes/SKM_UEFN_Mannequin')
target = u.load_asset(cfg['body_mesh'])
retargeter = u.load_asset(crouch['retargeter'])
inputs = u.IKRetargetBatchOperationInputs()
inputs.assets_to_retarget = [lib.find_asset_data(p) for p in donors['clips'].values()]
inputs.source_mesh = source; inputs.target_mesh = target; inputs.ik_retarget_asset = retargeter
inputs.prefix = 'J_'; inputs.target_path = DEST
inputs.include_referenced_assets = False; inputs.overwrite_existing_files = False
for path in donors['clips'].values():
    if lib.does_asset_exist(DEST+'/J_'+path.rsplit('/',1)[1]):
        raise RuntimeError('Slide output already exists; do not overwrite a possibly loaded package')
outputs = u.IKRetargetBatchOperation.run_batch_retarget(inputs)
roles = {p.rsplit('/',1)[1]:role for role,p in donors['clips'].items()}
saved = {}; lengths = {}
for data in outputs:
    clip = data.get_asset()
    if not isinstance(clip,u.AnimSequence): continue
    role = roles[clip.get_name().removeprefix('J_')]
    clip.set_preview_skeletal_mesh(target)
    # Gameplay owns displacement. Lock every donor to the same reference root,
    # avoiding a different first-frame offset at entry/loop/exit boundaries.
    clip.set_editor_property('enable_root_motion',False)
    clip.set_editor_property('force_root_lock',True)
    clip.set_editor_property('root_motion_root_lock',u.RootMotionRootLock.REF_POSE)
    if not lib.save_loaded_asset(clip,False):
        raise RuntimeError('Save failed: '+clip.get_path_name())
    saved['Slide.'+role] = clip.get_path_name()
    lengths[role] = clip.get_play_length()
if len(saved) != len(roles): raise RuntimeError('Retarget did not finish all slide donors')
(OUT/'assets-saved.json').write_text(json.dumps({'retargeter':retargeter.get_path_name(),
    'runtime_clips':saved,'durations':lengths},indent=2),encoding='utf-8')
print('SLIDE_ASSETS_SAVED '+json.dumps(lengths))
