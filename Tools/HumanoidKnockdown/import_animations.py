"""Import recovery sources and bake each current humanoid skeleton; no gameplay runs."""
import unreal as u, json
from pathlib import Path

ROOT = Path('D:/FPS3D/FPSGAME/SourceAssets/HumanoidKnockdown20260926')
DEST = '/Game/Monsters/HumanoidKnockdown'
lib = u.EditorAssetLibrary
at = u.AssetToolsHelpers.get_asset_tools()
source = u.load_asset('/Game/Monsters/FatZombieMeshy/Sources/SK_M2M_Source')
if source is None: raise RuntimeError('Missing licensed M2M source skeleton')
u.SystemLibrary.execute_console_command(None, 'Interchange.FeatureFlags.Import.FBX 0')

def save(asset):
    if not lib.save_loaded_asset(asset, False): raise RuntimeError('Save failed ' + asset.get_path_name())

def create(name, folder, cls, factory):
    return u.load_asset(folder+'/'+name) or at.create_asset(name,folder,cls,factory)

clips=[]
for role in ['Hit_Knockback','LayToIdle']:
    name='A_M2M_'+role
    opts=u.FbxImportUI()
    opts.automated_import_should_detect_type=False
    opts.mesh_type_to_import=u.FBXImportType.FBXIT_ANIMATION
    opts.skeleton=source.skeleton
    opts.import_mesh=False;opts.import_animations=True
    opts.import_materials=False;opts.import_textures=False
    opts.anim_sequence_import_data.set_editor_property('use_default_sample_rate',False)
    opts.anim_sequence_import_data.set_editor_property('custom_sample_rate',60)
    opts.anim_sequence_import_data.set_editor_property('convert_scene_unit',True)
    task=u.AssetImportTask();task.filename=str(ROOT/(name+'.fbx'))
    task.destination_path=DEST+'/Sources';task.destination_name=name
    task.options=opts;task.automated=True;task.save=True;task.replace_existing=True
    at.import_asset_tasks([task])
    clip=u.load_asset(DEST+'/Sources/'+name)
    if not clip: raise RuntimeError('Source import failed '+name)
    save(clip); clips.append(clip)

bp=u.load_class(None,'/Game/Monsters/NurseZombie/BP_NurseZombie.BP_NurseZombie_C')
nurse=u.get_default_object(bp).get_editor_property('visual_mesh')
targets={
 'Nurse':nurse,
 'FatZombie':u.load_asset('/Game/Monsters/FatZombieMeshy/SK_FatZombie_Meshy'),
 'Mutant3':u.load_asset('/Game/Monsters/Mutant3Meshy/KhaimeraV2/SK_Mutant3_Claw'),
 'Witch':u.load_asset('/Game/Monsters/WitchRebuilt/SK_WitchRebuilt')}
standard={'Spine':('spine_01','spine_03'),'Neck':('neck_01','neck_01'),'Head':('head','head'),
 'ClavicleLeft':('clavicle_l','clavicle_l'),'ClavicleRight':('clavicle_r','clavicle_r'),
 'ArmLeft':('upperarm_l','hand_l'),'ArmRight':('upperarm_r','hand_r'),
 'LegLeft':('thigh_l','foot_l'),'LegRight':('thigh_r','foot_r'),
 'ToeLeft':('ball_l','ball_l'),'ToeRight':('ball_r','ball_r')}
meshy={'Spine':('Spine02','Spine'),'Neck':('neck','neck'),'Head':('Head','Head'),
 'ClavicleLeft':('LeftShoulder','LeftShoulder'),'ClavicleRight':('RightShoulder','RightShoulder'),
 'ArmLeft':('LeftArm','LeftHand'),'ArmRight':('RightArm','RightHand'),
 'LegLeft':('LeftUpLeg','LeftFoot'),'LegRight':('RightUpLeg','RightFoot'),
 'ToeLeft':('LeftToeBase','LeftToeBase'),'ToeRight':('RightToeBase','RightToeBase')}

def rig(name,mesh,pelvis,chains):
    asset=create('IK_'+name,DEST+'/Rig',u.IKRigDefinition,u.IKRigDefinitionFactory())
    ctl=u.IKRigController.get_controller(asset);ctl.set_skeletal_mesh(mesh);ctl.set_retarget_root(pelvis)
    existing={str(c.chain_name) for c in ctl.get_retarget_chains()}
    for chain,(first,last) in chains.items():
        if chain not in existing:ctl.add_retarget_chain(chain,first,last,'')
    save(asset);return asset

src=rig('M2M',source,'pelvis',standard)
report={}
for role,target in targets.items():
    if target is None:raise RuntimeError('Missing target '+role)
    chain=dict(meshy if role in ['FatZombie','Mutant3'] else standard)
    if role=='Witch':chain['Spine']=('spine_01','spine_05')
    dst=rig(role,target,'Hips' if role in ['FatZombie','Mutant3'] else 'pelvis',chain)
    rtg=create('RTG_M2M_'+role,DEST+'/Rig',u.IKRetargeter,u.IKRetargetFactory())
    ctl=u.IKRetargeterController.get_controller(rtg)
    ctl.set_ik_rig(u.RetargetSourceOrTarget.SOURCE,src)
    ctl.set_ik_rig(u.RetargetSourceOrTarget.TARGET,dst)
    ctl.set_preview_mesh(u.RetargetSourceOrTarget.SOURCE,source)
    ctl.set_preview_mesh(u.RetargetSourceOrTarget.TARGET,target)
    if ctl.get_num_retarget_ops()==0:ctl.add_default_ops()
    ctl.auto_map_chains(u.AutoMapChainType.EXACT,True)
    pose=ctl.create_retarget_pose('RecoveryAligned',u.RetargetSourceOrTarget.TARGET)
    ctl.set_current_retarget_pose(pose,u.RetargetSourceOrTarget.TARGET)
    ctl.auto_align_all_bones(u.RetargetSourceOrTarget.TARGET)
    save(rtg)
    p=u.IKRetargetBatchOperationInputs()
    p.assets_to_retarget=[lib.find_asset_data(a.get_path_name()) for a in clips]
    p.source_mesh=source;p.target_mesh=target;p.ik_retarget_asset=rtg
    p.search='A_M2M_';p.replace='A_'+role+'_';p.target_path=DEST+'/'+role
    p.include_referenced_assets=False;p.overwrite_existing_files=True
    out=u.IKRetargetBatchOperation.run_batch_retarget(p)
    saved=[]
    for data in out:
        a=data.get_asset()
        if isinstance(a,u.AnimSequence):
            a.set_preview_skeletal_mesh(target);a.set_editor_property('enable_root_motion',False)
            save(a);saved.append({'asset':a.get_path_name(),'seconds':a.get_play_length()})
    if len(saved)!=2:raise RuntimeError('Incomplete retarget '+role)
    report[role]={'mesh':target.get_path_name(),'skeleton':target.skeleton.get_path_name(),'clips':saved}
    (ROOT/'imported_animations.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('HUMANOID_RECOVERY_SAVED '+json.dumps(report))
