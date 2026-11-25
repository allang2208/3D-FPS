"""Import R4 pieces and switch the existing placed resident's blueprint in place."""
from pathlib import Path
import json,shutil,hashlib
import unreal as u

P=Path(u.Paths.convert_relative_path_to_full(u.Paths.project_dir()))
S=P/'SourceAssets/HillsVillageStable/StablemasterMeshyR4'
OLD='/Game/WorldGeneration/TemperateHills/VillageStable/StablemasterMeshyR3'
NEW=OLD[:-1]+'4'
batch=S.resolve().parents[3]/'HillsVillageStable/StablemasterMeshyR4'
m=u.MaterialEditingLibrary;e=u.EditorAssetLibrary;tools=u.AssetToolsHelpers.get_asset_tools()
def asset(path):
    v=e.load_asset(path)
    if v is None:raise RuntimeError('Missing asset '+path)
    return v
def save(v):
    if not e.save_loaded_asset(v,False):raise RuntimeError('Unable to save '+v.get_path_name())
    return v
def importer(source,folder,factory,opts=None):
    task=u.AssetImportTask();task.filename=str(source);task.destination_path=NEW+'/'+folder;task.destination_name=source.stem
    task.automated=True;task.replace_existing=True;task.save=False;task.factory=factory
    if opts:task.options=opts
    tools.import_asset_tasks([task]);return asset(NEW+'/'+folder+'/'+source.stem)
def skin():
    tx=importer(S/'T_Stablemaster_Head_R4_Color.png','Textures',u.TextureFactory())
    tx.set_editor_property('srgb',True);tx.set_editor_property('lod_group',u.TextureGroup.TEXTUREGROUP_CHARACTER)
    tx.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_DEFAULT);save(tx)
    path=NEW+'/Materials/M_Stablemaster_Head_R4'
    mat=asset(path) if e.does_asset_exist(path) else e.duplicate_asset(OLD+'/Materials/M_Stablemaster_Head_0',path)
    replacements=0
    for node in m.get_material_expressions(mat):
        if isinstance(node,u.MaterialExpressionTextureSample) and node.texture and node.texture.get_name() in ('T_Stablemaster_Head_0_Color',tx.get_name()):
            node.modify();node.texture=tx;replacements+=1
    if not replacements:raise RuntimeError('Head material has no source albedo sample')
    m.recompile_material(mat);return save(mat)
def part(role,mat,skel):
    ui=u.FbxImportUI();ui.automated_import_should_detect_type=False
    ui.mesh_type_to_import=u.FBXImportType.FBXIT_SKELETAL_MESH;ui.import_as_skeletal=True
    ui.import_mesh=True;ui.import_materials=False;ui.import_textures=False;ui.import_animations=False;ui.create_physics_asset=False;ui.skeleton=skel
    opt=ui.skeletal_mesh_import_data;opt.convert_scene=True;opt.convert_scene_unit=True
    opt.force_front_x_axis=False;opt.set_editor_property('bUseT0AsRefPose',False)
    opt.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS
    sk=importer(S/('SK_Stablemaster_'+role+'.fbx'),'Meshes',u.FbxFactory(),ui)
    slots=list(sk.materials)
    if len(slots)!=1 or sk.skeleton!=skel:raise RuntimeError('Unexpected material slots or skeleton on '+role)
    slots[0].material_interface=mat;sk.set_editor_property('materials',slots)
    return save(sk)
def standing(body):
    name='A_Stablemaster_Stand_R4';folder=NEW+'/Animations';path=folder+'/'+name
    if e.does_asset_exist(path):seq=asset(path)
    else:
        factory=u.AnimSequenceFactory();factory.target_skeleton=body.skeleton;factory.preview_skeletal_mesh=body
        seq=tools.create_asset(name,folder,u.AnimSequence,factory)
    data=json.loads((S/'standing.json').read_bytes());ctl=seq.get_editor_property('controller')
    ctl.open_bracket('Fit stablemaster standing idle to sleeves and hip pouch',False)
    try:
        ctl.set_frame_rate(u.FrameRate(data['rate'],1),False);ctl.set_number_of_frames(u.FrameNumber(data['frame_count']),False)
        tracks=set(map(str,u.AnimationLibrary.get_animation_track_names(seq)))
        for n,keys in data['tracks'].items():
            if n not in tracks:ctl.add_bone_curve(n,False)
            if not ctl.set_bone_track_keys(n,[u.Vector(*k[:3]) for k in keys],[u.Quat(*k[3:7]) for k in keys],[u.Vector(*k[7:]) for k in keys],False):raise RuntimeError(n)
    finally:ctl.close_bracket(False)
    seq.set_editor_property('enable_root_motion',False);seq.set_editor_property('force_root_lock',True)
    seq.set_editor_property('root_motion_root_lock',u.RootMotionRootLock.REF_POSE);seq.set_editor_property('loop',True)
    return save(seq)

def publish():
    if u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world():raise RuntimeError('Finish active PIE before updating the resident')
    bpfile=P/'Content'/(OLD[6:]+'/BP_Stablemaster.uasset')
    bp=asset(OLD+'/BP_Stablemaster')
    if bp.get_outermost() in u.EditorLoadingAndSavingUtils.get_dirty_content_packages():raise RuntimeError('The stablemaster blueprint has unsaved local edits')
    before=hashlib.sha256(bpfile.read_bytes()).hexdigest()
    copy=batch/'Before'/before/bpfile.name;copy.parent.mkdir(parents=True,exist_ok=True)
    if not copy.exists():shutil.copy2(bpfile,copy)
    u.SystemLibrary.execute_console_command(None,'Interchange.FeatureFlags.Import.FBX 0')
    skel=asset(OLD+'/Meshes/SK_Stablemaster_Body_Skeleton');mat=skin()
    body=part('Body',asset(OLD+'/Materials/M_Stablemaster_Body_0'),skel)
    head=part('Head',mat,skel);clip=standing(body)
    sub=u.get_engine_subsystem(u.SubobjectDataSubsystem);lib=u.SubobjectDataBlueprintFunctionLibrary
    templates=[lib.get_object_for_blueprint(lib.get_data(h),bp) for h in sub.k2_gather_subobject_data_for_blueprint(bp)]
    child,=[o for o in templates if isinstance(o,u.SkeletalMeshComponent) and 'StablemasterHead' in o.get_name()]
    if hashlib.sha256(bpfile.read_bytes()).hexdigest()!=before:raise RuntimeError('Blueprint was updated during asset import')
    bp.modify();child.modify();child.set_skeletal_mesh_asset(head)
    u.BlueprintEditorLibrary.compile_blueprint(bp)
    cdo=u.get_default_object(bp.generated_class());cdo.modify()
    main=cdo.mesh;main.modify();main.set_skeletal_mesh_asset(body)
    main.set_animation_mode(u.AnimationMode.ANIMATION_SINGLE_NODE)
    play=main.get_editor_property('animation_data');play.anim_to_play=clip;play.saved_looping=True;play.saved_playing=True;play.saved_position=0.;play.saved_play_rate=1.
    main.set_editor_property('animation_data',play)
    save(bp)
    (S/'published.json').write_text(json.dumps(dict(blueprint=bp.get_path_name(),body=body.get_path_name(),head=head.get_path_name(),idle=clip.get_path_name(),skeleton=skel.get_path_name(),material=mat.get_path_name(),before=str(copy),before_sha256=before,blueprint_sha256=hashlib.sha256(bpfile.read_bytes()).hexdigest(),level_placement='existing Village_Stable_Stablemaster',play_test=False),indent=2))
publish()
