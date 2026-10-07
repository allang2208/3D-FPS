"""Read the actual Mutant3 claw assets as M27 motion-authoring inputs."""
from pathlib import Path
import json
import unreal as u

ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/MantisM27/ClawV3')
ROOT.mkdir(parents=True,exist_ok=True)
DONOR='/Game/Monsters/Mutant3Meshy/KhaimeraV2'
mesh=u.load_asset(DONOR+'/SK_Mutant3_Claw')
opt=u.AnimPoseEvaluationOptions()
opt.set_editor_property('evaluation_type',u.AnimDataEvalType.RAW)
opt.set_editor_property('optional_skeletal_mesh',mesh)
opt.set_editor_property('should_retarget',False)
opt.set_editor_property('extract_root_motion',False)

def transform(t):
    p=t.translation;q=t.rotation;s=t.scale3d
    return {'p':[p.x,p.y,p.z],'q':[q.w,q.x,q.y,q.z],'s':[s.x,s.y,s.z]}

record={'source_mesh':mesh.get_path_name(),'fps':60,'space':'Unreal component centimeters','clips':{}}
for role in ['FeralIdle','ClawA','ClawB','ClawC']:
    clip=u.load_asset(DONOR+'/Animations/A_Mutant3_'+role)
    pose=u.AnimPoseExtensions.get_anim_pose_at_time(clip,0,opt)
    names=[str(n) for n in u.AnimPoseExtensions.get_bone_names(pose)]
    names=[n for n in names if not any(k in n for k in ['Index','Middle','Ring','Pinky','Thumb'])]
    ref={n:transform(u.AnimPoseExtensions.get_ref_bone_pose(pose,n,u.AnimPoseSpaces.WORLD)) for n in names}
    length=clip.get_play_length();count=round(length*60)+1
    # One idle pose is the neutral source for this attack adaptation.
    times=[0.] if role=='FeralIdle' else [min(i/60,length) for i in range(count)]
    frames=[]
    for t in times:
        pose=u.AnimPoseExtensions.get_anim_pose_at_time(clip,t,opt)
        frames.append({n:transform(u.AnimPoseExtensions.get_bone_pose(pose,n,u.AnimPoseSpaces.WORLD)) for n in names})
    record['clips'][role]={'asset':clip.get_path_name(),'seconds':length,'times':times,'reference':ref,'frames':frames,
                           'import_files':[str(p) for p in clip.get_editor_property('asset_import_data').extract_filenames()]}
    print('M27_SOURCE_READ '+role+' '+str(length)+' seconds',flush=True)
bp=u.load_class(None,'/Game/Monsters/MantisM27/BP_MantisM27.BP_MantisM27_C')
d=u.get_default_object(bp)
record['m27_before']={}
for key in ['visual_mesh','left_slash_clip','right_slash_clip','idle_clip','walk_clip','contact_time','contact_end','recovery_time','attack_damage','attack_range']:
    value=d.get_editor_property(key)
    record['m27_before'][key]=value.get_path_name() if isinstance(value,u.Object) else value
(ROOT/'claw_authoring_sources.json').write_text(json.dumps(record,ensure_ascii=False),encoding='utf-8')
print('M27_CLAW_SOURCE_INPUTS_SAVED',flush=True)
