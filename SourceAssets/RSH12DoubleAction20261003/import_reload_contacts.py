"""Save the final gun-relative extraction-palm correction, after its bake ends."""
import unreal as u,json,hashlib
from pathlib import Path
O=Path(__file__).parent
if u.EditorLevelLibrary.get_game_world():raise RuntimeError('Preserve existing PIE')
receipt=json.loads((O/'import_receipt.json').read_text(encoding='utf8'))
recipe=json.loads((O/'single/authoring.json').read_text(encoding='utf8'))
A=u.AssetToolsHelpers.get_asset_tools();E=u.EditorAssetLibrary
skeleton=u.load_asset('/Game/Weapons/DanWesson715/Integrated20260913/SK_DW715_Manny_Skeleton')
compression=u.load_asset('/Game/Weapons/M4InfimaRigV4/BC_M4Viewmodel')
flag='Interchange.FeatureFlags.Import.FBX';old=u.SystemLibrary.get_console_variable_int_value(flag)
u.SystemLibrary.execute_console_command(None,flag+' 0')
saved=[]
try:
    for job in recipe['clips']:
        if job['kind'] not in ('reload','reload_empty'):continue
        source=O/'single'/job['file']
        opts=u.FbxImportUI();opts.automated_import_should_detect_type=False
        opts.mesh_type_to_import=u.FBXImportType.FBXIT_ANIMATION
        opts.import_mesh=False;opts.import_animations=True;opts.skeleton=skeleton
        opts.import_materials=False;opts.import_textures=False
        opts.anim_sequence_import_data.set_editor_property('use_default_sample_rate',False)
        opts.anim_sequence_import_data.set_editor_property('custom_sample_rate',120)
        task=u.AssetImportTask();task.filename=str(source);task.destination_path=job['destination'];task.destination_name=job['name']
        task.automated=True;task.replace_existing=True;task.save=False;task.options=opts;task.factory=u.FbxFactory()
        A.import_asset_tasks([task]);clip=u.load_asset(job['destination']+'/'+job['name'])
        clip.set_editor_property('bone_compression_settings',compression)
        if not E.save_loaded_asset(clip,False):raise RuntimeError('Save failed '+job['name'])
        saved.append(dict(asset=clip.get_path_name(),source_sha256=hashlib.sha256(source.read_bytes()).hexdigest()))
finally:u.SystemLibrary.execute_console_command(None,flag+' '+str(old))
receipt['final_reload_contact_revision']='gun-relative-extraction-palm'
receipt['final_reload_contact_saves']=saved
(O/'import_receipt.json').write_text(json.dumps(receipt,indent=2),encoding='utf8')
print('RSH12_FINAL_RELOAD_CONTACTS_SAVED',len(saved),flush=True)
