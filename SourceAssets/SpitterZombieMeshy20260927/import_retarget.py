"""Background asset production: import Meshy skin and native UE IK retargeting."""
import unreal as u
import json
import os
from pathlib import Path

ROOT=Path(__file__).resolve().parent
DEST='/Game/Monsters/SpitterZombie'
LIB=u.EditorAssetLibrary;TOOLS=u.AssetToolsHelpers.get_asset_tools()
if os.environ.get('SPITTER_HEADLESS') != '1':
    level=u.get_editor_subsystem(u.LevelEditorSubsystem)
    if level and level.is_in_play_in_editor():raise RuntimeError('Asset production requires PIE to be stopped; nothing changed.')
u.SystemLibrary.execute_console_command(None,'Interchange.FeatureFlags.Import.FBX 0')

def save(asset):
    if not LIB.save_loaded_asset(asset,False):raise RuntimeError('Save failed: '+asset.get_path_name())

def create(name,folder,cls,factory):
    return u.load_asset(folder+'/'+name) or TOOLS.create_asset(name,folder,cls,factory)

def imp(file,name,folder,options):
    task=u.AssetImportTask();task.filename=str(file);task.destination_path=folder;task.destination_name=name
    task.options=options;task.automated=True;task.save=True;task.replace_existing=True
    TOOLS.import_asset_tasks([task])
    asset=u.load_asset(folder+'/'+name)
    if not asset:raise RuntimeError('Import failed: '+str(task.imported_object_paths))
    return asset

def mesh(file,name,folder):
    existing=u.load_asset(folder+'/'+name)
    if existing:
        save(existing.skeleton)
        if existing.physics_asset:save(existing.physics_asset)
        return existing
    o=u.FbxImportUI();o.automated_import_should_detect_type=False
    o.mesh_type_to_import=u.FBXImportType.FBXIT_SKELETAL_MESH;o.import_as_skeletal=True
    o.import_mesh=True;o.import_animations=False;o.import_materials=False;o.import_textures=False;o.create_physics_asset=True
    data=o.skeletal_mesh_import_data;data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS
    data.set_editor_property('use_t0_as_ref_pose',False);data.set_editor_property('convert_scene_unit',True)
    result=imp(file,name,folder,o);save(result.skeleton)
    if result.physics_asset:save(result.physics_asset)
    save(result);return result

target=mesh(ROOT/'prepared/SK_SpitterZombie.fbx','SK_SpitterZombie',DEST)
source=mesh(ROOT/'prepared/SK_M2M_Source.fbx','SK_M2M_Source',DEST+'/Sources')
clips=[]
for file in sorted((ROOT/'prepared').glob('A_M2M_*.fbx')):
    o=u.FbxImportUI();o.automated_import_should_detect_type=False
    o.mesh_type_to_import=u.FBXImportType.FBXIT_ANIMATION;o.skeleton=source.skeleton
    o.import_mesh=False;o.import_animations=True;o.import_materials=False;o.import_textures=False
    o.anim_sequence_import_data.set_editor_property('use_default_sample_rate',False)
    o.anim_sequence_import_data.set_editor_property('custom_sample_rate',60)
    o.anim_sequence_import_data.set_editor_property('convert_scene_unit',True)
    clips.append(imp(file,file.stem,DEST+'/Sources',o))

src_chains={'Spine':('spine_01','spine_03'),'Neck':('neck_01','neck_01'),'Head':('head','head'),
    'ClavicleLeft':('clavicle_l','clavicle_l'),'ClavicleRight':('clavicle_r','clavicle_r'),
    'ArmLeft':('upperarm_l','hand_l'),'ArmRight':('upperarm_r','hand_r'),
    'LegLeft':('thigh_l','foot_l'),'LegRight':('thigh_r','foot_r'),
    'ToeLeft':('ball_l','ball_l'),'ToeRight':('ball_r','ball_r')}
dst_chains={'Spine':('Spine02','Spine'),'Neck':('neck','neck'),'Head':('Head','Head'),
    'ClavicleLeft':('LeftShoulder','LeftShoulder'),'ClavicleRight':('RightShoulder','RightShoulder'),
    'ArmLeft':('LeftArm','LeftHand'),'ArmRight':('RightArm','RightHand'),
    'LegLeft':('LeftUpLeg','LeftFoot'),'LegRight':('RightUpLeg','RightFoot'),
    'ToeLeft':('LeftToeBase','LeftToeBase'),'ToeRight':('RightToeBase','RightToeBase')}
def ik(name,skel,pelvis,chains):
    asset=create(name,DEST+'/Rig',u.IKRigDefinition,u.IKRigDefinitionFactory())
    ctl=u.IKRigController.get_controller(asset);ctl.set_skeletal_mesh(skel);ctl.set_retarget_root(pelvis)
    existing={str(c.chain_name) for c in ctl.get_retarget_chains()}
    for chain,(start,end) in chains.items():
        if chain not in existing:ctl.add_retarget_chain(chain,start,end,'')
    save(asset);return asset
src=ik('IK_M2M_Source',source,'pelvis',src_chains)
dst=ik('IK_SpitterZombie',target,'Hips',dst_chains)
rtg=create('RTG_M2M_SpitterZombie',DEST+'/Rig',u.IKRetargeter,u.IKRetargetFactory())
ctl=u.IKRetargeterController.get_controller(rtg)
ctl.set_ik_rig(u.RetargetSourceOrTarget.SOURCE,src);ctl.set_ik_rig(u.RetargetSourceOrTarget.TARGET,dst)
ctl.set_preview_mesh(u.RetargetSourceOrTarget.SOURCE,source);ctl.set_preview_mesh(u.RetargetSourceOrTarget.TARGET,target)
if ctl.get_num_retarget_ops()==0:ctl.add_default_ops()
ctl.auto_map_chains(u.AutoMapChainType.EXACT,True)
pose=ctl.create_retarget_pose('Meshy_Aligned',u.RetargetSourceOrTarget.TARGET)
ctl.set_current_retarget_pose(pose,u.RetargetSourceOrTarget.TARGET);ctl.auto_align_all_bones(u.RetargetSourceOrTarget.TARGET)
save(rtg)
params=u.IKRetargetBatchOperationInputs()
params.assets_to_retarget=[LIB.find_asset_data(a.get_path_name()) for a in clips]
params.source_mesh=source;params.target_mesh=target;params.ik_retarget_asset=rtg
params.search='A_M2M_';params.replace='A_SpitterRaw_';params.target_path=DEST+'/RetargetedRaw'
params.include_referenced_assets=False;params.overwrite_existing_files=True
out=u.IKRetargetBatchOperation.run_batch_retarget(params)
folder=ROOT/'native_retarget';folder.mkdir(exist_ok=True)
report={}
for data in out:
    a=data.get_asset()
    if not isinstance(a,u.AnimSequence):continue
    a.set_preview_skeletal_mesh(target);a.set_editor_property('enable_root_motion',False);save(a)
    task=u.AssetExportTask();task.object=a;task.filename=str(folder/(a.get_name()+'.fbx'))
    task.automated=True;task.prompt=False;task.replace_identical=True
    task.exporter=u.AnimSequenceExporterFBX();opts=u.FbxExportOption();opts.set_editor_property('export_preview_mesh',False);task.options=opts
    if not u.Exporter.run_asset_export_task(task):raise RuntimeError('Export failed: '+a.get_name())
    report[a.get_name()]={'asset':a.get_path_name(),'seconds':a.get_play_length(),'fbx':task.filename}
(ROOT/'native_retarget.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
u.log('SPITTER_NATIVE_RETARGET_SAVED')
