"""Background UE asset production: import, bind and save. Never starts PIE or renders."""
from pathlib import Path
import json,sys,math
import unreal as u
ROOT=Path(__file__).resolve().parent;PROJECT=ROOT.parents[1]
sys.path.insert(0,str(PROJECT/'Tools/InfectedDog'))
from meshy_animation_units import match_bind_root_scale
DEST='/Game/Monsters/FleshHand';REV='GreenLocalHand20260927V1'
LIB=u.EditorAssetLibrary;TOOLS=u.AssetToolsHelpers.get_asset_tools();MEL=u.MaterialEditingLibrary
SUB=u.get_editor_subsystem(u.SkeletalMeshEditorSubsystem)
report={'state':'importing','revision':REV,'saved':[],'animations':{},'runtime_tested':False,'preview_rendered':False}
def record():(ROOT/'ue_installation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2,default=str),encoding='utf-8')
def load(path):
    asset=u.load_asset(path)
    if asset is None:raise RuntimeError('Required production input missing: '+path)
    return asset
def own(asset):LIB.set_metadata_tag(asset,'FleshHand.Revision',REV)
def save(asset):
    own(asset)
    if not LIB.save_loaded_asset(asset,False):raise RuntimeError('Asset save failed: '+asset.get_path_name())
    if asset.get_path_name() not in report['saved']:report['saved'].append(asset.get_path_name())
    record()
def create(name,cls,factory,folder=DEST):
    path=folder+'/'+name
    if LIB.does_asset_exist(path):
        asset=load(path)
        if LIB.get_metadata_tag(asset,'FleshHand.Revision')!=REV:raise RuntimeError('Preserving independent asset '+path)
        return asset
    asset=TOOLS.create_asset(name,folder,cls,factory)
    if asset is None:raise RuntimeError('Cannot create '+path)
    own(asset);return asset
def import_asset(file,name,folder,options=None):
    path=folder+'/'+name
    if LIB.does_asset_exist(path) and LIB.get_metadata_tag(load(path),'FleshHand.Revision')!=REV:
        raise RuntimeError('Preserving independent import '+path)
    task=u.AssetImportTask();task.filename=str(file);task.destination_name=name;task.destination_path=folder
    task.automated=True;task.save=False;task.replace_existing=True
    if options:task.options=options
    TOOLS.import_asset_tasks([task])
    asset=u.load_asset(path)
    if asset is None:
        assets=[u.load_asset(p) for p in task.imported_object_paths]
        asset=next((a for a in assets if isinstance(a,u.AnimSequence)),None)
    if asset is None:raise RuntimeError('Import failed: '+str(file))
    own(asset);return asset
if Path(u.Paths.project_dir()).resolve()!=PROJECT.resolve():raise RuntimeError('Wrong UE project')
dirty={p.get_name().casefold() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
if any(p.startswith(DEST.casefold()) for p in dirty):raise RuntimeError('Preserving unsaved FleshHand assets')
record()

textures={}
for semantic in ('BaseColor','Normal','ORM','TissueMasks'):
    tex=import_asset(ROOT/'UEInputs'/(semantic+'.png'),'T_FleshHand_'+semantic,DEST+'/Textures')
    tex.set_editor_property('srgb',semantic=='BaseColor')
    tex.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_NORMALMAP if semantic=='Normal' else u.TextureCompressionSettings.TC_MASKS if semantic in ('ORM','TissueMasks') else u.TextureCompressionSettings.TC_DEFAULT)
    tex.set_editor_property('max_texture_size',2048 if semantic in ('BaseColor','Normal') else 1024)
    tex.set_editor_property('never_stream',False);tex.set_editor_property('virtual_texture_streaming',False)
    tex.set_editor_property('lod_group',u.TextureGroup.TEXTUREGROUP_CHARACTER_NORMAL_MAP if semantic=='Normal' else u.TextureGroup.TEXTUREGROUP_CHARACTER)
    if semantic=='Normal':tex.set_editor_property('flip_green_channel',True)
    save(tex);textures[semantic]=tex
material=create('MI_FleshHand_GreenSkin',u.MaterialInstanceConstant,u.MaterialInstanceConstantFactoryNew())
MEL.set_material_instance_parent(material,load('/Game/Monsters/Shared/InfectedSurfaceV1/M_InfectedSurface_V1'))
for semantic,texture in textures.items():MEL.set_material_instance_texture_parameter_value(material,semantic,texture)
for key,value in {'NormalStrength':.9,'DryRoughnessBias':0.,'ScabRoughnessBias':.02,'WoundWetness':.8,'DrySpecular':.25,'WetSpecular':.34}.items():
    MEL.set_material_instance_scalar_parameter_value(material,key,value)
MEL.set_material_instance_vector_parameter_value(material,'SkinTint',u.LinearColor(1,.985,.97,1))
MEL.update_material_instance(material);save(material)
sound=import_asset(ROOT/'UEInputs/S_FleshHand_Impact.wav','S_FleshHand_Impact',DEST+'/Audio');save(sound)

cvar='Interchange.FeatureFlags.Import.FBX';previous=u.SystemLibrary.get_console_variable_int_value(cvar)
u.SystemLibrary.execute_console_command(None,cvar+' 0')
try:
    op=u.FbxImportUI();op.automated_import_should_detect_type=False;op.mesh_type_to_import=u.FBXImportType.FBXIT_SKELETAL_MESH
    op.import_as_skeletal=True;op.import_mesh=True;op.import_animations=False;op.import_materials=False;op.import_textures=False;op.create_physics_asset=True
    data=op.skeletal_mesh_import_data
    data.set_editor_property('normal_import_method',u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS)
    data.set_editor_property('normal_generation_method',u.FBXNormalGenerationMethod.MIKK_T_SPACE)
    data.set_editor_property('use_t0_as_ref_pose',False);data.set_editor_property('update_skeleton_reference_pose',False)
    mesh=import_asset(ROOT/'LocalRig/SK_FleshHand_Green_LocalRigV1.fbx','SK_FleshHand_Green',DEST,op)
    skeleton=mesh.get_editor_property('skeleton');own(skeleton)
    slots=list(mesh.get_editor_property('materials'))
    for i,slot in enumerate(slots):slot.material_interface=material;slots[i]=slot
    mesh.set_editor_property('materials',slots);mesh.set_editor_property('enable_per_poly_collision',False)
    for level in (1,2):
        result=SUB.import_lod(mesh,level,str(ROOT/('LocalRig/LODs/SK_FleshHand_Green_LOD%d.fbx'%level)))
        if result!=level:raise RuntimeError('Authored LOD import failed: '+str(level))
    for level in (0,1,2):
        build=SUB.get_lod_build_settings(mesh,level);build.set_editor_property('recompute_normals',False)
        build.set_editor_property('recompute_tangents',True);build.set_editor_property('use_mikk_t_space',True);build.set_editor_property('use_full_precision_u_vs',True)
        SUB.set_lod_build_settings(mesh,level,build)
    physics=mesh.get_editor_property('physics_asset')
    if physics is None:physics=SUB.create_physics_asset(mesh,True,0)
    if not u.FleshHandMonster.build_query_physics(mesh,physics):raise RuntimeError('Hand query body authoring failed')
    save(physics);save(skeleton);save(mesh)
    report.update(mesh=mesh.get_path_name(),skeleton=skeleton.get_path_name(),physics=physics.get_path_name(),lod_screens=[1,.42,.16])
    source=json.loads((ROOT/'Animations/authoring.json').read_text(encoding='utf-8'))
    for role,row in source['clips'].items():
        options=u.FbxImportUI();options.automated_import_should_detect_type=False;options.mesh_type_to_import=u.FBXImportType.FBXIT_ANIMATION
        options.import_as_skeletal=True;options.import_mesh=False;options.import_animations=True;options.import_materials=False;options.import_textures=False;options.skeleton=skeleton
        data=options.anim_sequence_import_data
        data.set_editor_property('use_default_sample_rate',False);data.set_editor_property('custom_sample_rate',60)
        data.set_editor_property('animation_length',u.FBXAnimationLengthImportType.FBXALIT_EXPORTED_TIME);data.set_editor_property('remove_redundant_keys',False)
        clip=import_asset(row['file'],'A_FleshHand_'+role,DEST+'/Animations',options)
        clip.set_editor_property('enable_root_motion',False)
        # The local root carries vertical support compensation, not navigation displacement.
        clip.set_editor_property('force_root_lock',False);clip.set_editor_property('rate_scale',1.)
        clip.set_preview_skeletal_mesh(mesh)
        report.setdefault('root_units',{})[role]=match_bind_root_scale(clip,mesh)
        save(clip);report['animations'][role]=clip.get_path_name();record()
    options=u.FbxImportUI();options.automated_import_should_detect_type=False;options.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
    options.import_mesh=True;options.import_as_skeletal=False;options.import_materials=False;options.import_textures=False;options.import_animations=False
    options.static_mesh_import_data.set_editor_property('combine_meshes',True)
    options.static_mesh_import_data.set_editor_property('auto_generate_collision',False)
    fist=import_asset(ROOT/'Animations/SM_FleshHand_PalmFist.fbx','SM_FleshHand_PalmFist',DEST,options)
    fist.set_material(0,material);save(fist)
finally:u.SystemLibrary.execute_console_command(None,cvar+' '+str(previous))

# Fit authoring forward to UE's imported bind coordinates instead of guessing FBX handedness.
definition=json.loads((ROOT/'LocalRig/rig_definition.json').read_text(encoding='utf-8'))
heads={b['name']:b['head'] for b in definition['bones']}
options=u.AnimPoseEvaluationOptions();options.set_editor_property('optional_skeletal_mesh',mesh)
pose=u.AnimPoseExtensions.get_anim_pose_at_time(load(report['animations']['Idle']),0.,options)
def sub(a,b):return [a[i]-b[i] for i in range(3)]
def det(a,b,c):return a[0]*(b[1]*c[2]-b[2]*c[1])-b[0]*(a[1]*c[2]-a[2]*c[1])+c[0]*(a[1]*b[2]-a[2]*b[1])
names=['wrist','middle_01','thumb_01','index_03']
source=[heads[n] for n in names];target=[]
for name in names:
    p=u.AnimPoseExtensions.get_ref_bone_pose(pose,name,u.AnimPoseSpaces.WORLD).translation
    target.append([p.x,p.y,p.z])
a,b,c=[sub(p,source[0]) for p in source[1:]];forward=definition['palm_outward_axis'];d=det(a,b,c)
coeff=[det(forward,b,c)/d,det(a,forward,c)/d,det(a,b,forward)/d]
edges=[sub(p,target[0]) for p in target[1:]]
direction=[sum(coeff[j]*edges[j][i] for j in range(3)) for i in range(3)]
yaw=-math.degrees(math.atan2(direction[1],direction[0]))
report['coordinate_fit']={'model_forward_cm':direction,'mesh_yaw':yaw,'source_heads':source,'imported_heads':target}
record()

factory=u.BlueprintFactory();factory.set_editor_property('parent_class',u.MonsterAIController.static_class())
ai=create('BP_FleshHandAIController',u.Blueprint,factory);u.BlueprintEditorLibrary.compile_blueprint(ai)
ai_defaults=u.get_default_object(ai.generated_class());ai_defaults.set_editor_property('behavior',load('/Game/Monsters/AI/BT_Monster'))
ai_defaults.set_editor_property('memory_seconds',3.);save(ai)
blueprints={}
for name,cls in [('BP_FleshHandMinion',u.FleshHandMinion),('BP_FleshHand',u.FleshHandMonster)]:
    factory=u.BlueprintFactory();factory.set_editor_property('parent_class',cls.static_class())
    bp=create(name,u.Blueprint,factory);u.BlueprintEditorLibrary.compile_blueprint(bp);cdo=u.get_default_object(bp.generated_class())
    is_minion=name=='BP_FleshHandMinion'
    cdo.set_editor_property('walk_speed',324. if is_minion else 259.2)
    cdo.set_editor_property('animation_walk_speed',270. if is_minion else 216.)
    cdo.set_editor_property('slam_knockback_distance',150.)
    cdo.set_editor_property('visual_mesh',mesh)
    # Retain retired source assets, but do not restore the cancelled attacks on rebuild.
    cdo.set_editor_property('palm_fist_mesh',None)
    cdo.set_editor_property('hammer_clip',None)
    cdo.set_editor_property('minion_class',None)
    cdo.set_editor_property('ai_controller_class',ai.generated_class())
    for prop,role in [('idle_clip','Idle'),('move_clip','Walk'),('slam_clip','Slam'),('grand_slam_clip','GrandSlam'),('death_clip','Death')]:
        cdo.set_editor_property(prop,load(report['animations'][role]))
    combat=cdo.get_editor_property('combat');combat.set_editor_property('hit_clip',load(report['animations']['Hit']));combat.set_editor_property('dizzy_clip',load(report['animations']['Dizzy']))
    cdo.set_editor_property('impact_sound',sound)
    cdo.set_editor_property('warning_material',load('/Game/Monsters/HandBrain/Materials/M_HandBrain_GroundRing'))
    component=cdo.get_editor_property('mesh');component.set_skeletal_mesh_asset(mesh);component.set_anim_instance_class(u.FatZombieAnimInstance.static_class())
    component.set_editor_property('override_materials',[material])
    # Python Rotator positional arguments differ from C++ FRotator (roll, pitch, yaw).
    # Keep the authored Z-up hand upright; only turn its palm toward actor +X.
    component.set_editor_property('relative_rotation',u.Rotator(pitch=0.,yaw=yaw,roll=0.))
    fist_component=u.find_object(cdo,'PalmFist')
    if fist_component:
        fist_component.set_static_mesh(None)
        fist_component.set_visibility(False)
    cdo.set_editor_property('use_controller_rotation_yaw',False)
    cdo.get_editor_property('character_movement').set_editor_property('orient_rotation_to_movement',True)
    save(bp);blueprints[name]=bp
report.update(state='assets_saved_and_f6_bound',blueprints={n:b.get_path_name() for n,b in blueprints.items()},material=material.get_path_name(),retired_palm_fist=fist.get_path_name(),palm_extension_enabled=False,slam_summoning_enabled=False,game_started=False)
record();u.log('FLESHHAND_INSTALL_COMPLETE '+DEST)

# Preserve the separately authored charge when rebuilding the original family.
charge_source=ROOT/'Charge/authoring.json'
if charge_source.exists():
    charge_installer=ROOT/'install_charge.py'
    exec(compile(charge_installer.read_text(encoding='utf-8'),str(charge_installer),'exec'),{'__file__':str(charge_installer),'__name__':'__main__'})

if (ROOT/'Knockdown/authoring.json').exists():
    knockdown_installer=ROOT/'install_knockdown.py'
    exec(compile(knockdown_installer.read_text(encoding='utf-8'),str(knockdown_installer),'exec'),{'__file__':str(knockdown_installer),'__name__':'__main__'})

if (ROOT/'ChargeVisual/audio_source.json').exists():
    visual_installer=ROOT/'install_charge_visual.py'
    exec(compile(visual_installer.read_text(encoding='utf-8'),str(visual_installer),'exec'),{'__file__':str(visual_installer),'__name__':'__main__'})

if (ROOT/'Locomotion/authoring.json').exists():
    locomotion_installer=ROOT/'install_locomotion.py'
    exec(compile(locomotion_installer.read_text(encoding='utf-8'),str(locomotion_installer),'exec'),{'__file__':str(locomotion_installer),'__name__':'__main__'})
