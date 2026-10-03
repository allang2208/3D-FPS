"""Import one short batch through the project bridge, retaining runtime paths."""
import json,shutil
from pathlib import Path
import unreal as u
O=Path(__file__).parent;PROJECT=O.parents[1]
auth=json.loads((O/'authoring.json').read_text())
receipt=json.loads((O/'import_receipt.json').read_text()) if (O/'import_receipt.json').exists() else {}
jobs=[(k,v) for k,v in auth.items() if k not in receipt][:5]
dirty={p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
conflicts=[info['asset'] for key,info in jobs if info['asset'] in dirty]
if conflicts:raise RuntimeError('Target animations have unsaved edits: '+str(conflicts))
E=u.EditorAssetLibrary;A=u.AssetToolsHelpers.get_asset_tools()
flag='Interchange.FeatureFlags.Import.FBX';prior=u.SystemLibrary.get_console_variable_int_value(flag)
u.SystemLibrary.execute_console_command(None,flag+' 0')
try:
    for key,info in jobs:
        path=info['asset'];old=u.load_asset(path)
        if not old:raise RuntimeError('Missing installed action '+path)
        # The complete original package remains available for a scoped rollback.
        backup=O/'Before'/Path(path.removeprefix('/Game/')).with_suffix('.uasset')
        disk=PROJECT/'Content'/Path(path.removeprefix('/Game/')).with_suffix('.uasset')
        backup.parent.mkdir(parents=True,exist_ok=True)
        if not backup.exists():shutil.copy2(disk,backup)
        opts=u.FbxImportUI();opts.automated_import_should_detect_type=False
        opts.mesh_type_to_import=u.FBXImportType.FBXIT_ANIMATION
        opts.skeleton=old.get_editor_property('skeleton')
        opts.import_mesh=False;opts.import_animations=True;opts.import_materials=False;opts.import_textures=False
        opts.anim_sequence_import_data.set_editor_property('use_default_sample_rate',False)
        opts.anim_sequence_import_data.set_editor_property('custom_sample_rate',info['rate'])
        t=u.AssetImportTask();t.filename=info['fbx'];t.destination_path=path.rsplit('/',1)[0]
        t.destination_name=path.rsplit('/',1)[1];t.options=opts;t.factory=u.FbxFactory()
        t.automated=True;t.replace_existing=True;t.replace_existing_settings=False;t.save=False
        A.import_asset_tasks([t])
        if not t.imported_object_paths:raise RuntimeError('Animation import failed '+path)
        anim=u.load_asset(path)
        anim.set_editor_property('bone_compression_settings',u.load_asset(info['compression']))
        if not E.save_loaded_asset(anim,False):raise RuntimeError('Save failed '+path)
        receipt[key]={'asset':anim.get_path_name(),'source':info['fbx'],'saved':True,
                      'original_package':str(backup),'game_tested':False}
        (O/'import_receipt.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
finally:u.SystemLibrary.execute_console_command(None,flag+' '+str(prior))
print('MAGAZINE_GRASP_IMPORTED',len(jobs),'TOTAL',len(receipt),'OF',len(auth))
