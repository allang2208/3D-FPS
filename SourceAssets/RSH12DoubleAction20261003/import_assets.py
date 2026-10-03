"""Save only the new RSH double-action packages; preserve loaded legacy assets."""
import unreal as u, json
from pathlib import Path
O=Path(__file__).parent;P=O.parents[1]
E=u.EditorAssetLibrary;A=u.AssetToolsHelpers.get_asset_tools()
if Path(u.Paths.project_dir()).resolve()!=P.resolve():raise RuntimeError('Unexpected project')
if u.EditorLevelLibrary.get_game_world():raise RuntimeError('Existing PIE/game is active; preserve it and defer saving')
root='/Game/Weapons/RSH12/DoubleAction20261003'
skeleton=u.load_asset('/Game/Weapons/DanWesson715/Integrated20260913/SK_DW715_Manny_Skeleton')
compression=u.load_asset('/Game/Weapons/M4InfimaRigV4/BC_M4Viewmodel')
metal=u.load_asset('/Game/Weapons/RSH12/Materials/MI_RSH12_SourcePBR')
bare=u.load_asset('/Game/Characters/ModularOutfit20260924/BarePalmV7/Materials/MI_BareNative_Default')
receipt=dict(revision='double-action-v1',complete=False,saved=[],meshes=[],animations=[],audio=[],runtime_tested=False)
def record():(O/'import_receipt.json').write_text(json.dumps(receipt,indent=2),encoding='utf8')
def save(a):
    if not E.save_loaded_asset(a,False):raise RuntimeError('Save failed '+a.get_path_name())
    receipt['saved'].append(a.get_path_name());record()
polymer=u.load_asset(root+'/Materials/M_RSH12_Loader')
if not polymer:
    polymer=A.create_asset('M_RSH12_Loader',root+'/Materials',u.Material,u.MaterialFactoryNew())
    polymer.set_editor_property('two_sided',False)
    polymer.set_editor_property('used_with_skeletal_mesh',True)
    lib=u.MaterialEditingLibrary
    color=lib.create_material_expression(polymer,u.MaterialExpressionConstant3Vector,-300,0)
    color.set_editor_property('constant',u.LinearColor(.023,.026,.030,1))
    lib.connect_material_property(color,'',u.MaterialProperty.MP_BASE_COLOR)
    rough=lib.create_material_expression(polymer,u.MaterialExpressionConstant,-300,140)
    rough.set_editor_property('r',.62);lib.connect_material_property(rough,'',u.MaterialProperty.MP_ROUGHNESS)
    lib.recompile_material(polymer)
save(polymer)
flag='Interchange.FeatureFlags.Import.FBX';old=u.SystemLibrary.get_console_variable_int_value(flag)
u.SystemLibrary.execute_console_command(None,flag+' 0')
outfit_path=P/'Content/ColdSteelData/modular_outfits.json'
original=outfit_path.read_text(encoding='utf-8-sig');outfits=json.loads(original)
try:
    for family in ('single','r','l'):
        src=O/family;recipe=json.loads((src/'authoring.json').read_text(encoding='utf8'))
        name=Path(recipe['mesh']).stem;dest=root+'/'+family
        opts=u.FbxImportUI();opts.automated_import_should_detect_type=False
        opts.mesh_type_to_import=u.FBXImportType.FBXIT_SKELETAL_MESH
        opts.import_as_skeletal=True;opts.import_mesh=True;opts.import_animations=False
        opts.import_materials=False;opts.import_textures=False;opts.create_physics_asset=False;opts.skeleton=skeleton
        opts.skeletal_mesh_import_data.set_editor_property('update_skeleton_reference_pose',False)
        opts.skeletal_mesh_import_data.set_editor_property('use_t0_as_ref_pose',False)
        opts.skeletal_mesh_import_data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS
        task=u.AssetImportTask();task.filename=str(src/recipe['mesh']);task.destination_path=dest;task.destination_name=name
        task.automated=True;task.replace_existing=True;task.replace_existing_settings=True;task.save=False;task.options=opts;task.factory=u.FbxFactory()
        A.import_asset_tasks([task]);mesh=u.load_asset(dest+'/'+name)
        if not mesh:raise RuntimeError('Mesh import failed '+name)
        slots=list(mesh.materials);arms=[]
        for i,slot in enumerate(slots):
            tag=str(slot.material_slot_name);arm='Manny' in tag
            slot.material_interface=bare if arm else polymer if 'LoaderPolymer' in tag else metal
            if arm:arms.append(i)
            slots[i]=slot
        mesh.set_editor_property('materials',slots);mesh.set_editor_property('physics_asset',None)
        E.set_metadata_tag(mesh,'RSHRevision','DoubleAction20261003 v1; V7 hands; five-chamber fitted Medji mesh; locally authored five-round loader')
        save(mesh);receipt['meshes'].append(mesh.get_path_name())
        oldpath='/Game/Weapons/RSH12/'+('SK_RSH12_Manny.SK_RSH12_Manny' if family=='single' else 'Dual/'+family+'/SK_Dual_RSH12_'+family+'.SK_Dual_RSH12_'+family)
        profile=dict(outfits['profiles'][oldpath]);profile['hide_source_materials']=arms
        outfits['profiles'][mesh.get_path_name()]=profile
        for job in recipe['clips']:
            opts=u.FbxImportUI();opts.automated_import_should_detect_type=False
            opts.mesh_type_to_import=u.FBXImportType.FBXIT_ANIMATION;opts.import_mesh=False;opts.import_animations=True;opts.skeleton=skeleton
            opts.import_materials=False;opts.import_textures=False
            opts.anim_sequence_import_data.set_editor_property('use_default_sample_rate',False)
            opts.anim_sequence_import_data.set_editor_property('custom_sample_rate',120)
            task=u.AssetImportTask();task.filename=str(src/job['file']);task.destination_path=job['destination'];task.destination_name=job['name']
            task.automated=True;task.replace_existing=True;task.save=False;task.options=opts;task.factory=u.FbxFactory()
            A.import_asset_tasks([task]);clip=u.load_asset(job['destination']+'/'+job['name'])
            if not clip:raise RuntimeError('Animation import failed '+job['name'])
            clip.set_editor_property('bone_compression_settings',compression)
            E.set_metadata_tag(clip,'AuthoringSource','RSH12DoubleAction20261003; BV1vh4HejEUF 0-22s motion reference; V7 native skeleton; local authoring; not visually accepted')
            save(clip);receipt['animations'].append(dict(asset=clip.get_path_name(),kind=job['kind'],duration=clip.get_play_length()))
        name='DA_RSH12_'+('' if family=='single' else family+'_')+'base'
        profile=u.load_asset(root+'/Profiles/'+name)
        if not profile:
            factory=u.DataAssetFactory();factory.set_editor_property('data_asset_class',u.WeaponGripProfile)
            profile=A.create_asset(name,root+'/Profiles',u.WeaponGripProfile,factory)
        if not profile.set_shared_clips_from_json((src/'profile.json').read_text(encoding='utf8')):raise RuntimeError('Profile save rejected '+name)
        save(profile)
        print('RSH12_DA_FAMILY_IMPORTED',family,flush=True)
finally:u.SystemLibrary.execute_console_command(None,flag+' '+str(old))
audio=json.loads((O/'Audio/manifest.json').read_text(encoding='utf8'))
for entry in audio['clips']:
    name=Path(entry['file']).stem
    task=u.AssetImportTask();task.filename=str(O/'Audio'/entry['file']);task.destination_path=root+'/Audio';task.destination_name=name
    task.automated=True;task.replace_existing=True;task.save=False;task.factory=u.SoundFactory()
    A.import_asset_tasks([task]);wave=u.load_asset(root+'/Audio/'+name)
    if not wave:raise RuntimeError('Audio import failed '+name)
    wave.set_sound_asset_compression_type(u.SoundAssetCompressionType.PCM)
    wave.set_editor_property('loading_behavior',u.SoundWaveLoadingBehavior.FORCE_INLINE)
    E.set_metadata_tag(wave,'Source','User-selected BV1vh4HejEUF mixed reference; locally cropped/filtered; no redistribution grant established')
    save(wave);receipt['audio'].append(wave.get_path_name())
if outfit_path.read_text(encoding='utf-8-sig')!=original:raise RuntimeError('Outfit catalog changed while importing; preserve and merge new RSH entries')
outfit_path.write_text(json.dumps(outfits,ensure_ascii=False,indent=2),encoding='utf8')
receipt['complete']=True;record()
print('RSH12_DOUBLE_ACTION_ASSETS_SAVED',len(receipt['saved']),flush=True)
