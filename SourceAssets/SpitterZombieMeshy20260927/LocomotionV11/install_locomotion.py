"""Save three independently refined clips; retain Walk_A, attack and native logic."""
import unreal as u,json,ast,shutil,math
from pathlib import Path
ROOT=Path(__file__).resolve().parent;BASE=ROOT.parent;PROJECT=BASE.parents[1]
DEST='/Game/Monsters/SpitterZombie';LIB=u.EditorAssetLibrary;ROLES=['Walk_B','Walk_C','Run_A']
level=u.get_editor_subsystem(u.LevelEditorSubsystem)
if level and level.is_in_play_in_editor():raise RuntimeError('Stop PIE before saving the three locomotion clips')
data=json.loads((ROOT/'authoring.json').read_text(encoding='utf-8'));before=json.loads((ROOT/'bindings_before.json').read_text())
entries=data['movement'];bp_path=DEST+'/BP_SpitterZombie'
targets={bp_path}|{DEST+'/Animations/'+e['asset_name'] for e in entries.values()}
dirty={p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
if dirty&targets:raise RuntimeError('Preserving unsaved edits: '+str(dirty&targets))
bp=u.load_asset(bp_path);cdo=u.get_default_object(bp.generated_class());mesh=cdo.get_editor_property('visual_mesh')
clips=list(cdo.get_editor_property('movement_clips'));speeds=list(cdo.get_editor_property('movement_reference_speeds'))
if [a.get_path_name() if a else None for a in clips]!=before['movements']:
    raise RuntimeError('Movement bindings changed after the scoped read; preserving them')
backup=BASE.parents[1]/'trash/spitter-zombie-rollbacks'/ROOT.name/'Before';backup.mkdir(parents=True,exist_ok=True)
for file in [PROJECT/'Content/Monsters/SpitterZombie/BP_SpitterZombie.uasset',BASE/'animation_contract.json',BASE/'ue_installation.json',BASE/'production_status.json']:
    if file.exists() and not (backup/file.name).exists():shutil.copy2(file,backup/file.name)
# Reuse only the established unit-conversion function, not the V10 installer.
helper=BASE/'LocomotionV10/install_locomotion.py'
tree=ast.parse(helper.read_text(encoding='utf-8'))
function=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='fit_container_units')
exec(compile(ast.Module(body=[function],type_ignores=[]),str(helper),'exec'),globals())
report=dict(revision=data['revision'],saved=[],runtime_tested=False,offline_inspected=True,preview_rendered=True,
    native_changed=False,mesh_changed=False,walk_a=clips[0].get_path_name(),attack=cdo.get_editor_property('attack_clip').get_path_name(),animation_evaluation={})
assets={};cvar='Interchange.FeatureFlags.Import.FBX';previous=u.SystemLibrary.get_console_variable_int_value(cvar)
u.SystemLibrary.execute_console_command(None,cvar+' 0')
try:
    for role in ROLES:
        e=entries[role];options=u.FbxImportUI();options.automated_import_should_detect_type=False
        options.mesh_type_to_import=u.FBXImportType.FBXIT_ANIMATION;options.import_as_skeletal=True
        options.import_mesh=False;options.import_animations=True;options.import_materials=False;options.import_textures=False
        options.skeleton=mesh.skeleton;imp=options.anim_sequence_import_data
        imp.set_editor_property('use_default_sample_rate',False);imp.set_editor_property('custom_sample_rate',e['fps'])
        imp.set_editor_property('convert_scene_unit',True);imp.set_editor_property('remove_redundant_keys',False)
        imp.set_editor_property('animation_length',u.FBXAnimationLengthImportType.FBXALIT_EXPORTED_TIME)
        task=u.AssetImportTask();task.filename=e['file'];task.destination_name=e['asset_name'];task.destination_path=DEST+'/Animations'
        task.automated=True;task.save=False;task.replace_existing=True;task.replace_existing_settings=True;task.options=options
        u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
        clip=u.load_asset(DEST+'/Animations/'+e['asset_name'])
        if clip is None:raise RuntimeError('No imported animation: '+role)
        fit_container_units(clip);clip.set_preview_skeletal_mesh(mesh)
        clip.set_editor_property('loop',True);clip.set_editor_property('enable_root_motion',False);clip.set_editor_property('force_root_lock',True)
        LIB.set_metadata_tag(clip,'Spitter.Revision',data['revision']);LIB.set_metadata_tag(clip,'Source',e['source'])
        LIB.set_metadata_tag(clip,'Spitter.ReferenceSpeedCmS',str(e['reference_speed_cm_s']))
        if not LIB.save_loaded_asset(clip,False):raise RuntimeError('Failed to save '+role)
        assets[role]=clip;report['saved'].append(clip.get_path_name())
        # Targeted imported-animation check requested by the user; no actor/PIE.
        samples={}
        for label,mode in [('source',u.AnimDataEvalType.SOURCE),('compressed',u.AnimDataEvalType.COMPRESSED)]:
            opt=u.AnimPoseEvaluationOptions();opt.set_editor_property('evaluation_type',mode);opt.set_editor_property('optional_skeletal_mesh',mesh)
            samples[label]=[]
            for i in range(17):
                pose=u.AnimPoseExtensions.get_anim_pose_at_time(clip,clip.get_play_length()*i/16,opt)
                frame={}
                for name in ['SpitterRoot','Hips','Head','LeftForeArm','RightForeArm','LeftLeg','RightLeg','LeftFoot','RightFoot']:
                    local=u.AnimPoseExtensions.get_bone_pose(pose,name,u.AnimPoseSpaces.LOCAL)
                    world=u.AnimPoseExtensions.get_bone_pose(pose,name,u.AnimPoseSpaces.WORLD)
                    frame[name]=dict(q=[local.rotation.x,local.rotation.y,local.rotation.z,local.rotation.w],
                        p=[world.translation.x,world.translation.y,world.translation.z],scale=[local.scale3d.x,local.scale3d.y,local.scale3d.z])
                samples[label].append(frame)
        errors=[]
        for a,b in zip(samples['source'],samples['compressed']):
            for name in a:errors.append(math.dist(a[name]['p'],b[name]['p']))
        report['animation_evaluation'][role]=dict(seconds=clip.get_play_length(),max_compression_position_error_cm=max(errors),
            container_scale=samples['compressed'][0]['SpitterRoot']['scale'],samples=samples)
finally:u.SystemLibrary.execute_console_command(None,cvar+' '+str(previous))

for index,role in enumerate(ROLES,1):clips[index]=assets[role];speeds[index]=entries[role]['reference_speed_cm_s']
cdo.set_editor_property('movement_clips',clips);cdo.set_editor_property('movement_reference_speeds',speeds)
LIB.set_metadata_tag(bp,'Spitter.MovementRevision','V10_Walk_A_and_V11_other_styles')
if not LIB.save_loaded_asset(bp,False):raise RuntimeError('Failed to save blueprint movement bindings')
report['saved'].append(bp.get_path_name());report.update(state='three_clips_imported_evaluated_and_saved_with_blueprint',
    movement_clips=[a.get_path_name() for a in clips],movement_reference_speeds_cm_s=speeds)
(ROOT/'installation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
contract=json.loads((BASE/'animation_contract.json').read_text(encoding='utf-8'))
contract['MovementVariants']['variants'].update(entries)
(BASE/'animation_contract.json').write_text(json.dumps(contract,ensure_ascii=False,indent=2),encoding='utf-8')
delivery=json.loads((BASE/'ue_installation.json').read_text(encoding='utf-8'))
delivery.update(movement_variants=report['movement_clips'],movement_reference_speeds_cm_s=speeds,movement_revision='V10_Walk_A_and_V11_other_styles')
delivery['saved']=list(dict.fromkeys(delivery['saved']+report['saved']))
(BASE/'ue_installation.json').write_text(json.dumps(delivery,ensure_ascii=False,indent=2),encoding='utf-8')
status=json.loads((BASE/'production_status.json').read_text(encoding='utf-8'))
status.update(movement_revision=delivery['movement_revision'],movement_delivery_scope='v11_b_c_run_saved_walk_a_retained',
    movement_offline_checked=True,movement_runtime_tested=False,tested=False)
(BASE/'production_status.json').write_text(json.dumps(status,ensure_ascii=False,indent=2),encoding='utf-8')
u.log('SPITTER_V11_INSTALLED '+json.dumps({k:v for k,v in report.items() if k!='animation_evaluation'}))
