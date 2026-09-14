"""Replace only the three sword guard animation assets."""
import unreal as u,json,shutil
from pathlib import Path
P=Path(__file__).parent;D='/Game/Weapons/AzureRunesword20260913'
content=P.parents[2]/'Content/Weapons/AzureRunesword20260913'
tools=u.AssetToolsHelpers.get_asset_tools();receipt=[]
u.SystemLibrary.execute_console_command(None,'Interchange.FeatureFlags.Import.FBX 0')
skeleton=u.load_asset(D+'/SK_AzureRunesword_Manny').skeleton
compression=u.load_asset('/Game/Weapons/M4InfimaRigV4/BC_M4Viewmodel')
for clip in ('Guard','GuardHit','GuardBreak'):
    name='A_RuneSword_'+clip
    current=content/(name+'.uasset');prior=P/'Before'/(name+'.uasset')
    if current.exists() and not prior.exists():
        prior.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(current,prior)
    opt=u.FbxImportUI();opt.automated_import_should_detect_type=False
    opt.mesh_type_to_import=u.FBXImportType.FBXIT_ANIMATION
    opt.import_mesh=False;opt.import_animations=True;opt.import_materials=False;opt.import_textures=False;opt.skeleton=skeleton
    opt.anim_sequence_import_data.set_editor_property('use_default_sample_rate',False)
    opt.anim_sequence_import_data.set_editor_property('custom_sample_rate',480)
    task=u.AssetImportTask();task.filename=str(P/'Export'/(name+'.fbx'))
    task.destination_path=D;task.destination_name=name;task.automated=True
    task.replace_existing=True;task.save=False;task.options=opt
    tools.import_asset_tasks([task]);seq=u.load_asset(D+'/'+name)
    if not task.imported_object_paths or not seq:raise RuntimeError('Animation import failed: '+name)
    if compression:seq.set_editor_property('bone_compression_settings',compression)
    if not u.EditorAssetLibrary.save_loaded_asset(seq):raise RuntimeError('Animation save failed: '+name)
    receipt.append({'source':task.filename,'asset':seq.get_path_name()})
(P/'import_receipt.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
u.log('RUNESWORD_V19_IMPORT_COMPLETE')
