"""Export native retarget pose data, including the pelvis root, for offline fitting."""
import json
from pathlib import Path
import unreal as u

ROOT = Path('D:/FPS3D/FPSGAME/SourceAssets/BlindSupplicantM07Meshy20261001/LibrarySweepV27')
record = json.loads((ROOT/'native_retarget_v27.json').read_text(encoding='utf-8'))
if (record.get('limb_rotation_mode') != 'OneToOne' or
        record.get('root_policy') != 'PelvisRetarget_NoGroundRootCopy'):
    import runpy
    runpy.run_path('D:/FPS3D/FPSGAME/Tools/BlindSupplicantM07/retarget_library_sweep_v27.py')
    record = json.loads((ROOT/'native_retarget_v27.json').read_text(encoding='utf-8'))
mesh, clip = u.load_asset(record['target_mesh']), u.load_asset(record['raw_asset'])
component = u.new_object(u.SkeletalMeshComponent)
component.set_skeletal_mesh_asset(mesh)
bones = [str(component.get_bone_name(i)) for i in range(component.get_num_bones())]
options = u.AnimPoseEvaluationOptions()
options.evaluation_type = u.AnimDataEvalType.RAW
options.optional_skeletal_mesh = mesh


def transform(t):
    return dict(translation_cm=[t.translation.x,t.translation.y,t.translation.z],
        rotation_xyzw=[t.rotation.x,t.rotation.y,t.rotation.z,t.rotation.w])


frames = []
for i in range(round(record['duration_seconds']*60)+1):
    pose = u.AnimPoseExtensions.get_anim_pose_at_time(clip, i/60., options)
    frames.append({b:transform(u.AnimPoseExtensions.get_bone_pose(pose,b,u.AnimPoseSpaces.WORLD)) for b in bones})
reference = {b:transform(u.AnimPoseExtensions.get_ref_bone_pose(pose,b,u.AnimPoseSpaces.WORLD)) for b in bones}
output = ROOT/'Native/native_pose_v27.json'
output.write_text(json.dumps(dict(asset=record['raw_asset'], fps=60, reference=reference, frames=frames)), encoding='utf-8')
record['pose_cache'] = str(output)
(ROOT/'native_retarget_v27.json').write_text(json.dumps(record, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
print('M07_V27_NATIVE_POSE_EXPORTED bones='+str(len(bones))+' frames='+str(len(frames)))
