"""Capture authored retargeted death head tracks for female camera production."""
import json
from pathlib import Path
import unreal as u

WORK = Path('D:/FPS3D/FPSGAME/SourceAssets/KaitlinPlayer20261023')
clips = json.loads((WORK / 'retargeted_clips.json').read_text())
body = json.loads((WORK / 'NativeGeometry/MHC_Kaitlin_Body.json').read_text())
bones = body['bones']
head = next(b for b in bones if b['name'] == 'head')
chain = []
index = head['index']
while index >= 0:
    chain.append(bones[index]['name'])
    index = bones[index]['parent']
chain.reverse()
result = {}
for role in ('Dead', 'Dead.Crouched'):
    clip = u.load_asset(clips[role])
    model = clip.get_editor_property('data_model_interface')
    rate = model.get_frame_rate()
    frequency = rate.numerator / rate.denominator
    frames = []
    for index in range(model.get_number_of_keys()):
        poses = u.AnimationLibrary.get_bone_poses_for_time(clip, chain, index / frequency, False)
        world = u.Transform()
        for pose in poses:
            world = u.MathLibrary.compose_transforms(pose, world)
        p, q = world.translation, world.rotation
        frames.append([p.x, p.y, p.z, q.x, q.y, q.z, q.w])
    result[role] = {'asset': clips[role], 'rate': frequency, 'frames': frames}
(WORK / 'death_head_tracks.json').write_text(json.dumps(result, separators=(',', ':')), encoding='utf-8')
(WORK / 'capture_death_tracks_status.json').write_text(json.dumps({'remaining': 0, 'complete': True}), encoding='utf-8')
print('KAITLIN_DEATH_HEAD_TRACKS_AUTHORED', flush=True)
