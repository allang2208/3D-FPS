"""Import and save authored single-action clips and shared non-fire profiles."""
import unreal as u,json
from pathlib import Path
O=Path(__file__).parent;E=u.EditorAssetLibrary;A=u.AssetToolsHelpers.get_asset_tools()
# Asset saving is unavailable during an existing PIE session. Preserve it.
if u.EditorLevelLibrary.get_game_world():raise RuntimeError('Existing game/PIE session is active; preserve it and import after it ends')
root='/Game/Weapons/RSH12/SingleAction20261003'
skeleton=u.load_asset('/Game/Weapons/DanWesson715/Integrated20260913/SK_DW715_Manny_Skeleton')
compression=u.load_asset('/Game/Weapons/M4InfimaRigV4/BC_M4Viewmodel')
if not skeleton:raise RuntimeError('Installed native skeleton is unavailable')
receipt=dict(complete=False,saved=[],clips=[],profiles=[],testing='Not performed; user testing')
def record():(O/'import_receipt.json').write_text(json.dumps(receipt,indent=2),encoding='utf8')
def save(a):
    if not E.save_loaded_asset(a,False):raise RuntimeError('Asset save failed '+a.get_path_name())
    receipt['saved'].append(a.get_path_name());record()
flag='Interchange.FeatureFlags.Import.FBX';old=u.SystemLibrary.get_console_variable_int_value(flag)
u.SystemLibrary.execute_console_command(None,flag+' 0')
try:
    for family in ('single','r','l'):
        recipe=json.loads((O/family/'authoring.json').read_text(encoding='utf8'))
        for job in recipe['clips']:
            options=u.FbxImportUI();options.automated_import_should_detect_type=False
            options.mesh_type_to_import=u.FBXImportType.FBXIT_ANIMATION
            options.import_mesh=False;options.import_animations=True;options.skeleton=skeleton
            options.import_materials=False;options.import_textures=False
            options.anim_sequence_import_data.set_editor_property('use_default_sample_rate',False)
            options.anim_sequence_import_data.set_editor_property('custom_sample_rate',120)
            task=u.AssetImportTask();task.filename=str(O/family/job['file']);task.destination_path=job['destination']
            task.destination_name=job['name'];task.automated=True;task.replace_existing=True;task.save=False
            task.options=options;task.factory=u.FbxFactory();A.import_asset_tasks([task])
            clip=u.load_asset(job['destination']+'/'+job['name'])
            if not clip:raise RuntimeError('Animation import failed '+job['name'])
            clip.set_editor_property('bone_compression_settings',compression)
            E.set_metadata_tag(clip,'AuthoringSource','RSH12SingleAction20261003; native V7 arms; original Medji RSH12; reference BV1pj411e7Jw 102-104s; motion authored locally, no video mesh or audio extraction')
            save(clip);receipt['clips'].append(dict(family=family,kind=job['kind'],asset=clip.get_path_name(),duration=clip.get_play_length(),target_skeleton=skeleton.get_path_name()))
        name='DA_RSH12_'+('' if family=='single' else family+'_')+'base';path=root+'/Profiles/'+name
        profile=u.load_asset(path)
        if not profile:
            f=u.DataAssetFactory();f.set_editor_property('data_asset_class',u.WeaponGripProfile)
            profile=A.create_asset(name,root+'/Profiles',u.WeaponGripProfile,f)
        data=json.loads((O/family/'profile.json').read_text(encoding='utf8'))
        if not profile.set_shared_clips_from_json(json.dumps(data)):raise RuntimeError('Cannot publish '+path)
        E.set_metadata_tag(profile,'AuthoringSource','RSH12SingleAction20261003; shared 715 non-fire clips, cocked ready pose; independent fire source clocks')
        save(profile);receipt['profiles'].append(dict(family=family,asset=profile.get_path_name(),shared_non_fire_clips=len(data['clips'])-len(recipe['clips']),authored_fire_clips=len(recipe['clips'])))
        record();print('RSH12_SINGLE_ACTION_FAMILY_SAVED',family,flush=True)
finally:u.SystemLibrary.execute_console_command(None,flag+' '+str(old))
receipt['complete']=True;record();print('RSH12_SINGLE_ACTION_ASSETS_SAVED',len(receipt['saved']),flush=True)
