import json,re
from pathlib import Path
import unreal as u
HERE=Path(__file__).parent;ROOT='/Game/Props/GamedevTreasureChest20260922'
E=u.EditorAssetLibrary;AT=u.AssetToolsHelpers.get_asset_tools()
if u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world():raise RuntimeError('Preserve running game; import needs editor mode.')
world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
flag='Interchange.FeatureFlags.Import.FBX';previous=u.SystemLibrary.get_console_variable_int_value(flag)
saved=[]
def save(asset):
    path=asset.get_path_name().split('.')[0]
    if not u.EditorLoadingAndSavingUtils.save_packages([u.load_package(path)],False):raise RuntimeError('Save failed '+path)
    saved.append(asset.get_path_name())
def import_fbx(name,kind,skeleton=None):
    path=ROOT+'/'+name;asset=u.load_asset(path)
    if asset:return asset
    options=u.FbxImportUI();options.automated_import_should_detect_type=False
    options.import_materials=False;options.import_textures=False;options.create_physics_asset=False
    options.import_as_skeletal=kind!='static';options.import_mesh=kind!='animation';options.import_animations=kind=='animation'
    options.mesh_type_to_import={'static':u.FBXImportType.FBXIT_STATIC_MESH,'skeletal':u.FBXImportType.FBXIT_SKELETAL_MESH,'animation':u.FBXImportType.FBXIT_ANIMATION}[kind]
    if skeleton:options.skeleton=skeleton
    data=options.static_mesh_import_data if kind=='static' else options.skeletal_mesh_import_data if kind=='skeletal' else options.anim_sequence_import_data
    data.convert_scene=True;data.convert_scene_unit=True;data.import_uniform_scale=1.0
    if kind=='static':
        data.combine_meshes=True;data.auto_generate_collision=True;data.generate_lightmap_u_vs=True
    if kind!='animation':data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS
    else:data.set_editor_property('animation_length',u.FBXAnimationLengthImportType.FBXALIT_EXPORTED_TIME)
    task=u.AssetImportTask();task.filename=str(HERE/'Authored'/(name+'.fbx'));task.destination_path=ROOT;task.destination_name=name
    task.automated=True;task.save=False;task.replace_existing=False;task.set_editor_property('async_',False)
    task.options=options;task.factory=u.FbxFactory();AT.import_asset_tasks([task])
    results=task.get_objects();asset=next((a for a in results if a.get_path_name()==path+'.'+name),None)
    if not asset:raise RuntimeError('Expected asset missing '+path+'; imported '+str([a.get_path_name() for a in results]))
    return asset
def materials(mesh,skeletal=False):
    slots=mesh.get_editor_property('materials' if skeletal else 'static_materials')
    for index,slot in enumerate(slots):
        n=re.sub(r'[._][0-9]{3}$','',str(slot.get_editor_property('material_slot_name')))
        mat=u.load_asset(ROOT+'/Materials/M_'+n)
        if not mat:raise RuntimeError('Missing chest material '+n)
        if skeletal:
            slot.set_editor_property('material_interface',mat)
            # Unreal Array iteration yields a struct copy; explicitly write it back.
            slots[index]=slot
        else:mesh.set_material(index,mat)
    if skeletal:mesh.set_editor_property('materials',slots)
    E.set_metadata_tag(mesh,'GamedevSource','dungeon_chest_open_model.blend')
try:
    u.SystemLibrary.execute_console_command(world,flag+' 0')
    sk=import_fbx('SK_GamedevTreasureChest','skeletal');materials(sk,True)
    save(sk);skeleton=sk.get_editor_property('skeleton');save(skeleton)
    closed=import_fbx('A_TreasureChest_ClosedPose','animation',skeleton);save(closed)
    opened=import_fbx('A_TreasureChest_OpenPose','animation',skeleton);save(opened)
    opening=None
    if (HERE/'Authored/A_TreasureChest_Opening.fbx').exists():
        opening=import_fbx('A_TreasureChest_Opening','animation',skeleton);save(opening)
    for name in ['SM_TreasureChest_Closed','SM_TreasureChest_Open']:
        mesh=import_fbx(name,'static');materials(mesh)
        mesh.get_editor_property('body_setup').set_editor_property('collision_trace_flag',u.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE)
        nanite=mesh.get_editor_property('nanite_settings');nanite.enabled=True;mesh.set_editor_property('nanite_settings',nanite);save(mesh)
finally:u.SystemLibrary.execute_console_command(world,flag+' '+str(previous))
manifest=json.loads((HERE/'export_manifest.json').read_text(encoding='utf-8'))
config={'mesh':sk.get_path_name(),'close':closed.get_path_name(),'open':opened.get_path_name(),
        'materials':{},'collision_extent':manifest['collision_extent'],
        'collision_center':[manifest['collision_center'][0],-manifest['collision_center'][1],manifest['collision_center'][2]],
        'identity':'gamedev_dungeon_treasure','display_name':'探险宝箱'}
if opening:config['opening']=opening.get_path_name()
(HERE/'treasure_assets.json').write_text(json.dumps(config,ensure_ascii=False,indent=2),encoding='utf-8')
(HERE.parents[1]/'Content/ColdSteelData/treasure_chest_assets.json').write_text(json.dumps(config,ensure_ascii=False,indent=2),encoding='utf-8')
(HERE/'import_receipt.json').write_text(json.dumps({'saved':saved,'tested':False},indent=2),encoding='utf-8')
print('TREASURE_ASSETS_SAVED '+json.dumps(saved))
