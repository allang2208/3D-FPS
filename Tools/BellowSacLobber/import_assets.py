"""Save the real rig, PBR, animation set and staged monster Blueprint in UE."""
import json
from pathlib import Path
import unreal as u

ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/BellowSacLobberMeshy20261012')
DEST='/Game/Monsters/BellowSacLobber'
VERSION=DEST+'/V01'
LIB=u.EditorAssetLibrary
AT=u.AssetToolsHelpers.get_asset_tools()
ME=u.MaterialEditingLibrary
manifest=json.loads((ROOT/'Records/locomotion_manifest_v01.json').read_text(encoding='utf-8'))
REPORT=ROOT/'Records/ue_import_v01.json'
report=json.loads(REPORT.read_text(encoding='utf-8')) if REPORT.exists() else {'saved':[],'stages':[],'runtime_tested':False}
stage=globals().get('BELLOW_STAGE','mesh')
if not globals().get('BELLOW_COMMANDLET',False) and u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world():
    raise RuntimeError('PIE is active; finish the current game before asset integration')
if any(p.get_path_name().startswith(DEST) for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()):
    raise RuntimeError('BellowSacLobber target packages have unsaved changes')

def save(asset):
    if not LIB.save_loaded_asset(asset,False):
        raise RuntimeError('Save failed: '+asset.get_path_name())
    if asset.get_path_name() not in report['saved']:
        report['saved'].append(asset.get_path_name())
    REPORT.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')

def create(name,folder,cls,factory):
    path=folder+'/'+name
    return u.load_asset(path) if LIB.does_asset_exist(path) else AT.create_asset(name,folder,cls,factory)

def import_file(path,name,folder,options=None,factory=None):
    if LIB.does_asset_exist(folder+'/'+name):
        return u.load_asset(folder+'/'+name)
    task=u.AssetImportTask()
    task.filename=str(path);task.destination_path=folder;task.destination_name=name
    task.automated=True;task.save=False;task.replace_existing=False
    if options:task.options=options
    if factory:task.factory=factory
    AT.import_asset_tasks([task])
    asset=u.load_asset(folder+'/'+name)
    if not asset:raise RuntimeError('Import missing: '+folder+'/'+name)
    return asset

def fbx(animation=False,skeleton=None):
    options=u.FbxImportUI()
    options.automated_import_should_detect_type=False
    options.mesh_type_to_import=u.FBXImportType.FBXIT_ANIMATION if animation else u.FBXImportType.FBXIT_SKELETAL_MESH
    options.import_as_skeletal=True;options.import_mesh=not animation;options.import_animations=animation
    options.import_materials=False;options.import_textures=False
    if skeleton:options.skeleton=skeleton
    data=options.anim_sequence_import_data if animation else options.skeletal_mesh_import_data
    data.convert_scene=True;data.convert_scene_unit=True;data.import_uniform_scale=1.
    if animation:
        data.set_editor_property('use_default_sample_rate',False)
        data.set_editor_property('custom_sample_rate',60)
        data.set_editor_property('animation_length',u.FBXAnimationLengthImportType.FBXALIT_EXPORTED_TIME)
    else:
        data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS
        options.create_physics_asset=True
    return options

def import_root_units(clip,mesh):
    # FBX animation-only import can omit the Armature unit-conversion scale.
    # Preserve this rig's bind scale without changing child motion or timing.
    options=u.AnimPoseEvaluationOptions()
    options.set_editor_property('evaluation_type',u.AnimDataEvalType.SOURCE)
    options.set_editor_property('optional_skeletal_mesh',mesh)
    pose=u.AnimPoseExtensions.get_anim_pose_at_time(clip,0.,options)
    root=u.AnimPoseExtensions.get_bone_names(pose)[0]
    ref=u.AnimPoseExtensions.get_ref_bone_pose(pose,root,u.AnimPoseSpaces.LOCAL)
    first=u.AnimPoseExtensions.get_bone_pose(pose,root,u.AnimPoseSpaces.LOCAL)
    target=[ref.scale3d.x,ref.scale3d.y,ref.scale3d.z]
    previous=[first.scale3d.x,first.scale3d.y,first.scale3d.z]
    changed=max(abs(a-b) for a,b in zip(target,previous))>1e-5
    if changed:
        count=clip.get_editor_property('data_model_interface').get_number_of_keys()
        positions,rotations,scales=[],[],[]
        for i in range(count):
            pose=u.AnimPoseExtensions.get_anim_pose_at_time(clip,clip.get_play_length()*i/max(1,count-1),options)
            value=u.AnimPoseExtensions.get_bone_pose(pose,root,u.AnimPoseSpaces.LOCAL)
            positions.append(value.translation);rotations.append(value.rotation);scales.append(u.Vector(*target))
        controller=clip.get_editor_property('controller')
        controller.open_bracket('Match BellowSacLobber FBX bind units',False)
        try:
            if not controller.set_bone_track_keys(root,positions,rotations,scales,False):
                raise RuntimeError('Root unit import failed: '+clip.get_path_name())
        finally:controller.close_bracket(False)
    return {'root':str(root),'before':previous,'bind':target,'changed':changed}

previous_fbx=u.SystemLibrary.get_console_variable_int_value('Interchange.FeatureFlags.Import.FBX')
u.SystemLibrary.execute_console_command(None,'Interchange.FeatureFlags.Import.FBX 0')
try:
    if stage=='mesh':
        mesh=import_file(ROOT/'Exports/SK_BellowSacLobber_v01.fbx','SK_BellowSacLobber',VERSION,fbx(),u.FbxFactory())
        for asset in (mesh,mesh.skeleton,mesh.physics_asset):
            if asset:save(asset)
        textures={}
        for key,filename in manifest['textures'].items():
            tex=import_file(filename,'T_BellowSacLobber_'+key,VERSION+'/Textures')
            tex.set_editor_property('srgb',key=='BaseColor')
            if key=='Normal':
                tex.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_NORMALMAP)
                tex.set_editor_property('flip_green_channel',True)
            elif key=='MetallicRoughness':
                tex.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_MASKS)
            textures[key]=tex;save(tex)
        mat=create('M_BellowSacLobber',VERSION+'/Materials',u.Material,u.MaterialFactoryNew())
        ME.delete_all_material_expressions(mat)
        mat.set_editor_property('two_sided',True)
        mat.set_editor_property('used_with_skeletal_mesh',True)
        slab=ME.create_material_expression(mat,u.MaterialExpressionSubstrateShadingModels)
        for key,pin,prop,channel in [('BaseColor','BaseColor',u.MaterialProperty.MP_BASE_COLOR,'RGB'),('Normal','Normal',u.MaterialProperty.MP_NORMAL,'RGB'),('MetallicRoughness','Roughness',u.MaterialProperty.MP_ROUGHNESS,'G'),('MetallicRoughness','Metallic',u.MaterialProperty.MP_METALLIC,'B')]:
            sample=ME.create_material_expression(mat,u.MaterialExpressionTextureSample)
            sample.texture=textures[key]
            sample.sampler_type=u.MaterialSamplerType.SAMPLERTYPE_NORMAL if key=='Normal' else u.MaterialSamplerType.SAMPLERTYPE_MASKS if key=='MetallicRoughness' else u.MaterialSamplerType.SAMPLERTYPE_COLOR
            ME.connect_material_property(sample,channel,prop)
            ME.connect_material_expressions(sample,channel,slab,pin)
        ME.connect_material_property(slab,'',u.MaterialProperty.MP_FRONT_MATERIAL)
        ME.recompile_material(mat);save(mat)
        slots=list(mesh.materials)
        for slot in slots:slot.material_interface=mat
        mesh.set_editor_property('materials',slots)
        LIB.set_metadata_tag(mesh,'BellowSacLobber.Source','User-provided decimated SmartRig GLB; original topology and weights preserved')
        save(mesh)
        report['mesh']=mesh.get_path_name();report['skeleton']=mesh.skeleton.get_path_name()
    elif stage=='motion':
        mesh=u.load_asset(VERSION+'/SK_BellowSacLobber')
        clips={}
        for row in manifest['loop_clips']:
            role=row['role'];name='A_BellowSacLobber_'+role
            clip=import_file(row['fbx'],name,VERSION+'/Animations',fbx(True,mesh.skeleton),u.FbxFactory())
            clip.set_editor_property('enable_root_motion',False)
            clip.set_editor_property('force_root_lock',True)
            clip.set_editor_property('loop',True)
            clip.set_preview_skeletal_mesh(mesh)
            report.setdefault('animation_root_units',{})[role]=import_root_units(clip,mesh)
            if not u.WeaponAnimationAuthoring.finalize_authored_animation(clip):
                raise RuntimeError('Animation completion failed: '+name)
            save(clip);clips[role]=clip
        save(mesh.skeleton)
        data_factory=u.DataAssetFactory()
        data_factory.set_editor_property('data_asset_class',u.QuadrupedAnimationSet)
        dataset=create('DA_BellowSacLobber_Locomotion',VERSION,u.QuadrupedAnimationSet,data_factory)
        dataset.set_editor_property('reference_mesh',mesh)
        dataset.set_editor_property('walk_speed',40.)
        dataset.set_editor_property('run_speed',80.)
        dataset.set_editor_property('run_blend_start_ratio',.60)
        dataset.set_editor_property('run_blend_full_ratio',.95)
        actions={}
        for slot,role in [('Idle','Idle'),('IdleAlert','Idle'),('Walk','WalkSlow'),('Run','Move')]:
            entry=u.QuadrupedTemplateAction()
            entry.set_editor_property('sequence',clips[role]);entry.set_editor_property('loop',True)
            entry.set_editor_property('blend_seconds',.25)
            actions[slot]=entry
        dataset.set_editor_property('actions',actions);save(dataset)
        factory=u.BlueprintFactory();factory.set_editor_property('parent_class',u.WolfMonster)
        bp=create('BP_BellowSacLobber',DEST,u.Blueprint,factory)
        u.BlueprintEditorLibrary.compile_blueprint(bp)
        defaults=u.get_default_object(bp.generated_class())
        # Reuse the existing four-foot Character/BT shell for this locomotion
        # stage; no canine attack clips, howl, pounce or skin replacement.
        values={'animation_set':dataset,'monster_display_name':'鼓囊 M-09',
                'walk_speed':80.,'chase_speed':80.,'aggro_radius':3200.,'leash_radius':3200.,
                'howl_on_encounter':False,'use_predictive_hunting':False,
                'use_ragdoll':False,'bite_damage':0.,'pounce_damage':0.,
                'bite_trigger_range':210.,'level':3,'rank':u.MonsterRank.NORMAL,
                'max_health':240.,'experience_reward':0}
        for name,value in values.items():defaults.set_editor_property(name,value)
        defaults.set_editor_property('tags',[u.Name('Enemy'),u.Name('BellowSacLobber'),u.Name('LocomotionStage')])
        defaults.get_editor_property('wound_appearance').set_editor_property('enabled',False)
        capsule=defaults.get_editor_property('capsule_component')
        capsule.set_capsule_size(62.,90.,False)
        movement=defaults.get_editor_property('character_movement')
        movement.set_editor_property('max_walk_speed',80.)
        movement.set_editor_property('max_acceleration',180.)
        movement.set_editor_property('braking_deceleration_walking',260.)
        movement.set_editor_property('rotation_rate',u.Rotator(pitch=0.,yaw=90.,roll=0.))
        movement.set_editor_property('max_step_height',40.)
        nav=movement.get_editor_property('nav_agent_props')
        nav.set_editor_property('agent_radius',62.);nav.set_editor_property('agent_height',204.)
        movement.set_editor_property('nav_agent_props',nav)
        component=defaults.get_editor_property('mesh')
        component.set_skeletal_mesh_asset(mesh)
        component.set_anim_instance_class(u.QuadrupedTemplateAnimInstance.static_class())
        component.set_editor_property('relative_rotation',u.Rotator(pitch=0.,yaw=-90.,roll=0.))
        component.set_editor_property('relative_location',u.Vector(0.,0.,-90.))
        defaults.set_editor_property('ai_controller_class',u.load_class(None,'/Game/Monsters/AI/BP_MonsterAIController.BP_MonsterAIController_C'))
        LIB.set_metadata_tag(bp,'BellowSacLobber.Stage','Idle and locomotion only; attacks and dedicated death not authored')
        u.BlueprintEditorLibrary.compile_blueprint(bp)
        save(bp)
        report['blueprint']=bp.get_path_name();report['animation_set']=dataset.get_path_name()
        report['clips']={role:clip.get_path_name() for role,clip in clips.items()}
    else:
        raise RuntimeError('Unknown stage: '+stage)
finally:
    u.SystemLibrary.execute_console_command(None,'Interchange.FeatureFlags.Import.FBX '+str(previous_fbx))
if stage not in report['stages']:report['stages'].append(stage)
REPORT.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print('BELLOW_SAVED '+stage+' '+json.dumps(report,ensure_ascii=False))
