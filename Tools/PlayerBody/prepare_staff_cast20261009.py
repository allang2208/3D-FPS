"""Import local KayKit magic takes, retarget to Jason, and export editable poses."""
import json
from pathlib import Path
import unreal as u

ROOT=Path('D:/FPS3D/FPSGAME')
OUT=ROOT/'SourceAssets/ThirdPersonStaffCast20261009'
DEST='/Game/Characters/JasonPlayer20261003/StaffCast20261009'
OUT.mkdir(parents=True,exist_ok=True)
lib=u.EditorAssetLibrary
cfg=json.loads((ROOT/'Content/ColdSteelData/player_body.json').read_text(encoding='utf-8-sig'))
info=json.loads((ROOT/'SourceAssets/ThirdPersonSwordFree20261005/imported-sources.json').read_text())['KayKit']
source_mesh=u.load_asset(info['mesh'])
source_dir=DEST+'/Source'
if not lib.does_directory_exist(source_dir):
    options=u.FbxImportUI()
    options.automated_import_should_detect_type=False
    options.mesh_type_to_import=u.FBXImportType.FBXIT_ANIMATION
    options.import_as_skeletal=False
    options.import_mesh=False
    options.import_animations=True
    options.import_materials=False
    options.import_textures=False
    options.create_physics_asset=False
    options.skeleton=source_mesh.skeleton
    options.anim_sequence_import_data.set_editor_property('use_default_sample_rate',False)
    options.anim_sequence_import_data.set_editor_property('custom_sample_rate',60)
    task=u.AssetImportTask()
    task.filename=str(ROOT/'SourceAssets/ThirdPersonSwordFree20261005/KayKit/KayKit_Character_Animations_1.1/Animations/fbx/Rig_Medium/Rig_Medium_CombatRanged.fbx')
    task.destination_path=source_dir
    task.destination_name='KayKit_Magic'
    task.automated=True
    task.replace_existing=False
    task.save=True
    task.options=options
    task.factory=u.FbxFactory()
    u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
sources=[u.load_asset(p) for p in lib.list_assets(source_dir,True,False)]
target=u.load_asset(cfg['body_mesh'])
ref=target.skeleton.get_reference_pose()
names=[str(n) for n in u.AnimPoseExtensions.get_bone_names(ref)]
comp=u.new_object(u.SkeletalMeshComponent)
comp.set_skeletal_mesh_asset(target)
parents=[names.index(str(comp.get_parent_bone(n))) if str(comp.get_parent_bone(n)) in names else -1 for n in names]
def pack(t):
    return [*t.translation.to_tuple(),t.rotation.x,t.rotation.y,t.rotation.z,t.rotation.w,*t.scale3d.to_tuple()]
def read(clip):
    opt=u.AnimPoseEvaluationOptions()
    opt.optional_skeletal_mesh=target
    opt.evaluation_type=u.AnimDataEvalType.SOURCE
    duration=clip.get_play_length()
    frames=[]
    for i in range(round(duration*60)+1):
        pose=u.AnimPoseExtensions.get_anim_pose_at_time(clip,min(i/60,duration),opt)
        frames.append([pack(u.AnimPoseExtensions.get_bone_pose(pose,n,u.AnimPoseSpaces.LOCAL)) for n in names])
    return dict(asset=clip.get_path_name(),duration=duration,rate=60,frames=frames)
data=dict(mesh=target.get_path_name(),names=names,parents=parents,
          reference=[pack(u.AnimPoseExtensions.get_bone_pose(ref,n,u.AnimPoseSpaces.LOCAL)) for n in names],clips={})
for role,suffix in [('Gather','Ranged_Magic_Raise'),('Release','Ranged_Magic_Shoot')]:
    source=next(a for a in sources if isinstance(a,u.AnimSequence) and a.get_name().endswith('_'+suffix))
    path=DEST+'/Donors/J_'+source.get_name()
    clip=u.load_asset(path) if lib.does_asset_exist(path) else None
    if not clip:
        inputs=u.IKRetargetBatchOperationInputs()
        inputs.assets_to_retarget=[lib.find_asset_data(source.get_path_name())]
        inputs.source_mesh=source_mesh
        inputs.target_mesh=target
        inputs.ik_retarget_asset=u.load_asset('/Game/Characters/JasonPlayer20261003/SwordFullBody20261005/Rig/RTG_KayKit_Jason_Sword')
        inputs.prefix='J_'
        inputs.target_path=DEST+'/Donors'
        inputs.include_referenced_assets=False
        inputs.overwrite_existing_files=False
        clip=next(a.get_asset() for a in u.IKRetargetBatchOperation.run_batch_retarget(inputs) if isinstance(a.get_asset(),u.AnimSequence))
    if not lib.save_loaded_asset(clip,False):raise RuntimeError('Cannot save '+path)
    data['clips'][role]=read(clip)
    data['clips'][role]['source']=source.get_path_name()
data['idle']=read(u.load_asset(cfg['clips']['Unarmed.Idle']))
(OUT/'donors.json').write_text(json.dumps(data,separators=(',',':')))
print('STAFF_CAST_DONORS_SAVED')
