"""Import right V2 and connect the two attacks to M27 for the user's check.

Only attack_clip, left_slash_clip and right_slash_clip are edited on the
existing primary/review Blueprints. No test, render or game launch.
"""
from pathlib import Path
import json
import unreal as u

ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/MantisM27/Beast06V2')
SOURCE=ROOT/'Delivery'; DEST='/Game/Monsters/MantisM27/Beast06V2/Animations'
MAIN='/Game/Monsters/MantisM27/BP_MantisM27'
REVIEW='/Game/Monsters/MantisM27/Beast06V1/BP_MantisM27_Beast06ReviewV1'
MESH='/Game/Monsters/MantisM27/BindingV2/SK_MantisM27_BindingV2'
LEFT=DEST+'/A_M27_LeftSlash_Beast06V2'
RIGHT=DEST+'/A_M27_RightSlash_Beast06V2'
SLOTS={'attack_clip':'LeftSlash','left_slash_clip':'LeftSlash','right_slash_clip':'RightSlash'}
L=u.EditorAssetLibrary
report={'revision':'Beast06V2','scope':'M27 left/right melee attacks','right_animation_saved':False,
    'blueprints':{},'runtime_tested':False,'offline_validated':False,'rendered':False,'native_code_changed':False}
def path(value): return value.get_path_name() if value else None
def receipt():
    (ROOT/'activation_receipt.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')

try:
    manifest=json.loads((SOURCE/'motion_manifest_right.json').read_text())
    info=manifest['clips']['RightSlash']; name=Path(info['file']).stem
    if '-run=pythonscript' not in u.SystemLibrary.get_command_line().lower():
        dirty={p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
        conflicts=dirty.intersection({MAIN,REVIEW,RIGHT})
        if conflicts: raise RuntimeError('Preserve unsaved target packages: '+', '.join(sorted(conflicts)))
        if u.get_editor_subsystem(u.LevelEditorSubsystem).is_in_play_in_editor():
            raise RuntimeError('Preserve running PIE; defer animation and Blueprint update')
    mesh=u.load_asset(MESH); left=u.load_asset(LEFT)
    if not mesh or not left: raise RuntimeError('Missing BindingV2 mesh or saved left V2 animation')
    targets={}
    for bp_path in [MAIN,REVIEW]:
        bp=u.load_asset(bp_path)
        if not bp: raise RuntimeError('Missing target Blueprint '+bp_path)
        defaults=u.get_default_object(bp.generated_class())
        if defaults.get_editor_property('visual_mesh')!=mesh:
            raise RuntimeError('Target Blueprint mesh changed; preserve '+bp_path)
        timing={p:defaults.get_editor_property(p) for p in ['contact_time','contact_end','recovery_time']}
        if abs(timing['contact_time']-.25)>.001 or abs(timing['contact_end']-.30)>.001:
            raise RuntimeError('Target attack timing changed; preserve '+bp_path)
        report['blueprints'][bp_path]={'saved':False,
            'previous':{p:path(defaults.get_editor_property(p)) for p in SLOTS},
            'preserved_timing':timing,
            'retained_clips':{p:path(defaults.get_editor_property(p)) for p in
                ['idle_clip','walk_clip','death_clip','pounce_windup_clip','pounce_flight_clip','pounce_land_clip']}}
        targets[bp_path]=(bp,defaults)
    receipt()
    options=u.FbxImportUI(); options.automated_import_should_detect_type=False
    options.mesh_type_to_import=u.FBXImportType.FBXIT_ANIMATION; options.import_mesh=False
    options.import_as_skeletal=options.import_animations=True
    options.import_materials=options.import_textures=False; options.skeleton=mesh.skeleton
    for prop,value in {'convert_scene':True,'convert_scene_unit':True,'import_uniform_scale':1.,
        'use_default_sample_rate':False,'custom_sample_rate':60,
        'animation_length':u.FBXAnimationLengthImportType.FBXALIT_EXPORTED_TIME,'preserve_local_transform':True}.items():
        options.anim_sequence_import_data.set_editor_property(prop,value)
    task=u.AssetImportTask(); task.filename=str(SOURCE/info['file']); task.destination_path=DEST; task.destination_name=name
    task.automated=task.replace_existing=task.replace_existing_settings=True; task.save=False
    task.options=options; task.factory=u.FbxFactory()
    u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    right=u.load_asset(RIGHT)
    if not right or not task.imported_object_paths: raise RuntimeError('Right attack import failed')
    right.set_preview_skeletal_mesh(mesh); right.set_editor_property('enable_root_motion',False); right.set_editor_property('force_root_lock',False)
    L.set_metadata_tag(right,'SourceAnimation',manifest['source'])
    L.set_metadata_tag(right,'M27.Authoring','Beast06V2 right: native Attack6 source, short horizontal hook, toe pivots, chest-carried signed blade frame, continuous recovery')
    if not L.save_loaded_asset(right,False): raise RuntimeError('Right animation save failed')
    report.update(right_animation_saved=True,animations={
        'LeftSlash':{'asset':path(left),'seconds':left.get_play_length()},
        'RightSlash':{'asset':path(right),'seconds':right.get_play_length()}})
    receipt()
    clips={'LeftSlash':left,'RightSlash':right}
    for bp_path,(bp,defaults) in targets.items():
        for prop,role in SLOTS.items(): defaults.set_editor_property(prop,clips[role])
        L.set_metadata_tag(bp,'AttackRevision','Beast06V2: left diagonal cut and right Attack6 horizontal hook; weight transfer and continuous recovery; user check pending')
        u.BlueprintEditorLibrary.compile_blueprint(bp)
        if not L.save_loaded_asset(bp,False): raise RuntimeError('Blueprint save failed '+bp_path)
        report['blueprints'][bp_path].update(saved=True,assigned={p:path(clips[r]) for p,r in SLOTS.items()})
        receipt(); print('M27_BEAST06_V2_PAIR_CONNECTED '+bp_path,flush=True)
    report.update(primary_blueprint_saved=True,review_blueprint_saved=True,f6_entry='MantisM27',user_check_pending=True)
    receipt(); print('M27_BEAST06_V2_PAIR_ACTIVATED',flush=True)
except Exception as error:
    report['error']=str(error); receipt(); raise
