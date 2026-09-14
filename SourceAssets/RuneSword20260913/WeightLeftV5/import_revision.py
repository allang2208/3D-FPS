"""Install left-face sword poses, held anticipation, forward sweeps and matching rifts."""
import unreal as u,json,shutil
from pathlib import Path
P=Path(__file__).parent;D='/Game/Weapons/AzureRunesword20260913';FX=D+'/WristRiftV3'
content=P.parents[2]/'Content/Weapons/AzureRunesword20260913';backup=P/'Before';backup.mkdir(exist_ok=True)
names=['SK_AzureRunesword_Manny','SK_AzureRunesword_Manny_Skeleton','SM_AzureRunesword']
clips=['Idle','Walk','Slash1','Slash2','Equip','Sprint'];names+=['A_RuneSword_'+n for n in clips]
names+=['WristRiftV3/SM_RuneRift_Slash1','WristRiftV3/SM_RuneRift_Slash2']
for name in names:
    file=content/(name+'.uasset');prior=backup/(name+'.uasset');prior.parent.mkdir(exist_ok=True,parents=True)
    if not prior.exists():shutil.copy2(file,prior)
tools=u.AssetToolsHelpers.get_asset_tools();receipt=[]
u.SystemLibrary.execute_console_command(None,'Interchange.FeatureFlags.Import.FBX 0')
def task(name,opt,destination=D):
    t=u.AssetImportTask();t.filename=str(P/('Export/'+name+'.fbx'));t.destination_path=destination;t.destination_name=name
    t.automated=True;t.replace_existing=True;t.save=True;t.options=opt
    tools.import_asset_tasks([t]);asset=u.load_asset(destination+'/'+name)
    if not t.imported_object_paths or not asset:raise RuntimeError('Import failed: '+name)
    receipt.append({'source':t.filename,'asset':asset.get_path_name()});return asset
mat=u.load_asset(D+'/M_AzureRunesword')
mat.set_editor_property('used_with_skeletal_mesh',True);u.EditorAssetLibrary.save_loaded_asset(mat)
old=u.load_asset(D+'/SK_AzureRunesword_Manny');skeleton=old.skeleton
bindings={str(s.material_slot_name):s.material_interface for s in old.get_editor_property('materials')}
opt=u.FbxImportUI();opt.automated_import_should_detect_type=False;opt.mesh_type_to_import=u.FBXImportType.FBXIT_SKELETAL_MESH
opt.import_as_skeletal=True;opt.import_mesh=True;opt.import_animations=False;opt.import_materials=False;opt.import_textures=False;opt.create_physics_asset=False;opt.skeleton=skeleton
sk=task('SK_AzureRunesword_Manny',opt);slots=sk.get_editor_property('materials')
for i,slot in enumerate(slots):slot.material_interface=bindings[str(slot.material_slot_name)];slots[i]=slot
sk.set_editor_property('materials',slots);sk.set_editor_property('positive_bounds_extension',u.Vector(120,120,120));sk.set_editor_property('negative_bounds_extension',u.Vector(120,120,120));u.EditorAssetLibrary.save_loaded_asset(sk)
compression=u.load_asset('/Game/Weapons/M4InfimaRigV4/BC_M4Viewmodel')
for name in clips:
    opt=u.FbxImportUI();opt.automated_import_should_detect_type=False;opt.mesh_type_to_import=u.FBXImportType.FBXIT_ANIMATION
    opt.import_mesh=False;opt.import_animations=True;opt.import_materials=False;opt.import_textures=False;opt.skeleton=skeleton
    opt.anim_sequence_import_data.set_editor_property('use_default_sample_rate',False);opt.anim_sequence_import_data.set_editor_property('custom_sample_rate',240)
    seq=task('A_RuneSword_'+name,opt)
    if compression:seq.set_editor_property('bone_compression_settings',compression)
    u.EditorAssetLibrary.save_loaded_asset(seq)
for name,destination,material in [('SM_AzureRunesword',D,mat),('SM_RuneRift_Slash1',FX,u.load_asset(FX+'/M_RuneRift')),('SM_RuneRift_Slash2',FX,u.load_asset(FX+'/M_RuneRift'))]:
    opt=u.FbxImportUI();opt.automated_import_should_detect_type=False;opt.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
    opt.import_mesh=True;opt.import_as_skeletal=False;opt.import_materials=False;opt.import_textures=False
    opt.static_mesh_import_data.combine_meshes=True;opt.static_mesh_import_data.auto_generate_collision=name=='SM_AzureRunesword'
    mesh=task(name,opt,destination);mesh.set_material(0,material);u.EditorAssetLibrary.save_loaded_asset(mesh)
(P/'import_receipt.json').write_text(json.dumps(receipt,indent=2));u.log('RUNESWORD_V5_IMPORT_COMPLETE')
