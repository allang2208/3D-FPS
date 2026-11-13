"""Carry the standard sword's four-cut path on the native two-hand haft grip."""
import json
from pathlib import Path
from mathutils import Matrix, Quaternion, Vector

def weapon_frames(idle):
    source = Path(__file__).resolve().parents[1]
    clip = json.loads((source/'Standard.json').read_text())
    hierarchy = json.loads((source.parent/'SwordUppercut20261003/GripRecoveryV15/inputs.json').read_text())['parents']
    flip = Matrix.Diagonal(Vector((1, -1, 1)))
    root = idle['wpn_root']
    rest_rotation = root.to_quaternion()
    rest_center = (idle['hand_l'].translation + idle['hand_r'].translation) * .5
    rest_offset = rest_rotation.inverted() @ (root.translation - rest_center)

    def sample(frame):
        cache = {}
        def world(name):
            if name not in cache:
                key = frame[name]
                local = Matrix.LocRotScale(Vector(key['p']), Quaternion(key['q']), Vector(key['s']))
                parent = hierarchy[name]
                cache[name] = world(parent) @ local if parent in frame else local
            return cache[name]
        center = (world('hand_l').translation + world('hand_r').translation) * .005
        rotation = (flip @ world('WPN_root').to_quaternion().to_matrix() @ flip).to_quaternion()
        return flip @ center, rotation

    # Align the blade axes while retaining the native grip's neutral roll.
    # Register the stroke at the middle of the two palms: the long haft has
    # a different guard-to-hand offset from the sword.
    center0, sword0 = sample(clip['frames'][0])
    z = Vector((0,0,1))
    align = (rest_rotation @ z).rotation_difference(sword0 @ z)
    roll = sword0.inverted() @ align @ rest_rotation
    def envelope(t):
        t = min(1.,max(0.,t))
        return t*t*t*(10.+t*(-15.+6.*t))
    poses = []
    count = len(clip['frames'])
    for i, frame in enumerate(clip['frames']):
        center, sword = sample(frame)
        # The initial lift and final recovery join the actual long-haft idle.
        # All four contact frames are inside the full-strength interval.
        t = i / clip['fps']
        weight = envelope(t/.22) * envelope(((count-1-i)/clip['fps'])/.48)
        rotation = rest_rotation.slerp(sword @ roll, weight)
        center = rest_center + (center-center0)*weight
        poses.append(Matrix.LocRotScale(center + rotation @ rest_offset, rotation, root.to_scale()))
    return poses,clip['markers']
