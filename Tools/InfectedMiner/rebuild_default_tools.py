"""Rebuild from untouched EBS source clips with UE's native IK Retargeter.

This creates an editable retarget asset. It does not run PIE or render previews.
"""
import json
from pathlib import Path
import unreal

ROOT=Path(unreal.Paths.project_dir())
OUT=ROOT/'SourceAssets/InfectedMiner20260913/Delivery'
OUT.mkdir(parents=True,exist_ok=True)
DEST='/Game/Monsters/InfectedMiner/EBSDefault20260913'
SOURCE='/Game/EasyBuildingSystem/Mannequin'
ACCEPTED='/Game/Monsters/InfectedMiner/AuthoredChopFinal'
lib=unreal.EditorAssetLibrary
assets=unreal.AssetToolsHelpers.get_asset_tools()
source_mesh=unreal.load_asset(SOURCE+'/Mesh/SK_Mannequin')
target_mesh=unreal.load_asset(ACCEPTED+'/SK_InfectedMiner')
accepted_idle=unreal.load_asset(ACCEPTED+'/A_Miner_Idle')

def create(name,cls,factory):
    return unreal.load_asset(DEST+'/'+name) or assets.create_asset(name,DEST,cls,factory)

rigs=[]
for name,mesh in [('IK_EBS_Default',source_mesh),('IK_Miner_Accepted',target_mesh)]:
    rig=create(name,unreal.IKRigDefinition,unreal.IKRigDefinitionFactory())
    ctl=unreal.IKRigController.get_controller(rig)
    ctl.set_skeletal_mesh(mesh)
    if not ctl.apply_auto_generated_retarget_definition():
        raise RuntimeError('No humanoid retarget template for '+name)
    rigs.append(rig)

retarget=create('RTG_EBS_Default_Miner',unreal.IKRetargeter,unreal.IKRetargetFactory())
ctl=unreal.IKRetargeterController.get_controller(retarget)
src=unreal.RetargetSourceOrTarget.SOURCE
tgt=unreal.RetargetSourceOrTarget.TARGET
ctl.set_ik_rig(src,rigs[0]);ctl.set_ik_rig(tgt,rigs[1])
ctl.set_preview_mesh(src,source_mesh);ctl.set_preview_mesh(tgt,target_mesh)
ctl.remove_all_ops();ctl.add_default_ops()
ctl.auto_map_chains(unreal.AutoMapChainType.EXACT,True)
pose=ctl.get_current_retarget_pose_name(tgt)
ctl.reset_retarget_pose(pose,[],tgt)
ctl.auto_align_all_bones(tgt,unreal.RetargetAutoAlignMethod.CHAIN_TO_CHAIN)
ctl.reset_retarget_pose(pose,['foot_l','foot_r','ball_l','ball_r'],tgt)
ops=[]
for i in range(ctl.get_num_retarget_ops()):
    op=ctl.get_op_controller(i)
    typ=op.get_class().get_name() if op else ''
    # Epic's automatic batch retarget also disables the optional IK solve.
    if 'RunIKRig' in typ:ctl.set_retarget_op_enabled(i,False)
    ops.append({'name':str(ctl.get_op_name(i)),'type':typ,'enabled':ctl.get_retarget_op_enabled(i)})
for asset in rigs+[retarget]:lib.save_loaded_asset(asset,False)

names=['A_Mannequin_Axe_Act','A_Mannequin_Axe_Idle','A_Mannequin_Axe_Walk']
inputs=unreal.IKRetargetBatchOperationInputs()
inputs.assets_to_retarget=[lib.find_asset_data(SOURCE+'/Animations/'+name) for name in names]
inputs.source_mesh=source_mesh;inputs.target_mesh=target_mesh;inputs.ik_retarget_asset=retarget
inputs.target_path=DEST;inputs.search='A_Mannequin';inputs.replace='A_Miner_Default'
inputs.include_referenced_assets=False;inputs.overwrite_existing_files=True
created=unreal.IKRetargetBatchOperation.run_batch_retarget(inputs)
if not created:raise RuntimeError('UE batch retarget produced no assets')

clips={}
for state,suffix in [('Attack','Act'),('Idle','Idle'),('Walk','Walk')]:
    asset=unreal.load_asset(DEST+'/A_Miner_Default_Axe_'+suffix)
    if not asset:raise RuntimeError('Missing retarget output '+state)
    # EBS interaction notifies target EBS characters/tools. The miner uses its
    # existing authoritative combat clock, so do not carry that gameplay over.
    unreal.AnimationLibrary.remove_all_animation_notify_tracks(asset)
    if not unreal.InfectedMiner.apply_accepted_grip(asset,accepted_idle):
        raise RuntimeError('Could not apply accepted finger grip to '+state)
    asset.set_preview_skeletal_mesh(target_mesh)
    lib.save_loaded_asset(asset,False)
    task=unreal.AssetExportTask();task.object=asset;task.filename=str(OUT/f'A_Miner_{state}.fbx')
    task.automated=True;task.prompt=False;task.options=unreal.FbxExportOption()
    task.options.set_editor_property('export_preview_mesh',False)
    task.exporter=unreal.AnimSequenceExporterFBX()
    if not unreal.Exporter.run_asset_export_task(task):raise RuntimeError('FBX export failed '+state)
    clips[state]=asset

bp=unreal.load_asset('/Game/Monsters/InfectedMiner/BP_InfectedMiner')
cdo=unreal.get_default_object(bp.generated_class())
cdo.set_editor_property('visual_mesh',target_mesh)
cdo.mesh.set_skeletal_mesh_asset(target_mesh)
for state,asset in clips.items():cdo.set_editor_property(state.lower()+'_clip',asset)
cdo.set_editor_property('contact_time',11/30)
cdo.set_editor_property('contact_end',17/30)
lib.save_loaded_asset(bp,False)
report={'version':'EBS original axe tool cycle via native UE IK Retargeter',
        'source_mesh':source_mesh.get_path_name(),'target_mesh':target_mesh.get_path_name(),
        'sources':[SOURCE+'/Animations/'+name for name in names],
        'retargeter':retarget.get_path_name(),'ops':ops,
        'clips':{state:{'path':asset.get_path_name(),'seconds':asset.get_play_length()} for state,asset in clips.items()},
        'contact_time':11/30,'contact_end':17/30,'source_play_rate':1,
        'custom_attack_ik':False,'custom_attack_keys':False,
        'source_ebs_notifies_removed':True,
        'accepted_finger_grip':accepted_idle.get_path_name(),
        'weapon_mesh':'existing pickaxe retained; free Fab candidate found, not downloaded',
        'tested':False,'rendered':False}
(OUT/'rebuild.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
unreal.log('MINER_DEFAULT_REBUILT '+json.dumps(report))
