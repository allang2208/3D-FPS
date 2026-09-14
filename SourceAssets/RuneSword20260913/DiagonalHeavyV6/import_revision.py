"""Install only the two revised attacks and their diagonal rift meshes."""
import unreal as u,json,shutil
from pathlib import Path
P=Path(__file__).parent;D='/Game/Weapons/AzureRunesword20260913';FX=D+'/WristRiftV3'
content=P.parents[2]/'Content/Weapons/AzureRunesword20260913';backup=P/'Before';backup.mkdir(exist_ok=True)
names=['A_RuneSword_Slash1','A_RuneSword_Slash2','WristRiftV3/SM_RuneRift_Slash1','WristRiftV3/SM_RuneRift_Slash2']
for name in names:
    file=content/(name+'.uasset');prior=backup/(name+'.uasset');prior.parent.mkdir(exist_ok=True,parents=True)
    if not prior.exists():shutil.copy2(file,prior)
tools=u.AssetToolsHelpers.get_asset_tools();receipt=[]
u.SystemLibrary.execute_console_command(None,'Interchange.FeatureFlags.Import.FBX 0')
skeleton=u.load_asset(D+'/SK_AzureRunesword_Manny').skeleton
compression=u.load_asset('/Game/Weapons/M4InfimaRigV4/BC_M4Viewmodel')

def task(name,opt,destination):
    t=u.AssetImportTask();t.filename=str(P/('Export/'+name+'.fbx'));t.destination_path=destination;t.destination_name=name
    t.automated=True;t.replace_existing=True;t.save=True;t.options=opt
    tools.import_asset_tasks([t]);asset=u.load_asset(destination+'/'+name)
    if not t.imported_object_paths or not asset:raise RuntimeError('Import failed: '+name)
    receipt.append({'source':t.filename,'asset':asset.get_path_name()});return asset

for clip in ['Slash1','Slash2']:
    opt=u.FbxImportUI();opt.automated_import_should_detect_type=False;opt.mesh_type_to_import=u.FBXImportType.FBXIT_ANIMATION
    opt.import_mesh=False;opt.import_animations=True;opt.import_materials=False;opt.import_textures=False;opt.skeleton=skeleton
    opt.anim_sequence_import_data.set_editor_property('use_default_sample_rate',False);opt.anim_sequence_import_data.set_editor_property('custom_sample_rate',240)
    seq=task('A_RuneSword_'+clip,opt,D)
    if compression:seq.set_editor_property('bone_compression_settings',compression)
    u.EditorAssetLibrary.save_loaded_asset(seq)
    opt=u.FbxImportUI();opt.automated_import_should_detect_type=False;opt.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
    opt.import_mesh=True;opt.import_as_skeletal=False;opt.import_materials=False;opt.import_textures=False
    opt.static_mesh_import_data.combine_meshes=True;opt.static_mesh_import_data.auto_generate_collision=False
    mesh=task('SM_RuneRift_'+clip,opt,FX);mesh.set_material(0,u.load_asset(FX+'/M_RuneRift'));u.EditorAssetLibrary.save_loaded_asset(mesh)
(P/'import_receipt.json').write_text(json.dumps(receipt,indent=2));u.log('RUNESWORD_V6_IMPORT_COMPLETE')
