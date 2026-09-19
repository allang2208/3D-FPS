"""Read source animation timing and hand contact stations before authoring."""
import unreal as u,json
from pathlib import Path
P=Path(__file__).parent
mesh=u.load_asset('/Game/Weapons/FrostCrystalSword20260915/Modules20260915/SK_FrostSword_Arms')
options=u.AnimPoseEvaluationOptions();options.evaluation_type=u.AnimDataEvalType.SOURCE;options.optional_skeletal_mesh=mesh
clips=['Idle','Walk','Equip','Inspect','Overhead','Slash1','Slash2','Thrust','PommelStrike','HeavyCharge','HeavyRelease','Guard','GuardHit','GuardBreak']
rows=[]
for name in clips:
    a=u.load_asset('/Game/Weapons/AzureRunesword20260913/A_RuneSword_'+name)
    duration=a.get_play_length();frame_count=u.AnimationLibrary.get_num_frames(a)
    samples=[]
    for i in range(13):
        t=duration*i/12;pose=u.AnimPoseExtensions.get_anim_pose_at_time(a,t,options)
        w=u.AnimPoseExtensions.get_bone_pose(pose,'WPN_root',u.AnimPoseSpaces.WORLD)
        hands={}
        for side in ['l','r']:
            h=u.AnimPoseExtensions.get_bone_pose(pose,'hand_'+side,u.AnimPoseSpaces.WORLD)
            v=w.inverse_transform_location(h.translation)
            hands[side]=[v.x,v.y,v.z]
        samples.append({'time':t,'hand_weapon_space':hands})
    rows.append({'name':name,'source':a.get_path_name(),'seconds':duration,'intervals':frame_count,'fps':frame_count/duration,'samples':samples})
(P/'source_animation_inputs.json').write_text(json.dumps(rows,indent=2))
u.log('GRIP_ANIMATION_INPUTS_READ')
