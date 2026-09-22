import unreal as u,json
from pathlib import Path
out=Path('D:/FPS3D/FPSGAME/SourceAssets/WitchRebuilt20260921/DrapeGrip20260922')
print('Pose methods:',[n for n in dir(u.AnimPoseExtensions) if 'pose' in n or 'bone' in n])
for name in ('get_reference_pose','get_ref_bone_pose'):
    method=getattr(u.AnimPoseExtensions,name,None)
    print(name,str(getattr(method,'__doc__',''))[:3000])
print('game_world',bool(u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world()))
print('dirty',[p.get_path_name() for p in list(u.EditorLoadingAndSavingUtils.get_dirty_content_packages())+list(u.EditorLoadingAndSavingUtils.get_dirty_map_packages())])
clip=u.load_asset('/Game/Monsters/WitchRebuilt/Animations/A_WitchRebuilt_Idle')
pose=u.AnimPoseExtensions.get_anim_pose_at_frame(clip,0,u.AnimPoseEvaluationOptions())
result={}
for name in ('hand_r','middle_01_r','index_01_r','pinky_01_r'):
    t=u.AnimPoseExtensions.get_ref_bone_pose(pose,name,u.AnimPoseSpaces.WORLD)
    result[name]=[t.translation.x,t.translation.y,t.translation.z]
(out/'ue_reference_bones.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print(result)
