"""Save the snap-bite clip and animated eye regions on the existing M10 Blueprint."""
from pathlib import Path
import json,sys,traceback
import unreal as u
ROOT=Path(__file__).resolve().parent;PROJECT=ROOT.parents[2];DEST='/Game/Monsters/M10Mawcrawler';REV='M10CombatV3_20261003'
sys.path.insert(0,str(PROJECT/'Tools/InfectedDog'))
from meshy_animation_units import match_bind_root_scale
lib=u.EditorAssetLibrary;tools=u.AssetToolsHelpers.get_asset_tools()
report={'revision':REV,'saved':[],'runtime_tested':False,'preview_rendered':False}
def receipt():(ROOT/'asset_receipt.json').write_text(json.dumps(report,ensure_ascii=False,indent=2,default=str),encoding='utf-8')
def load(path):
    value=u.load_asset(path)
    if value is None:raise RuntimeError('Missing '+path)
    return value
def save(asset):
    if not lib.save_loaded_asset(asset,False):raise RuntimeError('Save failed '+asset.get_path_name())
    report['saved'].append(asset.get_path_name());receipt()
if Path(u.Paths.project_dir()).resolve()!=PROJECT.resolve():raise RuntimeError('Wrong project')
if any(p.get_name().startswith(DEST) for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()):raise RuntimeError('Preserving unsaved M10 content')
old=u.SystemLibrary.get_console_variable_int_value('Interchange.FeatureFlags.Import.FBX')
try:
    u.SystemLibrary.execute_console_command(None,'Interchange.FeatureFlags.Import.FBX 0')
    mesh=load(DEST+'/SK_M10_Mawcrawler');skeleton=mesh.get_editor_property('skeleton')
    contract=json.loads((ROOT/'bite_contract.json').read_text(encoding='utf-8'))
    folder=DEST+'/Animations/CombatV3';name='A_M10_BiteSnap_V3';path=folder+'/'+name
    clip=u.load_asset(path) if lib.does_asset_exist(path) else None
    if clip is not None and lib.get_metadata_tag(clip,'M10.CombatRevision')!=REV:raise RuntimeError('Preserving unowned '+path)
    if clip is None:
        op=u.FbxImportUI();op.automated_import_should_detect_type=False;op.mesh_type_to_import=u.FBXImportType.FBXIT_ANIMATION
        op.import_as_skeletal=True;op.import_mesh=False;op.import_animations=True;op.import_materials=False;op.import_textures=False;op.skeleton=skeleton
        data=op.anim_sequence_import_data;data.set_editor_property('use_default_sample_rate',False);data.set_editor_property('custom_sample_rate',30)
        data.set_editor_property('animation_length',u.FBXAnimationLengthImportType.FBXALIT_EXPORTED_TIME);data.set_editor_property('remove_redundant_keys',False)
        task=u.AssetImportTask();task.filename=contract['file'];task.destination_path=folder;task.destination_name=name
        task.options=op;task.automated=True;task.save=False;task.replace_existing=False;tools.import_asset_tasks([task]);clip=load(path)
    clip.set_editor_property('enable_root_motion',False);clip.set_editor_property('force_root_lock',False);clip.set_editor_property('rate_scale',1.)
    clip.set_preview_skeletal_mesh(mesh);report['root_unit_adaptation']=match_bind_root_scale(clip,mesh)
    lib.set_metadata_tag(clip,'M10.CombatRevision',REV);save(clip)
    bp=load(DEST+'/BP_M10Mawcrawler');u.BlueprintEditorLibrary.compile_blueprint(bp);cdo=u.get_default_object(bp.generated_class())
    cdo.set_editor_property('bite_clip',clip);cdo.set_editor_property('bite_contact_seconds',contract['contact_seconds'])
    cdo.set_editor_property('bite_lunge_distance',contract['actor_lunge_cm']);cdo.set_editor_property('ranged_body_damage_multiplier',.7)
    options=u.AnimPoseEvaluationOptions();options.set_editor_property('optional_skeletal_mesh',mesh)
    pose=u.AnimPoseExtensions.get_anim_pose_at_time(cdo.get_editor_property('idle_clip'),0.,options)
    def ref(n):return u.AnimPoseExtensions.get_ref_bone_pose(pose,n,u.AnimPoseSpaces.WORLD)
    origin=ref('root').translation;bz=(ref('body_center').translation-origin)/.43
    bx=(ref('body_front').translation-origin-bz*.46)/.75
    by=(ref('leg_02_L_upper').translation-origin-bx*.39-bz*.53)/(-1.045)
    # Fit actual imported bone coordinates. Ellipse orientation is insensitive
    # to mirrored Y; its center uses the full affine mapping.
    rotation=u.MathLibrary.make_rot_from_xz(bx,bz).quaternion();head=ref('head')
    frames=[];regions=json.loads((ROOT/'eye_regions.json').read_text(encoding='utf-8'))
    for eye in regions['eyes']:
        x,y,z=eye['blender_center_m'];frame=u.Transform()
        frame.translation=origin+bx*x+by*y+bz*z;frame.rotation=rotation;frame.scale3d=u.Vector(*eye['radii_cm'])
        frames.append(u.MathLibrary.make_relative_transform(frame,head))
    cdo.set_editor_property('eye_weakpoint_frames',frames)
    lib.set_metadata_tag(bp,'M10.CombatRevision',REV);save(bp)
    report.update(stage='assets_saved',blueprint=bp.get_path_name(),bite_clip=clip.get_path_name(),eyes=len(frames),body_ranged_multiplier=.7,contact_seconds=contract['contact_seconds'],lunge_cm=contract['actor_lunge_cm'])
    receipt();u.log('M10_COMBAT_V3_ASSETS_SAVED')
except Exception:
    report.update(stage='production_failed',error=traceback.format_exc());receipt();raise
finally:u.SystemLibrary.execute_console_command(None,'Interchange.FeatureFlags.Import.FBX '+str(old))
