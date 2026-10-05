"""Background M25 hit surface, health defaults and response-animation delivery."""
from pathlib import Path
import json, sys, traceback
import unreal as u
ROOT=Path(__file__).resolve().parent
PROJECT=ROOT.parents[2]
DEST='/Game/Monsters/VortexCofferM25'
REV='M25HitWeakpoint20261004V1'
LIB=u.EditorAssetLibrary
record=dict(revision=REV,stage='started',saved=[],runtime_tested=False,rendered=False)
sys.path.insert(0,str(PROJECT/'Tools/InfectedDog'))
from meshy_animation_units import match_bind_root_scale
def receipt():
    (ROOT/'asset_receipt.json').write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf-8')
def load(path):
    asset=u.load_asset(path)
    if asset is None:raise RuntimeError('Missing asset: '+path)
    return asset
def save(asset):
    LIB.set_metadata_tag(asset,'M25.HitWeakpointRevision',REV)
    if not LIB.save_loaded_asset(asset,False):raise RuntimeError('Save failed: '+asset.get_path_name())
    record['saved'].append(asset.get_path_name());receipt()
def own_existing(path):
    if not LIB.does_asset_exist(path):return None
    asset=load(path)
    if LIB.get_metadata_tag(asset,'M25.HitWeakpointRevision')!=REV:
        raise RuntimeError('Preserving existing unowned asset: '+path)
    return asset
def import_clip(role,mesh,skeleton):
    name='A_M25_'+role+'_V01';path=DEST+'/Animations/'+name
    clip=own_existing(path)
    if clip is None:
        op=u.FbxImportUI()
        op.automated_import_should_detect_type=False
        op.mesh_type_to_import=u.FBXImportType.FBXIT_ANIMATION
        op.import_as_skeletal=True;op.import_mesh=False;op.import_animations=True
        op.import_materials=False;op.import_textures=False;op.skeleton=skeleton
        data=op.anim_sequence_import_data
        data.set_editor_property('use_default_sample_rate',False)
        data.set_editor_property('custom_sample_rate',30)
        data.set_editor_property('animation_length',u.FBXAnimationLengthImportType.FBXALIT_EXPORTED_TIME)
        data.set_editor_property('remove_redundant_keys',False)
        task=u.AssetImportTask()
        task.filename=str(ROOT/(name+'.fbx'))
        task.destination_path=DEST+'/Animations';task.destination_name=name
        task.options=op;task.automated=True;task.save=False;task.replace_existing=False
        u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
        clip=load(path)
    clip.set_editor_property('enable_root_motion',False)
    clip.set_editor_property('force_root_lock',False)
    clip.set_editor_property('rate_scale',1.)
    clip.set_preview_skeletal_mesh(mesh)
    record.setdefault('root_units',{})[role]=match_bind_root_scale(clip,mesh)
    save(clip)
    return clip
def main():
    if Path(u.Paths.project_dir()).resolve()!=PROJECT.resolve():raise RuntimeError('Wrong project')
    if '-run=pythonscript' not in u.SystemLibrary.get_command_line().lower():
        editor=u.get_editor_subsystem(u.UnrealEditorSubsystem)
        if editor and editor.get_game_world():raise RuntimeError('Stop PIE before asset writes')
    if any(p.get_name().startswith(DEST) for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()):
        raise RuntimeError('Preserving unsaved M25 packages')
    mesh=load(DEST+'/SK_M25_VortexCoffer');skeleton=mesh.get_editor_property('skeleton')
    physics_path=DEST+'/PA_M25_HitSurface_V01'
    asset=own_existing(physics_path)
    record['stage']='authoring_hit_surface';receipt()
    if asset is None:asset=u.VortexCofferM25.build_hit_surface_physics(mesh,physics_path)
    if asset is None:raise RuntimeError('M25 query-body authoring did not produce an asset')
    save(asset)
    cvar='Interchange.FeatureFlags.Import.FBX'
    old=u.SystemLibrary.get_console_variable_int_value(cvar)
    u.SystemLibrary.execute_console_command(None,cvar+' 0')
    try:
        hit=import_clip('Hit',mesh,skeleton)
        death=import_clip('Death',mesh,skeleton)
    finally:
        u.SystemLibrary.execute_console_command(None,cvar+' '+str(old))
    save(skeleton)
    bp=load(DEST+'/BP_VortexCofferM25')
    u.BlueprintEditorLibrary.compile_blueprint(bp)
    cdo=u.get_default_object(bp.generated_class())
    for key,value in dict(max_health=1500.,physical_defense=25,magical_defense=40,
        level=8,rank=u.MonsterRank.NORMAL,experience_reward=100,corpse_seconds=20.,
        hit_surface_physics=asset,hit_clip=hit,death_clip=death,can_be_damaged=True).items():
        cdo.set_editor_property(key,value)
    body=cdo.get_editor_property('mesh')
    body.set_physics_asset(asset)
    body.set_collision_enabled(u.CollisionEnabled.QUERY_ONLY)
    body.set_editor_property('visibility_based_anim_tick_option',
        u.VisibilityBasedAnimTickOption.ALWAYS_TICK_POSE_AND_REFRESH_BONES)
    cdo.get_editor_property('combat').set_editor_property('hit_clip',hit)
    save(bp)
    record.update(stage='assets_saved',physics=asset.get_path_name(),
        animations=[hit.get_path_name(),death.get_path_name()],mesh_component_class=body.get_class().get_name(),
        health=1500,physical_defense=25,magical_defense=40,
        weakpoint='maw_and_maw_rim_bones_shared_critical_damage',
        ordinary_hits='shared_local_gun_feedback_without_forced_stagger',
        hard_control='shared_toughness_stun_interrupts_both_channels',
        death='soft_collapse_then_hold_stop_attacks_and_back_electric',
        gameplay_tested=False)
    receipt()
    u.log('M25_HIT_WEAKPOINT_ASSETS_SAVED')
try:main()
except Exception:
    record.update(stage='production_failed',error=traceback.format_exc());receipt();raise
