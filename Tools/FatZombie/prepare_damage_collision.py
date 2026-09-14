"""Export the UE reference frames used to author bone-local hit shapes."""
import json
from pathlib import Path
import unreal as u

mesh = u.load_asset('/Game/Monsters/FatZombieMeshy/SK_FatZombie_Meshy')
pose = u.AnimPoseExtensions.get_reference_pose(mesh.skeleton)
names = u.AnimPoseExtensions.get_bone_names(pose)
frames = {}
for name in names:
    t = u.AnimPoseExtensions.get_ref_bone_pose(pose, name, u.AnimPoseSpaces.WORLD)
    p, q, s = t.translation, t.rotation, t.scale3d
    frames[str(name)] = {'location': [p.x, p.y, p.z],
                         'quaternion_xyzw': [q.x, q.y, q.z, q.w],
                         'scale': [s.x, s.y, s.z]}
out = Path('D:/FPS3D/FPSGAME/SourceAssets/FatZombieMeshy20260913/damage_collision_rig.json')
out.write_text(json.dumps(frames, indent=2), encoding='utf-8')
u.log('FAT_DAMAGE_REFERENCE_EXPORTED')
