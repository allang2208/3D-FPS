"""Create the dedicated fat-zombie stagger; preserve the four accepted clips."""
import json
from pathlib import Path
import unreal as u

folder = '/Game/Monsters/FatZombieMeshy/Animations'
mesh = u.load_asset('/Game/Monsters/FatZombieMeshy/SK_FatZombie_Meshy')
attack = u.load_asset(folder + '/A_FatZombie_Attack')
options = u.AnimPoseEvaluationOptions()
options.set_editor_property('evaluation_type', u.AnimDataEvalType.COMPRESSED)
options.set_editor_property('optional_skeletal_mesh', mesh)
options.set_editor_property('incorporate_root_motion_into_pose', False)
contact_reference = []
for seconds in [0.6, 0.65, 0.675, 0.7, 0.75, 0.78, 1.0]:
    pose = u.AnimPoseExtensions.get_anim_pose_at_time(attack, seconds, options)
    hand = u.AnimPoseExtensions.get_bone_pose(pose, 'RightHand', u.AnimPoseSpaces.WORLD).translation
    contact_reference.append({'seconds': seconds, 'right_hand_cm': [hand.x, hand.y, hand.z]})
target = folder + '/A_FatZombie_Stagger'
clip = u.load_asset(target) if u.EditorAssetLibrary.does_asset_exist(target) else u.EditorAssetLibrary.duplicate_asset(folder + '/A_FatZombie_Idle', target)
if not clip or not u.FatZombie.author_stagger_animation(clip):
    raise RuntimeError('Fat zombie stagger authoring failed')
if not u.EditorAssetLibrary.save_loaded_asset(clip, False):
    raise RuntimeError('Fat zombie stagger could not be saved')
output = Path('D:/FPS3D/FPSGAME/SourceAssets/FatZombieParry20260914')
output.mkdir(parents=True, exist_ok=True)
(output / 'authoring.json').write_text(json.dumps({
    'asset': target,
    'base': folder + '/A_FatZombie_Idle',
    'authorship': 'Authored recoil and arm brace on the accepted Meshy idle pose',
    'fps': 120, 'frames': [0, 108], 'seconds': 0.9, 'loop': False,
    'recoil_end': 0.1, 'hold_end': 0.6, 'recovery_end': 0.9,
    'parry_entry_time': 0.1, 'attack_contact_seconds': [0.65, 0.78],
    'attack_contact_reference': contact_reference,
    'control_seconds': 1.0, 'total_knockback_cm': 100,
    'status': 'Authored and saved; gameplay and visual testing remain manual'
}, indent=2), encoding='utf-8')
u.log('FAT_ZOMBIE_STAGGER_AUTHORED ' + target)
