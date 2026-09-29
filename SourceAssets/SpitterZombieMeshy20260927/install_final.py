"""Produce and save the Spitter's own UE assets. No PIE, preview or runtime tests."""
import json
import os
from pathlib import Path
import unreal as u

ROOT=Path(__file__).resolve().parent
DEST='/Game/Monsters/SpitterZombie'
LIB=u.EditorAssetLibrary;TOOLS=u.AssetToolsHelpers.get_asset_tools();MEL=u.MaterialEditingLibrary
SUB=u.get_editor_subsystem(u.SkeletalMeshEditorSubsystem)
report={'state':'installing','saved':[],'animations':{},'root_units':{},'runtime_tested':False,'preview_rendered':False}

def record():
    (ROOT/'ue_installation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2,default=str),encoding='utf-8')

def load(path):
    asset=u.load_asset(path)
    if asset is None:raise RuntimeError('Required production input missing: '+path)
    return asset

def save(asset):
    LIB.set_metadata_tag(asset,'Spitter.Revision','MeshyGreen20260927')
    if not LIB.save_loaded_asset(asset,False):raise RuntimeError('Save failed: '+asset.get_path_name())
    if asset.get_path_name() not in report['saved']:report['saved'].append(asset.get_path_name())
    record()

def create(name,folder,cls,factory):
    return u.load_asset(folder+'/'+name) or TOOLS.create_asset(name,folder,cls,factory)

def imp(file,name,folder,options=None):
    task=u.AssetImportTask();task.filename=str(file);task.destination_name=name;task.destination_path=folder
    task.automated=True;task.save=False;task.replace_existing=True;task.replace_existing_settings=True
    if options:task.options=options
    TOOLS.import_asset_tasks([task])
    return load(folder+'/'+name)

def fit_root_units(clip,mesh):
    # FBX container conversion belongs to the animation import, not the child bone lengths.
    opts=u.AnimPoseEvaluationOptions();opts.set_editor_property('evaluation_type',u.AnimDataEvalType.SOURCE)
    opts.set_editor_property('optional_skeletal_mesh',mesh)
    pose=u.AnimPoseExtensions.get_anim_pose_at_time(clip,0.,opts)
    ref=u.AnimPoseExtensions.get_ref_bone_pose(pose,'SpitterRoot',u.AnimPoseSpaces.LOCAL)
    first=u.AnimPoseExtensions.get_bone_pose(pose,'SpitterRoot',u.AnimPoseSpaces.LOCAL)
    target=ref.scale3d;before=first.scale3d
    factors=[a/b for a,b in zip((target.x,target.y,target.z),(before.x,before.y,before.z))]
    result={'before':str(before),'bind':str(target),'factors':factors,'changed':False}
    if max(abs(v-1.) for v in factors)<1e-5:return result
    if max(abs(v-100.) for v in factors)>.01:raise RuntimeError('Unsupported FBX root conversion: '+str(factors))
    count=clip.get_editor_property('data_model_interface').get_number_of_keys()
    positions=[];rotations=[];scales=[]
    for i in range(count):
        pose=u.AnimPoseExtensions.get_anim_pose_at_time(clip,clip.get_play_length()*i/max(1,count-1),opts)
        bone=u.AnimPoseExtensions.get_bone_pose(pose,'SpitterRoot',u.AnimPoseSpaces.LOCAL)
        positions.append(bone.translation);rotations.append(bone.rotation);scales.append(target)
    ctl=clip.get_editor_property('controller');ctl.open_bracket('Apply Meshy FBX container units',False)
    try:
        if not ctl.set_bone_track_keys('SpitterRoot',positions,rotations,scales,False):raise RuntimeError('Root unit conversion failed')
    finally:ctl.close_bracket(False)
    result['changed']=True;return result

if os.environ.get('SPITTER_HEADLESS')!='1':
    level=u.get_editor_subsystem(u.LevelEditorSubsystem)
    if level and level.is_in_play_in_editor():raise RuntimeError('Stop PIE before asset production')
dirty={p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
if any(p.startswith(DEST+'/') for p in dirty):raise RuntimeError('Preserving unsaved Spitter assets')

mesh=load(DEST+'/SK_SpitterZombie');skeleton=mesh.skeleton
manifest=json.loads((ROOT/'Surface/mutant/authoring_manifest.json').read_text(encoding='utf-8'))
textures={}
for semantic,path in manifest['materials'][0]['textures'].items():
    tex=imp(path,'T_Spitter_'+semantic,DEST+'/Textures')
    tex.set_editor_property('srgb',semantic=='BaseColor')
    tex.set_editor_property('max_texture_size',2048 if semantic in ('BaseColor','Normal') else 1024)
    tex.set_editor_property('lod_bias',0);tex.set_editor_property('never_stream',False)
    tex.set_editor_property('global_force_mip_levels_to_be_resident',False)
    tex.set_editor_property('virtual_texture_streaming',False)
    tex.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_NORMALMAP if semantic=='Normal'
        else u.TextureCompressionSettings.TC_MASKS if semantic in ('ORM','TissueMasks') else u.TextureCompressionSettings.TC_DEFAULT)
    tex.set_editor_property('lod_group',u.TextureGroup.TEXTUREGROUP_CHARACTER_NORMAL_MAP if semantic=='Normal' else u.TextureGroup.TEXTUREGROUP_CHARACTER)
    tex.set_editor_property('mip_gen_settings',u.TextureMipGenSettings.TMGS_SHARPEN1 if semantic=='BaseColor' else u.TextureMipGenSettings.TMGS_FROM_TEXTURE_GROUP)
    if semantic=='Normal':tex.set_editor_property('flip_green_channel',False)  # Style V1 already writes DirectX normals.
    save(tex);textures[semantic]=tex

material=create('MI_Spitter_MutantGreen',DEST+'/Materials',u.MaterialInstanceConstant,u.MaterialInstanceConstantFactoryNew())
master='/Game/Monsters/Shared/InfectedSurfaceV1/M_InfectedSurface_V1'
MEL.set_material_instance_parent(material,load(master))
for semantic,tex in textures.items():MEL.set_material_instance_texture_parameter_value(material,semantic,tex)
for key,value in {'NormalStrength':.9,'DryRoughnessBias':0.,'ScabRoughnessBias':.02,
                  'WoundWetness':.8,'DrySpecular':.25,'WetSpecular':.34}.items():
    MEL.set_material_instance_scalar_parameter_value(material,key,value)
MEL.set_material_instance_vector_parameter_value(material,'SkinTint',u.LinearColor(1.,.985,.97,1))
MEL.set_material_instance_vector_parameter_value(material,'ClothTint',u.LinearColor(1.04,1.04,1.05,1))
MEL.update_material_instance(material);save(material)
slots=list(mesh.get_editor_property('materials'))
for slot in slots:slot.material_interface=material
mesh.set_editor_property('materials',slots);mesh.set_editor_property('enable_per_poly_collision',False)
build=SUB.get_lod_build_settings(mesh,0)
build.set_editor_property('recompute_normals',False);build.set_editor_property('recompute_tangents',True)
build.set_editor_property('use_mikk_t_space',True);build.set_editor_property('use_full_precision_u_vs',True)
SUB.set_lod_build_settings(mesh,0,build)
factory=u.DataAssetFactory();factory.set_editor_property('data_asset_class',u.SkeletalMeshLODSettings.static_class())
lods=create('LOD_SpitterZombie',DEST,u.SkeletalMeshLODSettings,factory);groups=[]
for percent,screen in [(1.,1.),(.45,.45),(.16,.18)]:
    info=u.SkeletalMeshLODGroupSettings();reduction=info.get_editor_property('reduction_settings')
    reduction.set_editor_property('num_of_triangles_percentage',percent);reduction.set_editor_property('base_lod',0)
    reduction.set_editor_property('max_bones_per_vertex',4);info.set_editor_property('reduction_settings',reduction)
    size=info.get_editor_property('screen_size');size.set_editor_property('default',screen)
    info.set_editor_property('screen_size',size);groups.append(info)
lods.set_editor_property('lod_groups',groups);save(lods);mesh.set_editor_property('lod_settings',lods)
if not SUB.regenerate_lod(mesh,3,False,False):raise RuntimeError('Spitter LOD production failed')
if not u.SpitterZombie.prepare_physics(mesh):raise RuntimeError('Spitter physics production failed')
save(mesh.physics_asset);save(skeleton);save(mesh)
report.update(mesh=mesh.get_path_name(),skeleton=skeleton.get_path_name(),physics=mesh.physics_asset.get_path_name(),
              material=material.get_path_name(),material_parent=master,lod_count=3)

contract=json.loads((ROOT/'animation_contract.json').read_text(encoding='utf-8'))
movement_variants=contract.get('MovementVariants',{}).get('variants',{})
attack_variants=contract.get('AttackVariants',{}).get('variants',{})
clip_specs={role:spec for role,spec in contract.items() if role not in ['MovementVariants','AttackVariants','MeleePoison']}
# Walk_A is already the standard Walk fallback; import that asset only once.
clip_specs.update({role:spec for role,spec in movement_variants.items() if role!='Walk_A'})
clip_specs.update({role:spec for role,spec in attack_variants.items() if role!='AttackD'})
cvar='Interchange.FeatureFlags.Import.FBX';previous=u.SystemLibrary.get_console_variable_int_value(cvar)
u.SystemLibrary.execute_console_command(None,cvar+' 0')
try:
    for role,spec in clip_specs.items():
        options=u.FbxImportUI();options.automated_import_should_detect_type=False
        options.mesh_type_to_import=u.FBXImportType.FBXIT_ANIMATION;options.import_as_skeletal=True
        options.import_mesh=False;options.import_animations=True;options.import_materials=False;options.import_textures=False;options.skeleton=skeleton
        data=options.anim_sequence_import_data
        data.set_editor_property('use_default_sample_rate',False);data.set_editor_property('custom_sample_rate',spec.get('fps',60))
        data.set_editor_property('animation_length',u.FBXAnimationLengthImportType.FBXALIT_EXPORTED_TIME)
        data.set_editor_property('convert_scene_unit',True);data.set_editor_property('remove_redundant_keys',False)
        clip=imp(spec['file'],spec.get('asset_name','A_Spitter_'+role),DEST+'/Animations',options)
        report['root_units'][role]=fit_root_units(clip,mesh)
        clip.set_editor_property('enable_root_motion',False);clip.set_editor_property('force_root_lock',True)
        clip.set_editor_property('loop',spec['loop']);clip.set_preview_skeletal_mesh(mesh)
        LIB.set_metadata_tag(clip,'Source',spec['source']);save(clip)
        report['animations'][role]=clip.get_path_name();record()
finally:u.SystemLibrary.execute_console_command(None,cvar+' '+str(previous))

factory=u.BlueprintFactory();factory.set_editor_property('parent_class',u.SpitterZombie.static_class())
bp=create('BP_SpitterZombie',DEST,u.Blueprint,factory)
u.BlueprintEditorLibrary.compile_blueprint(bp)
cdo=u.get_default_object(bp.generated_class());cdo.set_editor_property('visual_mesh',mesh)
for prop,role in [('idle_clip','Idle'),('walk_clip','Walk'),('attack_clip','Attack'),('death_clip','Death')]:
    cdo.set_editor_property(prop,load(report['animations'][role]))
if movement_variants:
    order=['Walk_A','Walk_B','Walk_C','Run_A']
    cdo.set_editor_property('movement_clips',[load(report['animations']['Walk' if role=='Walk_A' else role]) for role in order])
    cdo.set_editor_property('movement_reference_speeds',[movement_variants[role]['reference_speed_cm_s'] for role in order])
    report['movement_variants']=[report['animations']['Walk' if role=='Walk_A' else role] for role in order]
import runpy
report['bite_settings']=runpy.run_path(str(ROOT/'BiteV8/melee_settings.py'))['apply_melee_defaults'](cdo,contract['Attack'])
report['attack_revision']=contract['Attack'].get('revision','BiteV8-20260928')
report['attack_mode']=contract['Attack'].get('attack_mode', 'physical_melee_attack_a' if report['attack_revision'].startswith('LibraryAttackV9') else 'physical_melee_bite')
if attack_variants:
    runpy.run_path(str(ROOT/'AttackVariantsV13/install_attacks.py'))['bind_variants'](cdo,attack_variants)
    report['attack_revision']=contract['AttackVariants']['revision']
    report['attack_mode']='physical_melee_random_variants'
    report['attack_selection']=contract['AttackVariants']['selection']
report['movement_selection']=contract.get('MovementVariants',{}).get('selection','')
combat_settings_path=ROOT/'CombatDeathV14/settings.json'
if combat_settings_path.exists():
    combat_settings=json.loads(combat_settings_path.read_text(encoding='utf-8'))
    cdo.set_editor_property('attack_range',combat_settings['attack_range_base_cm'])
    report['combat_revision']=combat_settings['revision']
    report['attack_range_base_cm']=combat_settings['attack_range_base_cm']
    report['death_policy']=combat_settings['death_policy']
ai=load('/Game/Monsters/AI/BP_MonsterAIController');cdo.set_editor_property('ai_controller_class',ai.generated_class())
combat=cdo.get_editor_property('combat')
combat.set_editor_property('hit_clip',load(report['animations']['Stagger']))
combat.set_editor_property('dizzy_clip',load(report['animations']['Dizzy']))
knockdown=cdo.get_editor_property('knockdown')
knockdown.set_editor_property('fall_clip',load(report['animations']['Hit_Knockback']))
knockdown.set_editor_property('get_up_clip',load(report['animations']['LayToIdle']))
knockdown.set_editor_property('prone_get_up_clip',load(report['animations']['ProneToIdle']))
component=cdo.get_editor_property('mesh');component.set_skeletal_mesh_asset(mesh)
component.set_anim_instance_class(u.FatZombieAnimInstance.static_class())
component.set_editor_property('override_materials',[material])
# Construction calculates actor +X from Head -> headfront and the mesh's actual bind bounds.
save(bp);save(skeleton)
report.update(state='assets_saved_and_f6_bound',blueprint=bp.get_path_name(),game_started=False)
record()
status=json.loads((ROOT/'production_status.json').read_text(encoding='utf-8'))
status.update(stage='ue_assets_saved',ue_imported=True,tested=False,blueprint=bp.get_path_name(),
    attack_revision=report['attack_revision'],attack_mode=report['attack_mode'],
    movement_selection=report['movement_selection'],attack_assets_saved=True,
    attack_delivery_scope='ue_assets_installed',attack_import_blocker=None,
    native_attack_build='pending_editor_close_per_user_request' if report['bite_settings']['legacy_projectile_gate'] else 'native_melee_class_loaded')
(ROOT/'production_status.json').write_text(json.dumps(status,ensure_ascii=False,indent=2),encoding='utf-8')
u.log('SPITTER_FINAL_INSTALL_COMPLETE '+DEST)
