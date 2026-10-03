"""Import the V5 skin, its complete compatible animation set, and bind the existing BP."""
from pathlib import Path
import json,sys,traceback
import unreal as u
ROOT=Path(__file__).resolve().parent;PROJECT=ROOT.parents[2]
DEST='/Game/Monsters/M10Mawcrawler';FOLDER=DEST+'/SurfaceRigV5';REV='M10SurfaceRigV5_20261003'
sys.path.insert(0,str(PROJECT/'Tools/InfectedDog'))
from meshy_animation_units import match_bind_root_scale
lib=u.EditorAssetLibrary;tools=u.AssetToolsHelpers.get_asset_tools()
report={'revision':REV,'saved':[],'source_pose_rendered':True,'game_tested':False}
def receipt():(ROOT/'asset_receipt.json').write_text(json.dumps(report,ensure_ascii=False,indent=2,default=str),encoding='utf8')
def load(path):
    asset=u.load_asset(path)
    if asset is None:raise RuntimeError('Missing '+path)
    return asset
def save(asset):
    lib.set_metadata_tag(asset,'M10.SurfaceRevision',REV)
    if not lib.save_loaded_asset(asset,False):raise RuntimeError('Save failed '+asset.get_path_name())
    report['saved'].append(asset.get_path_name());receipt()
def imp(file,name,folder,options=None):
    path=folder+'/'+name
    if lib.does_asset_exist(path):
        asset=load(path)
        if lib.get_metadata_tag(asset,'M10.SurfaceRevision')!=REV:raise RuntimeError('Preserving unowned '+path)
        return asset
    task=u.AssetImportTask();task.filename=str(file);task.destination_path=folder;task.destination_name=name
    task.options=options;task.automated=True;task.save=False;task.replace_existing=False
    tools.import_asset_tasks([task]);return load(path)
if Path(u.Paths.project_dir()).resolve()!=PROJECT.resolve():raise RuntimeError('Wrong project')
if '-run=pythonscript' not in u.SystemLibrary.get_command_line().lower():
    level=u.get_editor_subsystem(u.LevelEditorSubsystem)
    if level and level.is_in_play_in_editor():raise RuntimeError('End the authorized PIE before importing the rig')
if any(p.get_name().startswith(DEST) for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()):raise RuntimeError('Preserving unsaved M10 assets')
old=u.SystemLibrary.get_console_variable_int_value('Interchange.FeatureFlags.Import.FBX')
try:
    u.SystemLibrary.execute_console_command(None,'Interchange.FeatureFlags.Import.FBX 0')
    contract=json.loads((ROOT/'export_contract.json').read_text(encoding='utf8'))
    op=u.FbxImportUI();op.automated_import_should_detect_type=False;op.mesh_type_to_import=u.FBXImportType.FBXIT_SKELETAL_MESH
    op.import_as_skeletal=True;op.import_mesh=True;op.import_animations=False;op.import_materials=False;op.import_textures=False;op.create_physics_asset=True
    data=op.skeletal_mesh_import_data;data.set_editor_property('normal_import_method',u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS)
    data.set_editor_property('import_morph_targets',True);data.set_editor_property('use_t0_as_ref_pose',False);data.set_editor_property('update_skeleton_reference_pose',False)
    mesh=imp(contract['mesh_file'],'SK_M10_SurfaceRig_V5',FOLDER,op)
    material=load(DEST+'/Materials/M_M10_MeshySurface')
    oral_materials={};mel=u.MaterialEditingLibrary
    for suffix,color,roughness in [('OralInterior',(.008,.0015,.003),.55),('OralTeeth',(.58,.48,.35),.31),('OralGum',(.16,.060,.055),.46)]:
        name='M_M10_'+suffix;oral_path=FOLDER+'/'+name
        if lib.does_asset_exist(oral_path):
            oral=load(oral_path)
            if lib.get_metadata_tag(oral,'M10.SurfaceRevision')!=REV:raise RuntimeError('Preserving unowned '+oral_path)
        else:oral=tools.create_asset(name,FOLDER,u.Material,u.MaterialFactoryNew())
        mel.delete_all_material_expressions(oral);oral.set_editor_property('two_sided',True)
        tint=mel.create_material_expression(oral,u.MaterialExpressionConstant3Vector);tint.set_editor_property('constant',u.LinearColor(*color,1))
        mel.connect_material_property(tint,'',u.MaterialProperty.MP_BASE_COLOR)
        rough=mel.create_material_expression(oral,u.MaterialExpressionConstant);rough.set_editor_property('r',roughness);mel.connect_material_property(rough,'',u.MaterialProperty.MP_ROUGHNESS)
        mel.recompile_material(oral);save(oral);oral_materials[suffix]=oral
    slots=list(mesh.get_editor_property('materials'))
    for i,slot in enumerate(slots):
        slot.material_interface=next((m for name,m in oral_materials.items() if name in str(slot.material_slot_name)),material);slots[i]=slot
    report['materials']={str(slot.material_slot_name):slot.material_interface.get_path_name() for slot in slots}
    mesh.set_editor_property('materials',slots);mesh.set_editor_property('enable_per_poly_collision',False)
    if not u.M10Mawcrawler.configure_surface_rig(mesh):raise RuntimeError('V5 corrective morph import/metadata incomplete')
    skeleton=mesh.get_editor_property('skeleton');physics=mesh.get_editor_property('physics_asset')
    if not physics or not u.M10Mawcrawler.build_physics(mesh,physics):raise RuntimeError('V5 physics authoring incomplete')
    save(skeleton);save(physics);save(mesh)
    height=imp(ROOT/'M10_FaceHeight16.png','T_M10_FaceHeight16',FOLDER+'/Authoring')
    height.set_editor_property('srgb',False);height.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_DISPLACEMENTMAP)
    height.set_editor_property('never_stream',False);save(height)
    clips={}
    for role,row in contract['clips'].items():
        op=u.FbxImportUI();op.automated_import_should_detect_type=False;op.mesh_type_to_import=u.FBXImportType.FBXIT_ANIMATION
        op.import_as_skeletal=True;op.import_mesh=False;op.import_animations=True;op.import_materials=False;op.import_textures=False;op.skeleton=skeleton
        data=op.anim_sequence_import_data;data.set_editor_property('use_default_sample_rate',False);data.set_editor_property('custom_sample_rate',30)
        data.set_editor_property('animation_length',u.FBXAnimationLengthImportType.FBXALIT_EXPORTED_TIME);data.set_editor_property('remove_redundant_keys',False)
        clip=imp(row['file'],'A_M10_'+role+'_V5',FOLDER+'/Animations',op)
        clip.set_editor_property('enable_root_motion',False);clip.set_editor_property('force_root_lock',False);clip.set_editor_property('rate_scale',1.)
        clip.set_preview_skeletal_mesh(mesh);report.setdefault('root_unit_adaptation',{})[role]=match_bind_root_scale(clip,mesh)
        save(clip);clips[role]=clip
    bp=load(DEST+'/BP_M10Mawcrawler');u.BlueprintEditorLibrary.compile_blueprint(bp);cdo=u.get_default_object(bp.generated_class())
    cdo.set_editor_property('visual_mesh',mesh)
    for prop,role in [('idle_clip','Idle'),('move_clip','Walk'),('bite_clip','Bite'),('death_clip','Death'),('howl_clip','Howl'),
        ('curve_left_clip','CurveLeft'),('curve_right_clip','CurveRight'),('pivot_left_clip','PivotLeft'),('pivot_right_clip','PivotRight')]:
        cdo.set_editor_property(prop,clips[role])
    cdo.get_editor_property('combat').set_editor_property('hit_clip',clips['Hit'])
    component=cdo.get_editor_property('mesh');component.set_skeletal_mesh_asset(mesh);component.set_anim_instance_class(u.M10AnimInstance.static_class())
    component.set_editor_property('override_materials',[slot.material_interface for slot in slots]);save(bp)
    report.update(stage='assets_saved',mesh=mesh.get_path_name(),skeleton=skeleton.get_path_name(),physics=physics.get_path_name(),blueprint=bp.get_path_name(),animations={k:v.get_path_name() for k,v in clips.items()},height_texture=height.get_path_name(),morphs=contract['morphs'],combat_timing_preserved=True)
    receipt();u.log('M10_SURFACE_RIG_V5_ASSETS_SAVED')
except Exception:
    report.update(stage='production_failed',error=traceback.format_exc());receipt();raise
finally:u.SystemLibrary.execute_console_command(None,'Interchange.FeatureFlags.Import.FBX '+str(old))
