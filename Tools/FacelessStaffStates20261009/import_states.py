"""Import the two scoped state revisions and save their original Blueprint entries."""
import unreal as u,json
from pathlib import Path
ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/FacelessStaffStates20261009')
SEC=Path('D:/FPS3D/FPSGAME/SourceAssets/FacelessSecurity20261008/V12')
REC=Path('D:/FPS3D/FPSGAME/SourceAssets/FacelessReceptionist20261007/V05')
LIB=u.EditorAssetLibrary;AT=u.AssetToolsHelpers.get_asset_tools()
if '-run=pythonscript' not in u.SystemLibrary.get_command_line().lower():
    if u.get_editor_subsystem(u.LevelEditorSubsystem).is_in_play_in_editor():raise RuntimeError('PIE active; staff import not started')
source=json.loads((ROOT/'source.json').read_text(encoding='utf-8'))
report=json.loads((ROOT/'ue_delivery.json').read_text(encoding='utf-8')) if (ROOT/'ue_delivery.json').exists() else {'stage':'importing','saved':[],'characters':{},'runtime_tested':False,'rendered':False}
def record():(ROOT/'ue_delivery.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
def save(asset):
    u.SystemLibrary.execute_console_command(None,'Editor.AsyncAssetCompilationFinishAll')
    if not LIB.save_loaded_asset(asset,False):raise RuntimeError('Cannot save '+asset.get_path_name())
    if asset.get_path_name() not in report['saved']:report['saved'].append(asset.get_path_name())
    record();print('STAFF_ASSET_SAVED '+asset.get_path_name(),flush=True)
def import_asset(file,folder,name,options):
    full=folder+'/'+name
    if LIB.does_asset_exist(full):return u.load_asset(full)
    task=u.AssetImportTask();task.filename=str(file);task.destination_path=folder;task.destination_name=name
    task.automated=True;task.save=False;task.replace_existing=False;task.options=options;task.factory=u.FbxFactory()
    AT.import_asset_tasks([task]);asset=u.load_asset(full)
    if not asset or not task.imported_object_paths:raise RuntimeError('Import produced no asset: '+full)
    return asset
# Protect the exact previously reviewed core motion configuration before mutating either entry.
entries={}
for who in ['Security','Receptionist']:
    entry=source['characters'][who];bp=u.load_asset(entry['blueprint']);cdo=u.get_default_object(bp.generated_class())
    allowed=[entry['mesh']]
    if who=='Receptionist':allowed.append('/Game/Monsters/FacelessReceptionist/SK_FacelessReceptionist_V05.SK_FacelessReceptionist_V05')
    if cdo.get_editor_property('visual_mesh').get_path_name() not in allowed:raise RuntimeError('Mesh changed during authoring '+who)
    for role,path in entry['core_clips'].items():
        if cdo.get_editor_property(role+'_clip').get_path_name()!=path:raise RuntimeError('Core motion changed during authoring '+who+' '+role)
    entries[who]=(bp,cdo)
u.SystemLibrary.execute_console_command(None,'Interchange.FeatureFlags.Import.FBX 0')
# Guard: only five new animation assets; current V11 uniform/hat/core motions remain referenced.
base='/Game/Monsters/FacelessSecurity';bp,cdo=entries['Security'];mesh=cdo.get_editor_property('visual_mesh')
skeleton=mesh.get_editor_property('skeleton');manifest=json.loads((SEC/'motion_manifest.json').read_text(encoding='utf-8'));clips={}
for role,entry in manifest['clips'].items():
    options=u.FbxImportUI();options.automated_import_should_detect_type=False;options.mesh_type_to_import=u.FBXImportType.FBXIT_ANIMATION
    options.import_as_skeletal=True;options.import_mesh=False;options.import_animations=True;options.import_materials=False;options.import_textures=False
    options.create_physics_asset=False;options.skeleton=skeleton
    data=options.anim_sequence_import_data;data.convert_scene=True;data.convert_scene_unit=True;data.import_uniform_scale=1.
    data.set_editor_property('use_default_sample_rate',False);data.set_editor_property('custom_sample_rate',round(entry['fps']))
    data.set_editor_property('animation_length',u.FBXAnimationLengthImportType.FBXALIT_EXPORTED_TIME);data.set_editor_property('preserve_local_transform',True)
    clip=import_asset(entry['file'],base+'/Animations/V12','A_Security_'+role+'_V12',options)
    clip.set_preview_skeletal_mesh(mesh);clip.set_editor_property('rate_scale',entry['rate_scale'])
    clip.set_editor_property('enable_root_motion',False);clip.set_editor_property('force_root_lock',False)
    LIB.set_metadata_tag(clip,'StaffStateSource',entry['source']);LIB.set_metadata_tag(clip,'StaffRevision','M03 V12 native ready-stance reactions; V06 locomotion and V10 attack retained')
    save(clip);clips[role]=clip
combat=cdo.get_editor_property('combat');knock=cdo.get_editor_property('knockdown')
combat.set_editor_property('hit_clip',clips['hit']);combat.set_editor_property('dizzy_clip',clips['dizzy'])
for role in ['fall','get_up','prone_get_up']:knock.set_editor_property(role+'_clip',clips[role])
LIB.set_metadata_tag(bp,'StaffStateRevision','V12 native hit, knockdown/recovery, dizzy; common staff transitions; V11 mesh retained')
u.BlueprintEditorLibrary.compile_blueprint(bp);save(skeleton);save(bp)
report['characters']['Security']={'mesh':mesh.get_path_name(),'blueprint':bp.get_path_name(),'clips':{k:v.get_path_name() for k,v in clips.items()},'preserved_core_clips':source['characters']['Security']['core_clips']};record()
# Receptionist: add new cloth states without rewriting the accepted V04 base, materials or bone clips.
base='/Game/Monsters/FacelessReceptionist';bp,cdo=entries['Receptionist']
skeleton=u.load_asset(base+'/SKEL_FacelessReceptionist');physics=u.load_asset(base+'/PA_FacelessReceptionist')
materials={'Receptionist_'+f:u.load_asset(base+'/Materials/M_FR4_'+f) for f in ['Skin','Suit','Shirt','Badge','Trim','Shoes']}
options=u.FbxImportUI();options.automated_import_should_detect_type=False;options.mesh_type_to_import=u.FBXImportType.FBXIT_SKELETAL_MESH
options.import_as_skeletal=True;options.import_mesh=True;options.import_animations=False;options.import_materials=False;options.import_textures=False
options.skeleton=skeleton;options.create_physics_asset=False;options.physics_asset=physics
options.skeletal_mesh_import_data.convert_scene=True;options.skeletal_mesh_import_data.convert_scene_unit=True;options.skeletal_mesh_import_data.import_uniform_scale=1.
data=options.skeletal_mesh_import_data;data.set_editor_property('update_skeleton_reference_pose',False);data.set_editor_property('use_t0_as_ref_pose',False)
data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS;data.set_editor_property('import_morph_targets',True)
meshes={}
for role,name in [('outfit','SK_FacelessReceptionist_V05'),('clothing','SK_FacelessReceptionist_Clothing_V05')]:
    mesh=import_asset(REC/'Delivery'/(name+'.fbx'),base,name,options);slots=list(mesh.materials)
    for slot in slots:
        imported=str(slot.get_editor_property('imported_material_slot_name'))
        chosen=next((v for k,v in materials.items() if imported.startswith(k)),None)
        if not chosen:raise RuntimeError('Unmapped receptionist material '+imported)
        slot.material_interface=chosen
    mesh.set_editor_property('materials',slots);mesh.set_editor_property('physics_asset',physics)
    LIB.set_metadata_tag(mesh,'StaffRevision','M04 V05: V04 geometry/weights/core shapes retained; anatomical hit/down/get-up/dizzy cloth')
    save(mesh);meshes[role]=mesh
mesh=meshes['outfit'];curves=json.loads((REC/'state_curves.json').read_text(encoding='utf-8'));manifest=json.loads((REC/'state_manifest.json').read_text(encoding='utf-8'))
actual={m.get_name() for m in mesh.get_editor_property('morph_targets')};clips={}
for role,entry in source['clips'].items():
    dest=base+'/Animations/V05/A_Receptionist_'+role+'_V05'
    clip=u.load_asset(dest) if LIB.does_asset_exist(dest) else LIB.duplicate_asset(entry['source'],dest)
    if not clip or not u.WeaponAnimationAuthoring.rebind_native_animation(clip,skeleton):raise RuntimeError('Cannot bind receptionist '+role)
    for name,values in curves[role].items():
        if name not in actual:raise RuntimeError('Required receptionist morph missing '+name)
        if u.AnimationLibrary.does_curve_exist(clip,name,u.RawCurveTrackTypes.RCT_FLOAT):u.AnimationLibrary.remove_curve(clip,name)
        u.AnimationLibrary.add_curve(clip,name)
        times=[min(i/manifest[role]['fps'],clip.get_play_length()) for i in range(len(values))]
        u.AnimationLibrary.add_float_curve_keys(clip,name,times,values);u.AnimationLibrary.set_curve_meta_data_morph_target(skeleton,name,True)
    clip.set_editor_property('rate_scale',entry['rate_scale']);clip.set_preview_skeletal_mesh(mesh)
    LIB.set_metadata_tag(clip,'StaffStateSource',entry['source']);LIB.set_metadata_tag(clip,'StaffRevision','M04 V05 native state and anatomical cloth; V04 core motion remains')
    save(clip);clips[role]=clip
save(skeleton)
cdo.set_editor_property('visual_mesh',mesh);cdo.get_editor_property('mesh').set_skeletal_mesh_asset(mesh)
combat=cdo.get_editor_property('combat');knock=cdo.get_editor_property('knockdown')
combat.set_editor_property('hit_clip',clips['hit']);combat.set_editor_property('dizzy_clip',clips['dizzy'])
for role in ['fall','get_up','prone_get_up']:knock.set_editor_property(role+'_clip',clips[role])
LIB.set_metadata_tag(bp,'StaffStateRevision','V05 clothed reactions, native state clips and curve-preserving transitions; V04 core clips retained')
u.BlueprintEditorLibrary.compile_blueprint(bp);save(bp)
report['characters']['Receptionist']={'mesh':mesh.get_path_name(),'clothing':meshes['clothing'].get_path_name(),'blueprint':bp.get_path_name(),'clips':{k:v.get_path_name() for k,v in clips.items()},'preserved_core_clips':source['characters']['Receptionist']['core_clips'],'new_cloth_shapes':sum(len(v) for v in curves.values())}
report['stage']='saved';record()
for who,folder in [('Security',SEC),('Receptionist',REC)]:
    delivery={'stage':'saved','runtime_tested':False,'rendered':False,**report['characters'][who]}
    (folder/'ue_delivery.json').write_text(json.dumps(delivery,indent=2),encoding='utf-8')
print('FACELESS_STAFF_STATES_SAVED '+json.dumps({'saved_count':len(report['saved']),'output':str(ROOT/'ue_delivery.json')}),flush=True)