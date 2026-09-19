"""Retarget the existing Godot runner in the isolated Mutant3 authoring project."""
import unreal as u, json
from pathlib import Path
ROOT=Path(__file__).parent
DEST='/Game/Monsters/Mutant3Meshy'
at=u.AssetToolsHelpers.get_asset_tools(); lib=u.EditorAssetLibrary
u.SystemLibrary.execute_console_command(None,'Interchange.FeatureFlags.Import.FBX 0')
def save(a): lib.save_loaded_asset(a,False)
def create(name,folder,cls,factory):
    return u.load_asset(folder+'/'+name) or at.create_asset(name,folder,cls,factory)
def imp(file,name,folder,options):
    task=u.AssetImportTask(); task.filename=str(file); task.destination_name=name
    task.destination_path=folder; task.options=options
    task.automated=True; task.save=True; task.replace_existing=True
    at.import_asset_tasks([task]); asset=u.load_asset(folder+'/'+name)
    if not asset: raise RuntimeError('Asset import failed: '+name)
    return asset
target=u.load_asset(DEST+'/SK_Mutant3_Meshy')
o=u.FbxImportUI(); o.automated_import_should_detect_type=False
o.mesh_type_to_import=u.FBXImportType.FBXIT_SKELETAL_MESH
o.import_as_skeletal=True; o.import_mesh=True; o.import_animations=False
o.import_materials=False; o.import_textures=False; o.create_physics_asset=False
o.skeletal_mesh_import_data.set_editor_property('use_t0_as_ref_pose',False)
o.skeletal_mesh_import_data.set_editor_property('convert_scene_unit',True)
source=imp(ROOT/'prepared/SK_GodotRunner.fbx','SK_GodotRunner',DEST+'/Sources/GodotRunner',o)
save(source.skeleton)
o=u.FbxImportUI(); o.automated_import_should_detect_type=False
o.mesh_type_to_import=u.FBXImportType.FBXIT_ANIMATION; o.skeleton=source.skeleton
o.import_mesh=False; o.import_animations=True; o.import_materials=False; o.import_textures=False
o.anim_sequence_import_data.set_editor_property('use_default_sample_rate',False)
o.anim_sequence_import_data.set_editor_property('custom_sample_rate',120)
o.anim_sequence_import_data.set_editor_property('convert_scene_unit',True)
clip=imp(ROOT/'prepared/A_GodotRunner_Run.fbx','A_GodotRunner_Run',DEST+'/Sources/GodotRunner',o)
chains={'Spine':('bip_Spine','bip_Spine1'),'Neck':('bip_Neck','bip_Neck'),'Head':('head','head'),
        'ClavicleLeft':('bip_L_Clavicle','bip_L_Clavicle'),'ClavicleRight':('bip_R_Clavicle','bip_R_Clavicle'),
        'ArmLeft':('bip_L_UpperArm','bip_L_Hand'),'ArmRight':('bip_R_UpperArm','bip_R_Hand'),
        'LegLeft':('bip_L_Thigh','bip_L_Foot'),'LegRight':('bip_R_Thigh','bip_R_Foot'),
        'ToeLeft':('bip_L_Toe0','bip_L_Toe0'),'ToeRight':('bip_R_Toe0','bip_R_Toe0')}
src=create('IK_GodotRunner',DEST+'/Rig',u.IKRigDefinition,u.IKRigDefinitionFactory())
ctl=u.IKRigController.get_controller(src); ctl.set_skeletal_mesh(source); ctl.set_retarget_root('bip_Pelvis')
existing={str(c.chain_name) for c in ctl.get_retarget_chains()}
for name,(start,end) in chains.items():
    if name not in existing: ctl.add_retarget_chain(name,start,end,'')
save(src)
dst=u.load_asset(DEST+'/Rig/IK_Mutant3_Meshy')
rtg=create('RTG_GodotRunner_Mutant3',DEST+'/Rig',u.IKRetargeter,u.IKRetargetFactory())
ctl=u.IKRetargeterController.get_controller(rtg)
ctl.set_ik_rig(u.RetargetSourceOrTarget.SOURCE,src); ctl.set_ik_rig(u.RetargetSourceOrTarget.TARGET,dst)
ctl.set_preview_mesh(u.RetargetSourceOrTarget.SOURCE,source); ctl.set_preview_mesh(u.RetargetSourceOrTarget.TARGET,target)
if ctl.get_num_retarget_ops()==0: ctl.add_default_ops()
ctl.auto_map_chains(u.AutoMapChainType.EXACT,True)
pose=ctl.create_retarget_pose('GodotRunner_Aligned',u.RetargetSourceOrTarget.TARGET)
ctl.set_current_retarget_pose(pose,u.RetargetSourceOrTarget.TARGET)
ctl.auto_align_all_bones(u.RetargetSourceOrTarget.TARGET); save(rtg)
params=u.IKRetargetBatchOperationInputs()
params.assets_to_retarget=[lib.find_asset_data(clip.get_path_name())]
params.source_mesh=source; params.target_mesh=target; params.ik_retarget_asset=rtg
params.search='A_GodotRunner_'; params.replace='A_Mutant3_GodotRaw_'; params.target_path=DEST+'/RetargetedRaw/GodotRunner'
params.include_referenced_assets=False; params.overwrite_existing_files=True
outputs=u.IKRetargetBatchOperation.run_batch_retarget(params)
(ROOT/'native_retarget').mkdir(exist_ok=True); report={}
for data in outputs:
    anim=data.get_asset()
    if not isinstance(anim,u.AnimSequence): continue
    anim.set_preview_skeletal_mesh(target); anim.set_editor_property('enable_root_motion',False); save(anim)
    task=u.AssetExportTask(); task.object=anim; task.filename=str(ROOT/'native_retarget'/(anim.get_name()+'.fbx'))
    task.automated=True; task.prompt=False; task.replace_identical=True; task.exporter=u.AnimSequenceExporterFBX()
    opt=u.FbxExportOption(); opt.set_editor_property('export_preview_mesh',False); task.options=opt
    if not u.Exporter.run_asset_export_task(task): raise RuntimeError('FBX export failed: '+anim.get_name())
    report[anim.get_name()]={'asset':anim.get_path_name(),'seconds':anim.get_play_length()}
if not report: raise RuntimeError('No animation was retargeted')
(ROOT/'native_retarget.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
u.log('GODOT_RUNNER_RETARGETED '+json.dumps(report))
