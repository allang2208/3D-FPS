"""Author female procedural coordinates and death camera tracks from native frames."""
import json
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation
from scipy.ndimage import gaussian_filter1d

WORK = Path('D:/FPS3D/FPSGAME/SourceAssets/KaitlinPlayer20261023')
read = lambda p: json.loads(p.read_text(encoding='utf-8-sig'))
config = read(WORK / 'FitInputs/player_body.json')
captured = read(WORK / 'FitInputs/captured.json')
male = read(WORK / 'FitInputs' / captured[config['body_mesh']]['file'])
body = read(WORK / 'NativeGeometry/MHC_Kaitlin_Body.json')
face = read(WORK / 'NativeGeometry/SKM_MHC_Kaitlin_FaceMesh.json')
male_bones = {b['name']: b for b in male['bones']}
bones = {b['name']: b for b in body['bones']}
face_bones = {b['name']: b for b in face['bones']}
head = bones['head']
mouth = np.mean([face_bones[name]['position'] for name in ('FACIAL_C_LipUpper2', 'FACIAL_C_LipLower2')], axis=0)
mouth += [0., .25, 0.]
mouth_local = (mouth - head['position']) @ np.linalg.inv(head['axes'])
eyes = np.mean([face_bones[name]['position'] for name in ('FACIAL_L_Eye', 'FACIAL_R_Eye')], axis=0)
eye_offset = eyes - head['position']
names = ('pelvis', 'spine_03', 'spine_05', 'head', 'hand_l', 'hand_r', 'foot_l', 'foot_r')
a = np.asarray([male_bones[name]['position'] for name in names])
b = np.asarray([bones[name]['position'] for name in names])
ratio = (a * b).sum(0) / (a * a).sum(0)
calibration = {'pose_scale': (np.asarray(config['pose_scale']) * ratio).tolist(),
               'consume_mouth_in_head': mouth_local.tolist(), 'eye_offset_body_space': eye_offset.tolist(),
               'first_person_body': dict(config['first_person_body']), 'death_presentation': {}}
# The lower-body display follows the full-body pose. Adjust only its authored
# camera-space separation for the measured torso depth of this body.
mp, fp = np.asarray(male['positions']), np.asarray(body['positions'])
from body_surface_fit import regions
mt, ft = mp[regions(male) == 'torso'], fp[regions(body) == 'torso']
front_delta = np.percentile(ft[:, 1], 99) - np.percentile(mt[:, 1], 99)
for key in ('camera_forward_cm', 'camera_crouch_forward_cm', 'torso_front_clearance_cm'):
    calibration['first_person_body'][key] += float(front_delta)
tracks = read(WORK / 'death_head_tracks.json')
for role, key, impact in [('Dead', 'standing_camera', 1.), ('Dead.Crouched', 'crouched_camera', .73)]:
    data = tracks[role]
    frames = np.asarray(data['frames'])
    initial = Rotation.from_quat(frames[0, 3:7])
    duration = (len(frames) - 1) / data['rate']
    camera = []
    for i, frame in enumerate(frames):
        age = i / data['rate']
        turn = Rotation.from_quat(frame[3:7]) * initial.inv()
        forward = turn.apply([0., 1., 0.])
        pitch = np.clip(np.degrees(np.arcsin(np.clip(forward[2], -1., 1.))), -58., 30.)
        yaw = np.clip(np.degrees(np.arctan2(-forward[0], forward[1])), -12., 12.)
        settle = np.clip((age - impact) / (duration - impact), 0., 1.)
        settle = settle * settle * (3. - 2. * settle)
        pitch = pitch * (1. - settle) - 14. * settle
        camera.append([*(frame[:3] + eye_offset), pitch, yaw, 18. * (i / (len(frames) - 1)) ** 2])
    camera = np.asarray(camera)
    camera[:, 3:] = gaussian_filter1d(camera[:, 3:], .7, axis=0, mode='nearest')
    calibration['death_presentation'][key] = camera.round(5).tolist()
(WORK / 'calibration.json').write_text(json.dumps(calibration, indent=2), encoding='utf-8')
print('KAITLIN_NATIVE_CALIBRATION_AUTHORED', flush=True)
