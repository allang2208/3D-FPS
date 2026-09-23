"""Offline inspection of the requested Mutant3 clip boundaries and gait phases."""
import bpy, json, math
from pathlib import Path
from mathutils import Vector

ROOT = Path(__file__).parent
bpy.ops.wm.open_mainfile(filepath=str(ROOT.parent/'hand_ground_fix/Mutant3_Khaimera_ClawGrounded.blend'))
rig = next(o for o in bpy.data.objects if o.type == 'ARMATURE')
scene = bpy.context.scene
names = ['Hips','Spine','Spine01','Spine02','Head','LeftHand','RightHand',
         'LeftUpLeg','RightUpLeg','LeftLeg','RightLeg','LeftFoot','RightFoot']
names = [n for n in names if n in rig.pose.bones]
clips = {}
for role in ['FeralIdle','FeralRun','FeralSprint','ClawA','ClawB','ClawC','PounceWindup','PounceFlight','PounceLand']:
    action = bpy.data.actions['A_Mutant3_'+role]
    rig.animation_data.action = action
    if action.slots: rig.animation_data.action_slot = action.slots[0]
    for track in rig.animation_data.nla_tracks: track.mute = True
    poses = []
    for frame in range(round(action.frame_range[0]), round(action.frame_range[1])+1):
        scene.frame_set(frame)
        poses.append({n: dict(position=list((rig.matrix_world@rig.pose.bones[n].matrix).translation),
                             local_rotation=list(rig.pose.bones[n].rotation_quaternion)) for n in names})
    clips[role] = poses

def distance(a,b):
    positions = {n: (Vector(a[n]['position'])-Vector(b[n]['position'])).length*100 for n in names}
    from mathutils import Quaternion
    angles = {n: math.degrees(Quaternion(a[n]['local_rotation']).rotation_difference(Quaternion(b[n]['local_rotation'])).angle) for n in names}
    angles = {n:min(a,360-a) for n,a in angles.items()}
    return dict(position_delta_cm=positions, local_rotation_delta_deg=angles)

pairs = [('FeralIdle','PounceWindup'),('PounceWindup','PounceFlight'),('PounceFlight','PounceLand'),
         ('PounceLand','FeralIdle'),('ClawA','ClawB'),('ClawB','ClawC'),('ClawC','ClawA')]
report = {'bones':list(rig.data.bones.keys()), 'boundaries':{}, 'gaits':{}, 'landing_early':{}}
for a,b in pairs:
    d = distance(clips[a][-1],clips[b][0])
    report['boundaries'][a+' -> '+b] = d
    print('BOUNDARY',a,b,'hips_cm',round(d['position_delta_cm']['Hips'],2),
          'max_hand_cm',round(max(d['position_delta_cm'][n] for n in ['LeftHand','RightHand']),2),
          'max_local_deg',round(max(d['local_rotation_delta_deg'].values()),2))
for role in ['FeralRun','FeralSprint']:
    poses = clips[role]
    feet = {}
    for foot in ['LeftFoot','RightFoot']:
        heights = [p[foot]['position'][2] for p in poses[:-1]]
        minima = [i for i,z in enumerate(heights) if z<heights[(i-1)%len(heights)] and z<=heights[(i+1)%len(heights)]]
        feet[foot] = dict(minima_frames=minima, heights_cm=[round(z*100,2) for z in heights])
    report['gaits'][role] = dict(duration=(len(poses)-1)/60,feet=feet)
    print('GAIT',role,report['gaits'][role]['duration'],{n:v['minima_frames'] for n,v in feet.items()})
for frame in [12,24,33,39]:
    report['landing_early'][str(frame)] = distance(clips['PounceFlight'][frame],clips['PounceLand'][0])
(ROOT/'clip_boundaries.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
(ROOT/'clip_poses.json').write_text(json.dumps(clips),encoding='utf-8')
print('TRANSITION_INSPECTION_SAVED')
