"""Short, resumable editor batches. Invoke only through mcp_call_codex.ps1."""
import unreal as u,json
from pathlib import Path
ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/WitchRebuilt20260921');DEST='/Game/Monsters/WitchRebuilt'
if Path(u.Paths.convert_relative_path_to_full(u.Paths.get_project_file_path())).resolve()!=ROOT.parent.parent/'FPSGAME.uproject':
    raise RuntimeError('Connected editor is not the FPSGAME host; no assets changed')
LIB=u.EditorAssetLibrary;AT=u.AssetToolsHelpers.get_asset_tools();MEL=u.MaterialEditingLibrary
REPORT=ROOT/'ue_delivery.json'
report=json.loads(REPORT.read_text()) if REPORT.exists() else {'completed':[],'assets':[],'runtime_tested':False}
stage=globals().get('WITCH_REBUILT_STAGE','mesh')
unit_repair=bool(globals().get('WITCH_REBUILT_UNIT_REPAIR',False))
garment_refresh=bool(globals().get('WITCH_REBUILT_GARMENT_REFRESH',False))
def record(name):
    if name not in report['completed']:report['completed'].append(name)
    REPORT.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print('SAVED '+name,flush=True)
def save(a):
    if not LIB.save_loaded_asset(a,False):raise RuntimeError('Save failed: '+a.get_path_name())
    if a.get_path_name() not in report['assets']:report['assets'].append(a.get_path_name())
def duplicate(source,path):
    a=u.load_asset(path) if LIB.does_asset_exist(path) else LIB.duplicate_asset(source,path)
    if not a:raise RuntimeError('Missing source/duplicate '+source)
    save(a);return a
def options(kind,skeleton=None):
    o=u.FbxImportUI();o.automated_import_should_detect_type=False;o.mesh_type_to_import=kind
    o.import_materials=False;o.import_textures=False;o.import_animations=kind==u.FBXImportType.FBXIT_ANIMATION
    o.import_mesh=not o.import_animations;o.import_as_skeletal=kind!=u.FBXImportType.FBXIT_STATIC_MESH
    if skeleton:o.skeleton=skeleton
    data=o.anim_sequence_import_data if o.import_animations else o.skeletal_mesh_import_data if o.import_as_skeletal else o.static_mesh_import_data
    data.convert_scene=True;data.convert_scene_unit=True;data.import_uniform_scale=1.;data.force_front_x_axis=False
    if not o.import_animations:data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_COMPUTE_NORMALS
    if o.import_as_skeletal and not o.import_animations and globals().get('WITCH_REBUILT_IMPORT_VERTEX_COLORS',False):
        data.set_editor_property('vertex_color_import_option',u.VertexColorImportOption.REPLACE)
    return o
def run_import(file,name,path,opts):
    task=u.AssetImportTask();task.filename=str(ROOT/'Delivery'/file);task.destination_path=path;task.destination_name=name
    task.factory=u.FbxFactory();task.options=opts;task.automated=True;task.save=False;task.replace_existing=True;task.replace_existing_settings=True
    AT.import_asset_tasks([task])
    if not task.imported_object_paths:raise RuntimeError('Import failed '+file)
    return u.load_asset(path+'/'+name)
def body_materials(mesh):
    original=u.load_asset('/Game/Monsters/WitchMeshy/Materials/M_Witch_Body')
    robe=u.load_asset(DEST+'/Materials/M_WitchRebuilt_Fabric') if LIB.does_asset_exist(DEST+'/Materials/M_WitchRebuilt_Fabric') else u.load_asset('/Game/Monsters/WitchMeshy/OriginalRobeV05/Materials/M_Witch_V05_OriginalRobe')
    skin=u.load_asset('/Game/ZombieFemale/Asset/Materials/Body/Zombie/MI_HorrorMaidenBodyZombie')
    lining=u.load_asset(DEST+'/Materials/M_WitchRebuilt_Lining') if LIB.does_asset_exist(DEST+'/Materials/M_WitchRebuilt_Lining') else robe
    head=u.load_asset(DEST+'/Materials/M_WitchRebuilt_HeadDetail03') if LIB.does_asset_exist(DEST+'/Materials/M_WitchRebuilt_HeadDetail03') else original
    hat=u.load_asset(DEST+'/Materials/M_WitchRebuilt_HatDetail03') if LIB.does_asset_exist(DEST+'/Materials/M_WitchRebuilt_HatDetail03') else original
    if LIB.does_asset_exist(DEST+'/Materials/M_WitchRebuilt_FabricDetail03'):robe=u.load_asset(DEST+'/Materials/M_WitchRebuilt_FabricDetail03')
    if LIB.does_asset_exist(DEST+'/Materials/M_WitchRebuilt_LiningDetail03'):lining=u.load_asset(DEST+'/Materials/M_WitchRebuilt_LiningDetail03')
    upper_robe=u.load_asset(DEST+'/Materials/M_WitchRebuilt_UpperFabric06') if LIB.does_asset_exist(DEST+'/Materials/M_WitchRebuilt_UpperFabric06') else robe
    if LIB.does_asset_exist(DEST+'/Materials/M_WitchRebuilt_UpperFabric07'):upper_robe=u.load_asset(DEST+'/Materials/M_WitchRebuilt_UpperFabric07')
    if LIB.does_asset_exist(DEST+'/Materials/M_WitchRebuilt_Lining06'):lining=u.load_asset(DEST+'/Materials/M_WitchRebuilt_Lining06')
    for part,path in (('upper','MI_WitchRebuilt_UpperFabric09'),('lower','MI_WitchRebuilt_LowerFabric09'),('lining','MI_WitchRebuilt_Lining09')):
        if LIB.does_asset_exist(DEST+'/Materials/'+path):
            material=u.load_asset(DEST+'/Materials/'+path)
            if part=='upper':upper_robe=material
            elif part=='lower':robe=material
            else:lining=material
    if not all((original,robe,skin)):raise RuntimeError('Required existing skin/identity materials missing')
    slots=list(mesh.materials)
    for slot in slots:
        name=str(slot.get_editor_property('imported_material_slot_name'))
        slot.material_interface=skin if 'AnatomicalSkin' in name else lining if 'Lining' in name else upper_robe if 'UpperRobe' in name else robe if 'Robe' in name else head if 'Head' in name else hat if 'Hat' in name else original
    mesh.set_editor_property('materials',slots)
if u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world():raise RuntimeError('PIE active; import deferred')
if any(p.get_path_name().startswith(DEST) for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()):
    raise RuntimeError('Candidate package has unsaved changes; kept intact')
u.SystemLibrary.execute_console_command(None,'Interchange.FeatureFlags.Import.FBX 0')

if stage=='mesh' and (stage not in report['completed'] or unit_repair or garment_refresh):
    foundation=u.load_asset('/Game/Monsters/WitchFoundation/SK_WitchFoundation')
    skeleton=duplicate(foundation.skeleton.get_path_name(),DEST+'/SKEL_WitchRebuilt')
    physics=duplicate(foundation.physics_asset.get_path_name(),DEST+'/PA_WitchRebuilt')
    o=options(u.FBXImportType.FBXIT_SKELETAL_MESH,skeleton);o.create_physics_asset=False;o.physics_asset=physics
    o.skeletal_mesh_import_data.set_editor_property('update_skeleton_reference_pose',unit_repair)
    existing=u.load_asset(DEST+'/SK_WitchRebuilt') if LIB.does_asset_exist(DEST+'/SK_WitchRebuilt') else None
    if existing and unit_repair:
        imp=existing.get_editor_property('asset_import_data')
        imp.set_editor_property('update_skeleton_reference_pose',True)
        imp.convert_scene=True;imp.convert_scene_unit=True;imp.import_uniform_scale=1.
    elif existing and garment_refresh:
        existing.get_editor_property('asset_import_data').set_editor_property('update_skeleton_reference_pose',False)
    mesh=run_import('SK_WitchRebuilt_ClothBuildSource.fbx','SK_WitchRebuilt',DEST,o)
    body_materials(mesh);mesh.set_editor_property('physics_asset',physics)
    LIB.set_metadata_tag(mesh,'Status','Isolated anatomical candidate; runtime and visual test pending')
    LIB.set_metadata_tag(mesh,'BodySource','Whole Nurse anatomical body fitted to Foundation; original Witch head/hat and separated robe')
    for a in (mesh,skeleton,physics):save(a)
    if unit_repair:
        report['completed']=[x for x in report['completed'] if x not in ('cloth_extracted','cloth') and not x.startswith('animation_')]
        report['status']='Unit repair mesh imported; animation and cloth replacement in progress'
        report['unit_revision']='Foundation armature object conversion 0.01 retained; robe width multiplier 1.0'
    if garment_refresh:
        report['completed']=[x for x in report['completed'] if x not in ('cloth_extracted','cloth')]
        report['status']='Garment polish mesh imported; cloth re-extraction pending'
    record(stage)
elif stage.startswith('animations'):
    roles=globals().get('WITCH_REBUILT_ROLES',('Idle','Walk','CastPoison','ThrowPoisonBottle') if stage=='animations_a' else ('Hit','DeathBackward','TurnLeft','TurnRight'))
    mesh=u.load_asset(DEST+'/SK_WitchRebuilt');skeleton=mesh.skeleton
    manifest=json.loads((ROOT/'Authoring/motion_manifest.json').read_text())
    for role in roles:
        if 'animation_'+role in report['completed'] and not unit_repair and not globals().get('WITCH_REBUILT_ROLES'):continue
        data=manifest[role];name='A_WitchRebuilt_'+role
        o=options(u.FBXImportType.FBXIT_ANIMATION,skeleton)
        imp=o.anim_sequence_import_data
        imp.set_editor_property('use_default_sample_rate',False)
        imp.set_editor_property('custom_sample_rate',data['fps'])
        imp.set_editor_property('animation_length',u.FBXAnimationLengthImportType.FBXALIT_EXPORTED_TIME)
        existing=u.load_asset(DEST+'/Animations/'+name) if LIB.does_asset_exist(DEST+'/Animations/'+name) else None
        if existing and (unit_repair or globals().get('WITCH_REBUILT_ROLES')):
            old=existing.get_editor_property('asset_import_data')
            old.convert_scene=True;old.convert_scene_unit=True;old.import_uniform_scale=1.
            old.set_editor_property('use_default_sample_rate',False);old.set_editor_property('custom_sample_rate',data['fps'])
        clip=run_import(name+'.fbx',name,DEST+'/Animations',o)
        clip.set_editor_property('loop',data['loop']);clip.set_editor_property('enable_root_motion',False)
        clip.set_editor_property('force_root_lock',True);clip.set_preview_skeletal_mesh(mesh)
        for curve,values in data['curves'].items():
            if u.AnimationLibrary.does_curve_exist(clip,curve,u.RawCurveTrackTypes.RCT_FLOAT):u.AnimationLibrary.remove_curve(clip,curve)
            u.AnimationLibrary.add_curve(clip,curve)
            u.AnimationLibrary.add_float_curve_keys(clip,curve,[i/data['fps'] for i in range(len(values))],values)
        LIB.set_metadata_tag(clip,'Source',data['source']);LIB.set_metadata_tag(clip,'Status','Authored; user test pending')
        save(clip);save(skeleton);record('animation_'+role)
elif stage=='cloth':
    mesh=u.load_asset(DEST+'/SK_WitchRebuilt')
    if 'cloth_extracted' not in report['completed']:
        if not u.WitchRebuiltMonster.build_drape(mesh):raise RuntimeError('Cloth extraction failed')
        save(mesh);save(mesh.physics_asset);record('cloth_extracted')
    if 'cloth' not in report['completed'] or globals().get('WITCH_REBUILT_REFRESH_RENDER',False):
        o=options(u.FBXImportType.FBXIT_SKELETAL_MESH,mesh.skeleton);o.create_physics_asset=False;o.physics_asset=mesh.physics_asset
        o.skeletal_mesh_import_data.set_editor_property('update_skeleton_reference_pose',False)
        saved=mesh.get_editor_property('asset_import_data');saved.convert_scene=True;saved.convert_scene_unit=True;saved.import_uniform_scale=1.
        mesh=run_import('SK_WitchRebuilt.fbx','SK_WitchRebuilt',DEST,o);body_materials(mesh)
        if not u.WitchRebuiltMonster.build_drape(mesh):raise RuntimeError('Render drape binding failed')
        LIB.set_metadata_tag(mesh,'Cloth','Drape05: waist-supported lower cloth and independent upper cloth; stable render binding rejects extreme extrapolation; simulation continues through death')
        save(mesh);save(mesh.skeleton);save(mesh.physics_asset);record('cloth')
elif stage=='bottle' and stage not in report['completed']:
    def mat(name,color,rough,opacity=1,emissive=0):
        path=DEST+'/Materials/'+name
        m=u.load_asset(path) if LIB.does_asset_exist(path) else AT.create_asset(name,DEST+'/Materials',u.Material,u.MaterialFactoryNew())
        MEL.delete_all_material_expressions(m)
        if opacity<1:
            m.set_editor_property('blend_mode',u.BlendMode.BLEND_TRANSLUCENT)
            m.set_editor_property('translucency_lighting_mode',u.TranslucencyLightingMode.TLM_SURFACE_PER_PIXEL_LIGHTING)
            m.set_editor_property('two_sided',True)
        slab=MEL.create_material_expression(m,u.MaterialExpressionSubstrateShadingModels)
        def constant(value,prop,pin):
            n=MEL.create_material_expression(m,u.MaterialExpressionConstant3Vector if isinstance(value,tuple) else u.MaterialExpressionConstant)
            n.set_editor_property('constant' if isinstance(value,tuple) else 'r',u.LinearColor(*value,1) if isinstance(value,tuple) else value)
            MEL.connect_material_property(n,'',prop);MEL.connect_material_expressions(n,'',slab,pin)
        constant(color,u.MaterialProperty.MP_BASE_COLOR,'BaseColor');constant(rough,u.MaterialProperty.MP_ROUGHNESS,'Roughness')
        constant(opacity,u.MaterialProperty.MP_OPACITY,'Opacity');constant(.5,u.MaterialProperty.MP_SPECULAR,'Specular')
        if emissive:constant(tuple(x*emissive for x in color),u.MaterialProperty.MP_EMISSIVE_COLOR,'Emissive Color')
        MEL.connect_material_property(slab,'',u.MaterialProperty.MP_FRONT_MATERIAL)
        MEL.recompile_material(m);save(m);return m
    materials={'BottleGlass':mat('M_BottleGlass',(.045,.12,.055),.12,.24),
               'BottleClosure':mat('M_BottleClosure',(.11,.052,.021),.86),
               'BottleLiquid':mat('M_BottleLiquid',(.02,.24,.012),.16,1,.45)}
    o=options(u.FBXImportType.FBXIT_STATIC_MESH)
    o.static_mesh_import_data.set_editor_property('combine_meshes',True)
    o.static_mesh_import_data.set_editor_property('auto_generate_collision',False)
    bottle=run_import('SM_WitchRebuilt_Bottle.fbx','SM_WitchRebuilt_Bottle',DEST+'/Props',o)
    for i,s in enumerate(bottle.static_materials):
        name=str(s.get_editor_property('imported_material_slot_name'))
        for key,m in materials.items():
            if key in name:bottle.set_material(i,m)
    save(bottle);record(stage)
print('WITCH_REBUILT '+stage+' finished; no gameplay test',flush=True)
