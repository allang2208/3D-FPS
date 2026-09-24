"""Scoped read-back check for the user-reported invisible F6 dog issue."""
import gc
import json
from pathlib import Path
import unreal as u


def main():
    project = Path('D:/FPS3D/FPSGAME')
    folder = project/'SourceAssets/InfectedDogMeshy20260924/CompletionV2'
    installed = json.loads((folder/'f6_scale_repair.json').read_text(encoding='utf-8'))
    mesh = u.load_asset('/Game/Monsters/InfectedDog/MeshyV2/SK_InfectedDog_MeshyV2')
    report = {'scope': 'Saved animation source and runtime-compressed root scale at start/middle/end',
              'clips': {}, 'game_started': False, 'visual_reviewed': False, 'failures': []}
    for role, row in installed['clips'].items():
        clip = u.load_asset(row['asset'])
        result = {}; report['clips'][role] = result
        for label, mode in [('source', u.AnimDataEvalType.SOURCE), ('compressed', u.AnimDataEvalType.COMPRESSED)]:
            options = u.AnimPoseEvaluationOptions()
            options.set_editor_property('evaluation_type', mode)
            options.set_editor_property('optional_skeletal_mesh', mesh)
            result[label] = []
            for time in [0., clip.get_play_length()*.5, clip.get_play_length()]:
                pose = u.AnimPoseExtensions.get_anim_pose_at_time(clip, time, options)
                ref = u.AnimPoseExtensions.get_ref_bone_pose(pose, 'root', u.AnimPoseSpaces.LOCAL)
                root = u.AnimPoseExtensions.get_bone_pose(pose, 'root', u.AnimPoseSpaces.LOCAL)
                head = u.AnimPoseExtensions.get_bone_pose(pose, 'head', u.AnimPoseSpaces.WORLD)
                s = root.scale3d; r = ref.scale3d
                error = max(abs(s.x-r.x),abs(s.y-r.y),abs(s.z-r.z))
                result[label].append({'seconds': time, 'root_scale': [s.x,s.y,s.z],
                                      'head_cm': [head.translation.x,head.translation.y,head.translation.z],
                                      'root_error': error})
                if error > .01:
                    report['failures'].append([role, label, time, error])
    report['passed'] = not report['failures']
    path = project/'Saved/InfectedDogMeshy/F6ScaleReadback.json'
    path.write_text(json.dumps(report, indent=2), encoding='utf-8')
    if report['failures']: raise RuntimeError(str(report['failures']))
    print('F6_SCALE_READBACK_PASS clips=' + str(len(report['clips'])) + ' samples=126')


main()
gc.collect()
