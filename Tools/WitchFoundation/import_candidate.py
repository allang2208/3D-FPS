"""Create isolated full-body candidate assets and source-derived foot curves."""
import unreal as u,json
from pathlib import Path
ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/WitchFoundation20260920')
DEST='/Game/Monsters/WitchFoundation'
LIB=u.EditorAssetLibrary; AT=u.AssetToolsHelpers.get_asset_tools()
motion=json.loads((ROOT/'Authoring/motion_manifest.json').read_text())
report={'assets':[],'runtime_tested':False,'status':'authoring'}

def save(a):
    if not LIB.save_loaded_asset(a,False):raise RuntimeError('Could not save '+a.get_path_name())
    if a.get_path_name() not in report['assets']:report['assets'].append(a.get_path_name())
    (ROOT/'ue_delivery.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')

def copy(a,path):
    result=u.load_asset(path) if LIB.does_asset_exist(path) else LIB.duplicate_asset(a.get_path_name(),path)
    if not result:raise RuntimeError('Could not duplicate '+path)
    return result

if u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world():
    raise RuntimeError('PIE is running; candidate import has not begun')
dirty=list(u.EditorLoadingAndSavingUtils.get_dirty_content_packages())
resuming=globals().get('WITCH_FOUNDATION_RESUME_OWN_IMPORT',False)
if any(p.get_path_name().startswith(DEST) for p in dirty) and not resuming:
    raise RuntimeError('Candidate has unsaved edits; preserved without overwriting')

source=u.load_asset('/Game/Characters/Mannequins/Meshes/SKM_Quinn_Simple')
mesh=copy(source,DEST+'/SK_WitchFoundation')
skeleton=copy(source.skeleton,DEST+'/SKEL_WitchFoundation')
if hasattr(u,'WitchMotionCandidate'):
    u.WitchMotionCandidate.assign_foundation_skeleton(mesh,skeleton)
else:
    report['pending_native_binding']=True
physics=copy(source.physics_asset,DEST+'/PA_WitchFoundation')
mesh.set_editor_property('physics_asset',physics)
mat=u.load_asset(DEST+'/Materials/M_Foundation_Charcoal')
if not mat:
    mat=AT.create_asset('M_Foundation_Charcoal',DEST+'/Materials',u.Material,u.MaterialFactoryNew())
    mat.set_editor_property('used_with_skeletal_mesh',True)
    color=u.MaterialEditingLibrary.create_material_expression(mat,u.MaterialExpressionConstant3Vector,-250,0)
    color.set_editor_property('constant',u.LinearColor(.048,.039,.029,1))
    u.MaterialEditingLibrary.connect_material_property(color,'',u.MaterialProperty.MP_BASE_COLOR)
    rough=u.MaterialEditingLibrary.create_material_expression(mat,u.MaterialExpressionConstant,-250,160)
    rough.set_editor_property('r',.82)
    u.MaterialEditingLibrary.connect_material_property(rough,'',u.MaterialProperty.MP_ROUGHNESS)
    metal=u.MaterialEditingLibrary.create_material_expression(mat,u.MaterialExpressionConstant,-250,280)
    metal.set_editor_property('r',0)
    u.MaterialEditingLibrary.connect_material_property(metal,'',u.MaterialProperty.MP_METALLIC)
    u.MaterialEditingLibrary.recompile_material(mat)
slots=list(mesh.materials)
for slot in slots:slot.material_interface=mat
mesh.set_editor_property('materials',slots)
LIB.set_metadata_tag(mesh,'Stage','Complete humanoid locomotion foundation; original robe and witch head pending user review')
LIB.set_metadata_tag(mesh,'Source','Unmodified complete Epic Quinn Simple mesh and original skin weights; isolated duplicate')
for a in (mat,physics,skeleton,mesh):save(a)
u.SystemLibrary.execute_console_command(None,'Interchange.FeatureFlags.Import.FBX 0')
for role,data in motion.items():
    name='A_WitchFoundation_'+role
    path=DEST+'/Animations/'+name
    options=u.FbxImportUI();options.automated_import_should_detect_type=False
    options.mesh_type_to_import=u.FBXImportType.FBXIT_ANIMATION
    options.skeleton=skeleton;options.import_mesh=False;options.import_animations=True
    options.import_materials=False;options.import_textures=False
    imp=options.anim_sequence_import_data
    imp.convert_scene=True;imp.convert_scene_unit=True;imp.import_uniform_scale=1.0
    imp.import_translation=u.Vector(0,0,0);imp.import_rotation=u.Rotator(0,0,0)
    imp.force_front_x_axis=False
    imp.set_editor_property('use_default_sample_rate',False)
    imp.set_editor_property('custom_sample_rate',30)
    imp.set_editor_property('animation_length',u.FBXAnimationLengthImportType.FBXALIT_EXPORTED_TIME)
    old=u.load_asset(path)
    if old:
        saved=old.get_editor_property('asset_import_data')
        for prop,value in [('convert_scene',True),('convert_scene_unit',True),('import_uniform_scale',1.0),('force_front_x_axis',False)]:
            saved.set_editor_property(prop,value)
    task=u.AssetImportTask();task.filename=data['file'];task.destination_path=DEST+'/Animations';task.destination_name=name
    task.factory=u.FbxFactory();task.options=options;task.automated=True;task.save=False
    task.replace_existing=True;task.replace_existing_settings=True
    AT.import_asset_tasks([task])
    if not task.imported_object_paths:raise RuntimeError('Animation import did not produce '+name)
    clip=u.load_asset(path)
    clip.set_editor_property('loop',True);clip.set_editor_property('enable_root_motion',False)
    clip.set_editor_property('force_root_lock',True);clip.set_preview_skeletal_mesh(mesh)
    for curve,values in data['curves'].items():
        if u.AnimationLibrary.does_curve_exist(clip,curve,u.RawCurveTrackTypes.RCT_FLOAT):
            u.AnimationLibrary.remove_curve(clip,curve)
        u.AnimationLibrary.add_curve(clip,curve)
        u.AnimationLibrary.add_float_curve_keys(clip,curve,[i/data['fps'] for i in range(len(values))],values)
    LIB.set_metadata_tag(clip,'Source','Epic matching mannequin '+role+'; full-body carry, articulated fingers, original leg timing')
    LIB.set_metadata_tag(clip,'FootContact','Manual FootSpeed_l/r from source root-motion toe speed; native stride and ground solvers')
    save(clip)
    print('SAVED '+path,flush=True)
save(skeleton)
report['status']='assets imported and saved; native integration and user test pending'
(ROOT/'ue_delivery.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(report,ensure_ascii=False))
