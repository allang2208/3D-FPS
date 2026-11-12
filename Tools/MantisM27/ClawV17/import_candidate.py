"""Save two small ClawV16-derived refinements on a separate review Blueprint."""
from pathlib import Path
import json
import unreal as u

ROOT = Path('D:/FPS3D/FPSGAME/SourceAssets/MantisM27/ClawV17')
SOURCE = ROOT/'Delivery'; DEST = '/Game/Monsters/MantisM27/ClawV17/Animations'
MAIN = '/Game/Monsters/MantisM27/BP_MantisM27'
REVIEW = '/Game/Monsters/MantisM27/ClawV17/BP_MantisM27_ClawReviewV17'
SLOTS = {'attack_clip':'LeftSlash','left_slash_clip':'LeftSlash','right_slash_clip':'RightSlash'}
L = u.EditorAssetLibrary
report = {'revision':'ClawV17','status':'candidate_only','clips':{},'animation_assets_saved':False,
    'review_blueprint_saved':False,'formal_blueprint_modified':False,
    'runtime_tested':False,'offline_validated':False,'rendered':False,'native_code_changed':False}
def path(obj): return obj.get_path_name() if obj else None
def receipt():
    (ROOT/'ue_receipt.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')

try:
    manifest = json.loads((SOURCE/'motion_manifest.json').read_text(encoding='utf-8'))
    packages = {DEST+'/'+Path(info['file']).stem for info in manifest['clips'].values()}
    if '-run=pythonscript' not in u.SystemLibrary.get_command_line().lower():
        dirty = {p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
        conflicts = dirty.intersection(packages | {MAIN,REVIEW})
        if conflicts: raise RuntimeError('Preserve unsaved packages: '+', '.join(sorted(conflicts)))
        if u.get_editor_subsystem(u.LevelEditorSubsystem).is_in_play_in_editor():
            raise RuntimeError('Preserve running PIE; defer candidate import')
    mesh = u.load_asset('/Game/Monsters/MantisM27/BindingV2/SK_MantisM27_BindingV2'); main = u.load_asset(MAIN)
    if not mesh or not main: raise RuntimeError('Missing M27 inputs')
    defaults = u.get_default_object(main.generated_class())
    if defaults.get_editor_property('visual_mesh') != mesh: raise RuntimeError('Formal mesh changed; preserve setup')
    report['formal_retained'] = {prop:path(defaults.get_editor_property(prop)) for prop in SLOTS}
    for prop,role in SLOTS.items():
        name = 'A_M27_'+role+'_ClawV16'
        if report['formal_retained'][prop] != '/Game/Monsters/MantisM27/ClawV16/Animations/'+name+'.'+name:
            raise RuntimeError('Formal melee changed since rollback; preserve '+prop)
    report['inherited_clips'] = {prop:path(defaults.get_editor_property(prop)) for prop in
        ['idle_clip','walk_clip','death_clip','pounce_windup_clip','pounce_flight_clip','pounce_land_clip']}
    report['preserved_timing'] = {prop:defaults.get_editor_property(prop) for prop in ['contact_time','contact_end','recovery_time']}
    receipt()
    for role,info in manifest['clips'].items():
        name = Path(info['file']).stem; options = u.FbxImportUI()
        options.automated_import_should_detect_type = False; options.mesh_type_to_import = u.FBXImportType.FBXIT_ANIMATION
        options.import_mesh = False; options.import_as_skeletal = options.import_animations = True
        options.import_materials = options.import_textures = False; options.skeleton = mesh.skeleton
        for prop,value in {'convert_scene':True,'convert_scene_unit':True,'import_uniform_scale':1.,
            'use_default_sample_rate':False,'custom_sample_rate':60,
            'animation_length':u.FBXAnimationLengthImportType.FBXALIT_EXPORTED_TIME,'preserve_local_transform':True}.items():
            options.anim_sequence_import_data.set_editor_property(prop,value)
        task = u.AssetImportTask(); task.filename = str(SOURCE/info['file']); task.destination_path = DEST; task.destination_name = name
        task.automated = task.replace_existing = task.replace_existing_settings = True; task.save = False
        task.options = options; task.factory = u.FbxFactory()
        u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task]); clip = u.load_asset(DEST+'/'+name)
        if not clip or not task.imported_object_paths: raise RuntimeError('Import failed: '+role)
        clip.set_preview_skeletal_mesh(mesh); clip.set_editor_property('enable_root_motion',False); clip.set_editor_property('force_root_lock',False)
        L.set_metadata_tag(clip,'SourceAnimation',info['source'])
        L.set_metadata_tag(clip,'M27.Authoring','ClawV17 candidate: dense pre-Beast06 ClawV16 poses; entry and late recovery timing only; .16-.36s unchanged')
        if not L.save_loaded_asset(clip,False): raise RuntimeError('Save failed: '+role)
        report['clips'][role] = {'asset':path(clip),'seconds':clip.get_play_length()}; receipt()
        print('M27_CLAW_V17_CANDIDATE_SAVED '+role,flush=True)
    report['animation_assets_saved'] = True; receipt()
    review = u.load_asset(REVIEW) if L.does_asset_exist(REVIEW) else L.duplicate_asset(MAIN,REVIEW)
    if not review: raise RuntimeError('Unable to create candidate Blueprint')
    cdo = u.get_default_object(review.generated_class())
    for prop,role in SLOTS.items(): cdo.set_editor_property(prop,u.load_asset(report['clips'][role]['asset']))
    L.set_metadata_tag(review,'AttackRevision','ClawV17 candidate: minimal timing refinement of original ClawV16; formal remains ClawV16')
    u.BlueprintEditorLibrary.compile_blueprint(review)
    if not L.save_loaded_asset(review,False): raise RuntimeError('Candidate Blueprint save failed')
    report.update(review_blueprint_saved=True,review_blueprint=REVIEW,user_check_pending=True,
        assigned={prop:report['clips'][role]['asset'] for prop,role in SLOTS.items()})
    receipt(); print('M27_CLAW_V17_CANDIDATE_READY '+REVIEW,flush=True)
except Exception as error:
    report['error'] = str(error); receipt(); raise
