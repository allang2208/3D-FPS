"""Produce six native UE retargets; never modify the animation-pack source assets."""
import unreal as u
import json, os
from pathlib import Path

ROOT=Path(__file__).resolve().parent
DEST='/Game/Monsters/SpitterZombie'
LIB=u.EditorAssetLibrary;TOOLS=u.AssetToolsHelpers.get_asset_tools()
if os.environ.get('SPITTER_HEADLESS')!='1':
    level=u.get_editor_subsystem(u.LevelEditorSubsystem)
    if level and level.is_in_play_in_editor():raise RuntimeError('Stop PIE before asset production')
source=u.load_asset('/Game/ZombieAnimationPack/Demo/EpicContent/Mannequin_UE5/Meshes/SK_Manny_Simple')
target=u.load_asset(DEST+'/SK_SpitterZombie')
if not source or not target:raise RuntimeError('Required source or target mesh missing')
roles=['Walk_A','Walk_B','Walk_C','Run_A','Attack_A','Attack_D']
clips=[u.load_asset('/Game/ZombieAnimationPack/Animations/Mannequin_UE5/anim_'+n) for n in roles]
if not all(clips):raise RuntimeError('Required source clip missing')
def save(a):
    if not LIB.save_loaded_asset(a,False):raise RuntimeError('Could not save '+a.get_path_name())
def create(name,cls,factory):
    path=DEST+'/Rig/LibraryV7'
    return u.load_asset(path+'/'+name) or TOOLS.create_asset(name,path,cls,factory)
src_chains={'Spine':('spine_01','spine_05'),'Neck':('neck_01','neck_02'),'Head':('head','head'),
 'ClavicleLeft':('clavicle_l','clavicle_l'),'ClavicleRight':('clavicle_r','clavicle_r'),
 'ArmLeft':('upperarm_l','hand_l'),'ArmRight':('upperarm_r','hand_r'),
 'LegLeft':('thigh_l','foot_l'),'LegRight':('thigh_r','foot_r'),
 'ToeLeft':('ball_l','ball_l'),'ToeRight':('ball_r','ball_r')}
dst_chains={'Spine':('Spine02','Spine'),'Neck':('neck','neck'),'Head':('Head','Head'),
 'ClavicleLeft':('LeftShoulder','LeftShoulder'),'ClavicleRight':('RightShoulder','RightShoulder'),
 'ArmLeft':('LeftArm','LeftHand'),'ArmRight':('RightArm','RightHand'),
 'LegLeft':('LeftUpLeg','LeftFoot'),'LegRight':('RightUpLeg','RightFoot'),
 'ToeLeft':('LeftToeBase','LeftToeBase'),'ToeRight':('RightToeBase','RightToeBase')}
def ik(name,mesh,pelvis,chains):
    a=create(name,u.IKRigDefinition,u.IKRigDefinitionFactory())
    c=u.IKRigController.get_controller(a);c.set_skeletal_mesh(mesh);c.set_retarget_root(pelvis)
    existing={str(ch.chain_name) for ch in c.get_retarget_chains()}
    for chain,(start,end) in chains.items():
        if chain not in existing:c.add_retarget_chain(chain,start,end,'')
    save(a);return a
src=ik('IK_ZombiePackSource',source,'pelvis',src_chains)
dst=ik('IK_SpitterLibraryV7',target,'Hips',dst_chains)
rtg=create('RTG_ZombiePack_SpitterV7',u.IKRetargeter,u.IKRetargetFactory())
c=u.IKRetargeterController.get_controller(rtg)
c.set_ik_rig(u.RetargetSourceOrTarget.SOURCE,src);c.set_ik_rig(u.RetargetSourceOrTarget.TARGET,dst)
c.set_preview_mesh(u.RetargetSourceOrTarget.SOURCE,source);c.set_preview_mesh(u.RetargetSourceOrTarget.TARGET,target)
if c.get_num_retarget_ops()==0:c.add_default_ops()
c.auto_map_chains(u.AutoMapChainType.EXACT,True)
pose=c.create_retarget_pose('Meshy_Aligned',u.RetargetSourceOrTarget.TARGET)
c.set_current_retarget_pose(pose,u.RetargetSourceOrTarget.TARGET)
c.auto_align_all_bones(u.RetargetSourceOrTarget.TARGET);save(rtg)
p=u.IKRetargetBatchOperationInputs()
p.assets_to_retarget=[LIB.find_asset_data(a.get_path_name()) for a in clips]
p.source_mesh=source;p.target_mesh=target;p.ik_retarget_asset=rtg
p.search='anim_';p.replace='A_SpitterLibraryRaw_';p.target_path=DEST+'/RetargetedRaw/LibraryV7'
p.include_referenced_assets=False;p.overwrite_existing_files=True
results=u.IKRetargetBatchOperation.run_batch_retarget(p)
folder=ROOT/'Native';folder.mkdir(exist_ok=True);report={}
for data in results:
    a=data.get_asset()
    if not isinstance(a,u.AnimSequence):continue
    a.set_preview_skeletal_mesh(target);a.set_editor_property('enable_root_motion',False);save(a)
    task=u.AssetExportTask();task.object=a;task.filename=str(folder/(a.get_name()+'.fbx'))
    task.automated=True;task.prompt=False;task.replace_identical=True;task.exporter=u.AnimSequenceExporterFBX()
    options=u.FbxExportOption();options.set_editor_property('export_preview_mesh',False);task.options=options
    if not u.Exporter.run_asset_export_task(task):raise RuntimeError('Export failed: '+a.get_name())
    role=a.get_name().replace('A_SpitterLibraryRaw_','')
    report[role]={'asset':a.get_path_name(),'seconds':a.get_play_length(),'fbx':task.filename,
                  'source':'/Game/ZombieAnimationPack/Animations/Mannequin_UE5/anim_'+role}
if set(report)!=set(roles):raise RuntimeError('Retarget batch incomplete: '+str(list(report)))
(ROOT/'native.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
u.log('SPITTER_LIBRARY_V7_RETARGETED '+str(len(report)))
