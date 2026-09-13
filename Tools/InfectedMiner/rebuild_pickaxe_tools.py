"""Compose the miner from actual EBS mining clips and an existing relaxed arm.

Run with UnrealEditor-Cmd -run=pythonscript -script=<this file> -NullRHI.
The two-hand mining source is explicitly adapted into a single-hand composite.
"""
import json
from pathlib import Path
import unreal

ROOT=Path(unreal.Paths.project_dir())
OUT=ROOT/'SourceAssets/InfectedMiner20260913/PickaxeSingleHand/Delivery'
OUT.mkdir(parents=True,exist_ok=True)
DEST='/Game/Monsters/InfectedMiner/PickaxeSingleHand20260913'
SOURCE='/Game/EasyBuildingSystem/Mannequin'
ACCEPTED='/Game/Monsters/InfectedMiner/AuthoredChopFinal'
lib=unreal.EditorAssetLibrary
assets=unreal.AssetToolsHelpers.get_asset_tools()
source_mesh=unreal.load_asset(SOURCE+'/Mesh/SK_Mannequin')
target_mesh=unreal.load_asset(ACCEPTED+'/SK_InfectedMiner')
accepted_idle=unreal.load_asset(ACCEPTED+'/A_Miner_Idle')

def compose_single_hand(clip,rate):
    model=clip.get_editor_property('data_model_interface')
    controller=clip.get_editor_property('controller')
    tracks=list(model.get_bone_track_names())
    old_frames=model.get_number_of_frames()
    new_frames=max(1,round(old_frames/rate))
    source_seconds=clip.get_play_length()
    idle_tracks=set(accepted_idle.get_editor_property('data_model_interface').get_bone_track_names())
    options=unreal.AnimPoseEvaluationOptions()
    options.set_editor_property('evaluation_type',unreal.AnimDataEvalType.SOURCE)
    options.set_editor_property('should_retarget',False)
    options.set_editor_property('evaluate_curves',False)
    pose_api=unreal.AnimPoseExtensions
    space=unreal.AnimPoseSpaces.LOCAL
    grip=pose_api.get_anim_pose_at_time(accepted_idle,0,options)
    baked={bone:([],[],[]) for bone in tracks}
    # Read the existing local transforms before editing any tracks. No new
    # swing poses or IK targets are authored; only the free arm is layered.
    for frame in range(new_frames+1):
        time=frame/new_frames*source_seconds
        source=pose_api.get_anim_pose_at_time(clip,time,options)
        idle=pose_api.get_anim_pose_at_time(accepted_idle,min(time,accepted_idle.get_play_length()),options)
        for bone in tracks:
            name=str(bone)
            right=name.endswith('_r') and name.startswith(('clavicle','upperarm','lowerarm','hand'))
            finger=name.startswith(('thumb','index','middle','ring','pinky'))
            donor=grip if finger and bone in idle_tracks else idle if right and bone in idle_tracks else source
            transform=pose_api.get_bone_pose(donor,bone,space)
            position,rotation,scale=baked[bone]
            position.append(transform.translation);rotation.append(transform.rotation);scale.append(transform.scale3d)
    # The monster owns animation time directly; bake speed into the sequence.
    controller.open_bracket('Compose single-hand pickaxe motion',False)
    try:
        controller.set_number_of_frames(unreal.FrameNumber(new_frames),False)
        for bone,(position,rotation,scale) in baked.items():
            if not controller.set_bone_track_keys(bone,position,rotation,scale,False):raise RuntimeError('Bone bake failed: '+str(bone))
    finally:controller.close_bracket(False)

def create(name,cls,factory):
    return unreal.load_asset(DEST+'/'+name) or assets.create_asset(name,DEST,cls,factory)

rigs=[]
for name,mesh in [('IK_EBS_Pickaxe',source_mesh),('IK_Miner_Accepted',target_mesh)]:
    rig=create(name,unreal.IKRigDefinition,unreal.IKRigDefinitionFactory())
    control=unreal.IKRigController.get_controller(rig)
    control.set_skeletal_mesh(mesh)
    if not control.apply_auto_generated_retarget_definition():raise RuntimeError('No humanoid template: '+name)
    rigs.append(rig)
retarget=create('RTG_EBS_Pickaxe_Miner',unreal.IKRetargeter,unreal.IKRetargetFactory())
control=unreal.IKRetargeterController.get_controller(retarget)
src=unreal.RetargetSourceOrTarget.SOURCE;tgt=unreal.RetargetSourceOrTarget.TARGET
control.set_ik_rig(src,rigs[0]);control.set_ik_rig(tgt,rigs[1])
control.set_preview_mesh(src,source_mesh);control.set_preview_mesh(tgt,target_mesh)
control.remove_all_ops();control.add_default_ops()
control.auto_map_chains(unreal.AutoMapChainType.EXACT,True)
pose=control.get_current_retarget_pose_name(tgt)
control.reset_retarget_pose(pose,[],tgt)
control.auto_align_all_bones(tgt,unreal.RetargetAutoAlignMethod.CHAIN_TO_CHAIN)
control.reset_retarget_pose(pose,['foot_l','foot_r','ball_l','ball_r'],tgt)
for i in range(control.get_num_retarget_ops()):
    op=control.get_op_controller(i)
    if op and 'RunIKRig' in op.get_class().get_name():control.set_retarget_op_enabled(i,False)
for asset in rigs+[retarget]:lib.save_loaded_asset(asset,False)

sources={'Attack':'A_Mannequin_PickAxe_Act','Idle':'A_Mannequin_Pickaxe_Idle','Walk':'A_Mannequin_Pickaxe_Walk'}
inputs=unreal.IKRetargetBatchOperationInputs()
inputs.assets_to_retarget=[lib.find_asset_data(SOURCE+'/Animations/'+name) for name in sources.values()]
inputs.source_mesh=source_mesh;inputs.target_mesh=target_mesh;inputs.ik_retarget_asset=retarget
inputs.target_path=DEST;inputs.search='A_Mannequin';inputs.replace='A_Miner_SingleHand'
inputs.include_referenced_assets=False;inputs.overwrite_existing_files=True
if not unreal.IKRetargetBatchOperation.run_batch_retarget(inputs):raise RuntimeError('No retarget output')

clips={};clip_report={}
for state,name in sources.items():
    asset=unreal.load_asset(DEST+'/'+name.replace('A_Mannequin','A_Miner_SingleHand'))
    if not asset:raise RuntimeError('Missing retarget clip: '+state)
    source_seconds=asset.get_play_length()
    # EBS interaction events do not belong to the miner's combat clock.
    unreal.AnimationLibrary.remove_all_animation_notify_tracks(asset)
    compose_single_hand(asset,1.2 if state=='Attack' else 1.0)
    asset.set_preview_skeletal_mesh(target_mesh);lib.save_loaded_asset(asset,False)
    task=unreal.AssetExportTask();task.object=asset;task.filename=str(OUT/f'A_Miner_{state}.fbx')
    task.automated=True;task.prompt=False;task.options=unreal.FbxExportOption()
    task.options.set_editor_property('export_preview_mesh',False)
    task.exporter=unreal.AnimSequenceExporterFBX()
    if not unreal.Exporter.run_asset_export_task(task):raise RuntimeError('FBX export failed: '+state)
    clips[state]=asset
    clip_report[state]={'path':asset.get_path_name(),'seconds':asset.get_play_length(),
                        'source_seconds':source_seconds,'baked_speed':source_seconds/asset.get_play_length()}

speed=clip_report['Attack']['baked_speed']
contact_time=21/30/speed;contact_end=27/30/speed
bp=unreal.load_asset('/Game/Monsters/InfectedMiner/BP_InfectedMiner')
cdo=unreal.get_default_object(bp.generated_class())
for state,asset in clips.items():cdo.set_editor_property(state.lower()+'_clip',asset)
cdo.set_editor_property('contact_time',contact_time);cdo.set_editor_property('contact_end',contact_end)
lib.save_loaded_asset(bp,False)
report={'version':'single-hand composite from EBS PickAxe mining cycle',
        'source_mesh':source_mesh.get_path_name(),'target_mesh':target_mesh.get_path_name(),
        'sources':{state:SOURCE+'/Animations/'+name for state,name in sources.items()},
        'retargeter':retarget.get_path_name(),'clips':clip_report,
        'contact_time':contact_time,'contact_end':contact_end,
        'source_play_rate':speed,'custom_attack_ik':False,
        'composition':'source body/legs/left arm; existing accepted idle right arm; accepted fingers',
        'original_source_is_single_hand':False,
        'source_ebs_notifies_removed':True,'accepted_pose_source':accepted_idle.get_path_name(),
        'mesh_rest_skin_materials_weapon':'accepted assets retained',
        'gameplay_tested':False}
(OUT/'rebuild.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
unreal.log('MINER_PICKAXE_REBUILT '+json.dumps(report))
