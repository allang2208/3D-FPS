"""Import four V10 clips and bind only locomotion on the existing zombie BP."""
import unreal as u
import json,os,shutil
from pathlib import Path
ROOT=Path(__file__).resolve().parent;BASE=ROOT.parent;PROJECT=BASE.parents[1]
DEST='/Game/Monsters/SpitterZombie';LIB=u.EditorAssetLibrary
ROLES=['Walk_A','Walk_B','Walk_C','Run_A']
if os.environ.get('SPITTER_HEADLESS')!='1':
    level=u.get_editor_subsystem(u.LevelEditorSubsystem)
    if level and level.is_in_play_in_editor():raise RuntimeError('Stop PIE before installing locomotion')
data=json.loads((ROOT/'authoring.json').read_text(encoding='utf-8'));entries=data['movement']
paths={DEST+'/BP_SpitterZombie'}|{DEST+'/Animations/'+e['asset_name'] for e in entries.values()}
dirty={p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
if paths&dirty:raise RuntimeError('Preserving unsaved target edits: '+str(paths&dirty))
bp=u.load_asset(DEST+'/BP_SpitterZombie')
if bp is None:raise RuntimeError('Existing zombie blueprint missing')
cdo=u.get_default_object(bp.generated_class());mesh=cdo.get_editor_property('visual_mesh')
# Runtime selection is private native state; import only needs the public
# movement bindings. Native delivery is recorded by the ordinary build below.
build=json.loads((ROOT/'build-result.json').read_text(encoding='utf-8-sig'))
if build['exit_code']!=0:raise RuntimeError('V10 native build is not complete')
backup=BASE.parents[1]/'trash/spitter-zombie-rollbacks'/ROOT.name/'Before';backup.mkdir(parents=True,exist_ok=True)
for file in [PROJECT/'Content/Monsters/SpitterZombie/BP_SpitterZombie.uasset',
             BASE/'animation_contract.json',BASE/'ue_installation.json',BASE/'production_status.json']:
    if file.exists() and not (backup/file.name).exists():shutil.copy2(file,backup/file.name)
report=dict(revision=data['revision'],runtime_tested=False,preview_rendered=False,saved=[],
    previous_attack=cdo.get_editor_property('attack_clip').get_path_name(),
    previous_movement=[a.get_path_name() if a else None for a in cdo.get_editor_property('movement_clips')],
    mesh_modified=False,attack_modified=False,source_build=build)

def fit_container_units(clip):
    options=u.AnimPoseEvaluationOptions();options.set_editor_property('evaluation_type',u.AnimDataEvalType.SOURCE)
    options.set_editor_property('optional_skeletal_mesh',mesh)
    pose=u.AnimPoseExtensions.get_anim_pose_at_time(clip,0.,options)
    expected=u.AnimPoseExtensions.get_ref_bone_pose(pose,'SpitterRoot',u.AnimPoseSpaces.LOCAL).scale3d
    scale=u.AnimPoseExtensions.get_bone_pose(pose,'SpitterRoot',u.AnimPoseSpaces.LOCAL).scale3d
    ratios=[a/b for a,b in zip((expected.x,expected.y,expected.z),(scale.x,scale.y,scale.z))]
    if max(abs(v-1) for v in ratios)<1e-5:return
    if max(abs(v-100) for v in ratios)>.01:raise RuntimeError('Unsupported FBX container units: '+str(ratios))
    count=clip.get_editor_property('data_model_interface').get_number_of_keys()
    positions=[];rotations=[];scales=[]
    for i in range(count):
        pose=u.AnimPoseExtensions.get_anim_pose_at_time(clip,clip.get_play_length()*i/max(1,count-1),options)
        transform=u.AnimPoseExtensions.get_bone_pose(pose,'SpitterRoot',u.AnimPoseSpaces.LOCAL)
        positions.append(transform.translation);rotations.append(transform.rotation);scales.append(expected)
    controller=clip.get_editor_property('controller');controller.open_bracket('Adapt Meshy FBX container units',False)
    try:
        if not controller.set_bone_track_keys('SpitterRoot',positions,rotations,scales,False):raise RuntimeError('Container conversion failed')
    finally:controller.close_bracket(False)

assets={};cvar='Interchange.FeatureFlags.Import.FBX';previous=u.SystemLibrary.get_console_variable_int_value(cvar)
u.SystemLibrary.execute_console_command(None,cvar+' 0')
try:
    for role in ROLES:
        entry=entries[role]
        options=u.FbxImportUI();options.automated_import_should_detect_type=False
        options.mesh_type_to_import=u.FBXImportType.FBXIT_ANIMATION;options.import_as_skeletal=True
        options.import_mesh=False;options.import_animations=True;options.import_materials=False;options.import_textures=False
        options.skeleton=mesh.skeleton;imp=options.anim_sequence_import_data
        imp.set_editor_property('use_default_sample_rate',False);imp.set_editor_property('custom_sample_rate',entry['fps'])
        imp.set_editor_property('convert_scene_unit',True);imp.set_editor_property('remove_redundant_keys',False)
        imp.set_editor_property('animation_length',u.FBXAnimationLengthImportType.FBXALIT_EXPORTED_TIME)
        task=u.AssetImportTask();task.filename=entry['file'];task.destination_name=entry['asset_name']
        task.destination_path=DEST+'/Animations';task.automated=True;task.save=False
        task.replace_existing=True;task.replace_existing_settings=True;task.options=options
        u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
        clip=u.load_asset(DEST+'/Animations/'+entry['asset_name'])
        if clip is None:raise RuntimeError('Animation import failed: '+role)
        fit_container_units(clip)
        clip.set_preview_skeletal_mesh(mesh);clip.set_editor_property('loop',True)
        clip.set_editor_property('enable_root_motion',False);clip.set_editor_property('force_root_lock',True)
        LIB.set_metadata_tag(clip,'Spitter.Revision',data['revision']);LIB.set_metadata_tag(clip,'Source',entry['source'])
        LIB.set_metadata_tag(clip,'Spitter.ReferenceSpeedCmS',str(entry['reference_speed_cm_s']))
        if not LIB.save_loaded_asset(clip,False):raise RuntimeError('Animation save failed: '+role)
        assets[role]=clip;report['saved'].append(clip.get_path_name())
finally:u.SystemLibrary.execute_console_command(None,cvar+' '+str(previous))

speeds=[entries[r]['reference_speed_cm_s'] for r in ROLES]
cdo.set_editor_property('movement_clips',[assets[r] for r in ROLES])
cdo.set_editor_property('movement_reference_speeds',speeds)
cdo.set_editor_property('walk_clip',assets['Walk_A']);cdo.set_editor_property('walk_speed',speeds[0])
LIB.set_metadata_tag(bp,'Spitter.MovementRevision',data['revision'])
LIB.set_metadata_tag(bp,'Spitter.MovementSpeedPolicy','clip_and_stride_speed_fixed_once_per_spawn')
if not LIB.save_loaded_asset(bp,False):raise RuntimeError('Zombie blueprint save failed')
report['saved'].append(bp.get_path_name())
report.update(state='four_locomotion_assets_and_blueprint_saved',blueprint=bp.get_path_name(),
    animations={r:a.get_path_name() for r,a in assets.items()},movement_order=ROLES,
    movement_reference_speeds_cm_s=speeds,movement_selection='shuffled_world_class_round_once_per_spawn_lifetime_fixed',
    movement_speed_policy='selected_reference_speed_sets_actor_walk_speed_before_super_beginplay',
    attack=cdo.get_editor_property('attack_clip').get_path_name())
(ROOT/'installation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')

contract=json.loads((BASE/'animation_contract.json').read_text(encoding='utf-8'))
contract['Walk']=entries['Walk_A']
contract['MovementVariants']=dict(selection=report['movement_selection'],speed_policy=report['movement_speed_policy'],variants=entries)
(BASE/'animation_contract.json').write_text(json.dumps(contract,ensure_ascii=False,indent=2),encoding='utf-8')
delivery=json.loads((BASE/'ue_installation.json').read_text(encoding='utf-8'))
delivery['animations']['Walk']=assets['Walk_A'].get_path_name()
delivery.update(movement_variants=[assets[r].get_path_name() for r in ROLES],movement_revision=data['revision'],
    movement_reference_speeds_cm_s=speeds,movement_selection=report['movement_selection'],movement_speed_policy=report['movement_speed_policy'],
    native_attack_build='succeeded_including_spawn_fixed_movement_and_style_speed')
delivery['saved']=list(dict.fromkeys(delivery['saved']+report['saved']))
(BASE/'ue_installation.json').write_text(json.dumps(delivery,ensure_ascii=False,indent=2),encoding='utf-8')
status=json.loads((BASE/'production_status.json').read_text(encoding='utf-8'))
status.update(stage='ue_assets_saved',movement_revision=data['revision'],tested=False,
    movement_selection=report['movement_selection'],movement_speed_policy=report['movement_speed_policy'],
    movement_selection_build='succeeded_including_spawn_fixed_movement_and_style_speed',
    native_attack_build=delivery['native_attack_build'],editor_build='Succeeded',editor_build_log=build['log'],
    movement_delivery_scope='native_built_four_clips_and_blueprint_saved')
for key in ['pending_revision','pending_source_stage','pending_native_change','pending_delivery']:status.pop(key,None)
(BASE/'production_status.json').write_text(json.dumps(status,ensure_ascii=False,indent=2),encoding='utf-8')
u.log('SPITTER_LOCOMOTION_V10_INSTALLED '+json.dumps(report,ensure_ascii=False))
