"""Read the reported M66 death pose and collision assets without playing or mutating them."""
import json
from pathlib import Path
import unreal as u

ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/IncineratorBossM66/DeathGroundV07')
(ROOT/'Records').mkdir(parents=True,exist_ok=True)
bp=u.load_asset('/Game/Monsters/IncineratorBossM66/BP_M66RigPreview')
cdo=u.get_default_object(bp.generated_class())
mesh=cdo.get_editor_property('visual_mesh');physics=cdo.get_editor_property('reaction_physics');clip=cdo.get_editor_property('death_clip')
api=u.get_default_object(u.PhysicsAssetToolset)
options=u.AnimPoseEvaluationOptions();options.evaluation_type=u.AnimDataEvalType.SOURCE
options.optional_skeletal_mesh=mesh;options.should_retarget=False;options.extract_root_motion=False
def transform(value):
    return {'position':[value.translation.x,value.translation.y,value.translation.z],'rotation':[value.rotation.x,value.rotation.y,value.rotation.z,value.rotation.w],
            'scale':[value.scale3d.x,value.scale3d.y,value.scale3d.z]}
report={'mesh':mesh.get_path_name(),'physics':physics.get_path_name(),'death_clip':clip.get_path_name(),
        'mesh_physics':mesh.get_editor_property('physics_asset').get_path_name(),'poses':[],'bodies':[]}
for seconds in (0.,.9,2.3):
    pose=u.AnimPoseExtensions.get_anim_pose_at_time(clip,seconds,options)
    row={'time':seconds,'bones':{}}
    for name in u.AnimPoseExtensions.get_bone_names(pose):
        row['bones'][str(name)]={'local':transform(u.AnimPoseExtensions.get_bone_pose(pose,name,u.AnimPoseSpaces.LOCAL)),
            'world':transform(u.AnimPoseExtensions.get_bone_pose(pose,name,u.AnimPoseSpaces.WORLD)),
            'reference':transform(u.AnimPoseExtensions.get_ref_bone_pose(pose,name,u.AnimPoseSpaces.WORLD))}
    report['poses'].append(row)
for name in api.call_method('GetBodyNames',(physics,)):
    report['bodies'].append({'bone':str(name),'shapes':[s.export_text() for s in api.call_method('GetBodyShapes',(physics,name))]})
report['constraints']=[c.export_text() for c in api.call_method('GetConstraints',(physics,))]
(ROOT/'Records/death_inputs.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('M66_DEATH_INPUTS_SAVED '+json.dumps({k:report[k] for k in ('mesh','physics','death_clip')}))
