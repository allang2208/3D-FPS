"""Import the authored M1911 into UE. Uses existing licensed material sources."""
import unreal as u,json
from pathlib import Path
O=Path(__file__).parent;P='/Game/Weapons/M1911/Integrated20260913';A=u.AssetToolsHelpers.get_asset_tools();L=u.MaterialEditingLibrary
ref=u.load_asset('/Game/Weapons/M4HK416Replica/SK_M4_FoldingSights_HK416')
bindings={str(s.material_slot_name):s.material_interface for s in ref.materials}
steel=u.load_asset('/Game/Weapons/AKMIntegration/SourceMatched/M_AKM_FabGunsteel')
wood=u.load_asset('/Game/Weapons/AKMIntegration/WalnutFab/M_AKM_SatinWalnut')
materials={}
for part,tint in [('Slide',(.12,.13,.145)),('Frame',(.055,.064,.075)),('Barrel',(.22,.23,.25)),('Mag',(.095,.10,.11)),('Ammo',(.40,.24,.065))]:
    name='MI_M1911_'+part;path=P+'/Materials/'+name
    m=u.load_asset(path) if u.EditorAssetLibrary.does_asset_exist(path) else A.create_asset(name,P+'/Materials',u.MaterialInstanceConstant,u.MaterialInstanceConstantFactoryNew())
    L.set_material_instance_parent(m,steel);L.set_material_instance_vector_parameter_value(m,'GunsteelTint',u.LinearColor(*tint,1));u.EditorAssetLibrary.save_loaded_asset(m,False);materials[part]=m
materials['Grip']=wood
opt=u.FbxImportUI();opt.automated_import_should_detect_type=False;opt.mesh_type_to_import=u.FBXImportType.FBXIT_SKELETAL_MESH
opt.import_as_skeletal=True;opt.import_mesh=True;opt.import_animations=False;opt.import_materials=False;opt.import_textures=False;opt.create_physics_asset=False
if u.EditorAssetLibrary.does_asset_exist(P+'/SK_M1911_Manny'):opt.skeleton=u.load_asset(P+'/SK_M1911_Manny').skeleton
opt.skeletal_mesh_import_data.set_editor_property('normal_import_method',u.FBXNormalImportMethod.FBXNIM_COMPUTE_NORMALS)
task=u.AssetImportTask();task.filename=str(O/'SK_M1911_Manny.fbx');task.destination_path=P;task.destination_name='SK_M1911_Manny';task.options=opt;task.automated=True;task.replace_existing=True;task.save=True
A.import_asset_tasks([task]);mesh=u.load_asset(P+'/SK_M1911_Manny')
slots=mesh.materials
for i,slot in enumerate(slots):
    name=str(slot.material_slot_name)
    material=materials[name.removeprefix('M_M1911_')] if name.startswith('M_M1911_') else bindings[name]
    if not material:raise RuntimeError('Missing source material for '+name)
    slot.material_interface=material;slots[i]=slot
mesh.set_editor_property('materials',slots);u.EditorAssetLibrary.save_loaded_asset(mesh,False)
clips={}
for source in sorted(O.glob('A_M1911_*.fbx')):
    opt=u.FbxImportUI();opt.automated_import_should_detect_type=False;opt.mesh_type_to_import=u.FBXImportType.FBXIT_ANIMATION;opt.import_mesh=False;opt.import_animations=True;opt.skeleton=mesh.skeleton
    opt.anim_sequence_import_data.set_editor_property('use_default_sample_rate',False);opt.anim_sequence_import_data.set_editor_property('custom_sample_rate',120)
    task=u.AssetImportTask();task.filename=str(source);task.destination_path=P+'/Animations';task.destination_name=source.stem;task.options=opt;task.automated=True;task.replace_existing=True;task.save=True
    A.import_asset_tasks([task]);clip=u.load_asset(P+'/Animations/'+source.stem)
    compression=u.load_asset('/Game/Weapons/M4InfimaRigV4/BC_M4Viewmodel')
    if compression:clip.set_editor_property('bone_compression_settings',compression)
    u.EditorAssetLibrary.save_loaded_asset(clip,False);clips[source.stem]=clip.get_path_name()
for source in (O/'Audio').glob('*.wav') if (O/'Audio').exists() else []:
    task=u.AssetImportTask();task.filename=str(source);task.destination_path=P+'/Audio';task.destination_name=source.stem;task.automated=True;task.replace_existing=True;task.save=True;A.import_asset_tasks([task])
(O/'import.json').write_text(json.dumps({'mesh':mesh.get_path_name(),'skeleton':mesh.skeleton.get_path_name(),'materials':{str(s.material_slot_name):s.material_interface.get_path_name() for s in slots},'animations':clips,'status':'imported; user testing pending'},indent=2))
u.log('M1911_IMPORT_COMPLETE')
