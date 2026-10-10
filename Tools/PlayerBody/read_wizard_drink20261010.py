"""Read imported Wizard drinking motion and current body inputs for authoring."""
import json
from pathlib import Path
import unreal as u

root=Path('D:/FPS3D/FPSGAME')
out=root/'SourceAssets/ThirdPersonWizardDrink20261010'
out.mkdir(parents=True,exist_ok=True)
cfg=json.loads((root/'Content/ColdSteelData/player_body.json').read_text(encoding='utf-8-sig'))

def pack(t):
    return [*t.translation.to_tuple(),t.rotation.x,t.rotation.y,t.rotation.z,t.rotation.w,*t.scale3d.to_tuple()]

def read(mesh, paths, full=False):
    mesh=u.load_asset(mesh)
    pose=mesh.skeleton.get_reference_pose()
    names=[str(n) for n in u.AnimPoseExtensions.get_bone_names(pose)]
    comp=u.new_object(u.SkeletalMeshComponent);comp.set_skeletal_mesh_asset(mesh)
    result=dict(mesh=mesh.get_path_name(),skeleton=mesh.skeleton.get_path_name(),names=names,
        parents=[names.index(str(comp.get_parent_bone(n))) if str(comp.get_parent_bone(n)) in names else -1 for n in names],
        reference=[pack(u.AnimPoseExtensions.get_bone_pose(pose,n,u.AnimPoseSpaces.LOCAL)) for n in names],clips={})
    opts=u.AnimPoseEvaluationOptions();opts.optional_skeletal_mesh=mesh;opts.evaluation_type=u.AnimDataEvalType.SOURCE
    for key,path in paths.items():
        clip=u.load_asset(path);length=clip.get_play_length();frames=[]
        count=round(length*60) if full else 0
        available=None
        for i in range(count+1):
            sampled=u.AnimPoseExtensions.get_anim_pose_at_time(clip,length*i/count if count else 0.,opts)
            if available is None: available={str(n) for n in u.AnimPoseExtensions.get_bone_names(sampled)}
            frames.append([pack(u.AnimPoseExtensions.get_bone_pose(sampled,n,u.AnimPoseSpaces.LOCAL)) if n in available else result['reference'][j] for j,n in enumerate(names)])
        result['clips'][key]=dict(asset=clip.get_path_name(),duration=length,rate=60,
            source_frames=u.AnimationLibrary.get_num_frames(clip),frames=frames,missing_source_bones=[n for n in names if n not in available])
        print('WIZARD_INPUT',key,length,len(frames),'bones',len(names))
    return result

if __name__=='__main__':
    data=dict(source=read('/Game/BattleWizardPBR/Meshes/WizardSM',{'drink':'/Game/BattleWizardPBR/Animations/PotionDrinkAnim'},True),
        target=read(cfg['body_mesh'],{'idle':cfg['clips']['Unarmed.Idle'],'book':cfg['clips']['Staff.BookCarry']}),
        previous_clips={k:v for k,v in cfg['clips'].items() if k.startswith('Consume.')},
        mouth_in_head=cfg['consume_mouth_in_head'],pose_scale=cfg['pose_scale'],
        source_url='https://www.fab.com/listings/a42813d8-92bd-4ee4-a3de-fd12f568ded2')
    (out/'inputs.json').write_text(json.dumps(data,separators=(',',':')),encoding='utf-8')
    print('WIZARD_DRINK_INPUTS_SAVED',str(out/'inputs.json'))
