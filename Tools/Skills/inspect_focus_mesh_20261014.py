"""Read-only book mesh/skeleton compatibility and bound-pose evaluation."""
import json
from pathlib import Path
import unreal as u
root = '/Game/Weapons/SpellbookEvildeer20261009/PagesV1'
mesh = u.load_asset(root + '/Meshes/SK_Spellbook_Alchemy_16Pages')
out = {'mesh_skeleton': mesh.get_editor_property('skeleton').get_path_name(), 'samples': []}
for name, time in [('A_Spellbook_16Pages_Open', 1.95), ('A_Spellbook_16Pages_Flip', 4.)]:
    clip = u.load_asset(root + '/Animations/' + name)
    options = u.AnimPoseEvaluationOptions()
    options.set_editor_property('evaluation_type', u.AnimDataEvalType.COMPRESSED)
    options.set_editor_property('optional_skeletal_mesh', mesh)
    pose = u.AnimPoseExtensions.get_anim_pose_at_time(clip, time, options)
    out['samples'].append({'clip': name, 'skeleton': clip.get_editor_property('skeleton').get_path_name(), 'bones': {n: str(u.AnimPoseExtensions.get_bone_pose(pose, n, u.AnimPoseSpaces.LOCAL)) for n in ['Book_Root', 'Book_Back', 'Cover_Front']}})
Path('D:/FPS3D/FPSGAME/Saved/FocusDragon20261014/mesh-compatibility.json').write_text(json.dumps(out, indent=2), encoding='utf-8')
print(json.dumps(out))
