"""Import native FPS traversal candidates; never modify the source weapon assets."""
import unreal,json
from pathlib import Path
out=Path('D:/FPS3D/FPSGAME/SourceAssets/GASPTraversal20260910/Native')
dest='/Game/Movement/Traversal/Native'
weapon=unreal.load_asset('/Game/Weapons/M4HK416Replica/SK_M4_FoldingSights_HK416')
assert weapon
def task(file,opt):
 t=unreal.AssetImportTask();t.filename=str(out/file);t.destination_path=dest;t.destination_name=Path(file).stem
 t.automated=True;t.replace_existing=True;t.save=True;t.options=opt
 unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([t])
 a=unreal.load_asset(dest+'/'+Path(file).stem);assert a,file
 return a
opt=unreal.FbxImportUI();opt.automated_import_should_detect_type=False
opt.mesh_type_to_import=unreal.FBXImportType.FBXIT_SKELETAL_MESH;opt.import_as_skeletal=True
opt.import_mesh=True;opt.import_animations=False;opt.import_materials=False;opt.import_textures=False
opt.create_physics_asset=False;opt.skeleton=weapon.skeleton
mesh=task('SK_TraversalArms.fbx',opt)
bindings={str(s.material_slot_name):s.material_interface for s in weapon.get_editor_property('materials')}
slots=mesh.get_editor_property('materials')
for i,s in enumerate(slots):
 assert str(s.material_slot_name) in bindings,str(s.material_slot_name)
 s.material_interface=bindings[str(s.material_slot_name)];slots[i]=s
mesh.set_editor_property('materials',slots);unreal.EditorAssetLibrary.save_loaded_asset(mesh,False)
report={'mesh':mesh.get_path_name(),'clips':{}}
for clip in ['Vault','Mantle','Climb']:
 opt=unreal.FbxImportUI();opt.automated_import_should_detect_type=False
 opt.mesh_type_to_import=unreal.FBXImportType.FBXIT_ANIMATION;opt.skeleton=weapon.skeleton
 opt.import_mesh=False;opt.import_animations=True;opt.import_materials=False;opt.import_textures=False
 opt.anim_sequence_import_data.set_editor_property('use_default_sample_rate',False)
 opt.anim_sequence_import_data.set_editor_property('custom_sample_rate',60)
 a=task('A_Traversal_'+clip+'.fbx',opt)
 a.set_editor_property('bone_compression_settings',unreal.load_asset('/Game/Weapons/M4InfimaRigV4/BC_M4Viewmodel'))
 unreal.EditorAssetLibrary.save_loaded_asset(a,False)
 report['clips'][clip]={'path':a.get_path_name(),'duration':a.get_play_length()}
exec((Path(__file__).parent/'apply_traversal_bounds.py').read_text(encoding='utf-8'))
report['runtime_mesh']=m.get_path_name()
(out/'import.json').write_text(json.dumps(report,indent=2))
unreal.log('TRAVERSAL_NATIVE_IMPORT_PASS '+json.dumps(report))
