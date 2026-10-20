import json,copy,hashlib,runpy
from pathlib import Path
import unreal as u
O=Path(__file__).parent;P=Path(u.Paths.project_dir()).resolve()
ROOT='/Game/Weapons/SVCH/Refined20261018/R5';PATH=ROOT+'/SK_SVCH_Refined_R5'
E=u.EditorAssetLibrary;A=u.AssetToolsHelpers.get_asset_tools()
if E.does_asset_exist(PATH):raise RuntimeError('R5 already exists; preserve installed revision')
donor=u.load_asset('/Game/Weapons/SVCH/Refined20261018/SK_SVCH_Refined_R4')
options=u.FbxImportUI();options.automated_import_should_detect_type=False
options.mesh_type_to_import=u.FBXImportType.FBXIT_SKELETAL_MESH
options.import_as_skeletal=True;options.import_mesh=True;options.import_animations=False
options.import_materials=False;options.import_textures=False;options.create_physics_asset=False
options.skeleton=donor.skeleton
options.skeletal_mesh_import_data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS
task=u.AssetImportTask();task.filename=str(O/'SK_SVCH_Refined_R5.fbx');task.destination_path=ROOT
task.destination_name='SK_SVCH_Refined_R5';task.automated=True;task.save=False;task.options=options;task.factory=u.FbxFactory()
A.import_asset_tasks([task]);mesh=u.load_asset(PATH)
materials={str(s.material_slot_name):s.material_interface for s in donor.get_editor_property('materials')}
slots=list(mesh.get_editor_property('materials'))
if set(str(s.material_slot_name) for s in slots)!=set(materials):raise RuntimeError('Unexpected material identities')
for slot in slots:slot.material_interface=materials[str(slot.material_slot_name)]
mesh.set_editor_property('materials',slots)
editor=u.get_editor_subsystem(u.SkeletalMeshEditorSubsystem)
editor.set_lod_build_settings(mesh,0,editor.get_lod_build_settings(donor,0))
E.set_metadata_tag(mesh,'Attribution',E.get_metadata_tag(donor,'Attribution'))
E.set_metadata_tag(mesh,'SVCHRevision','R5 rounded sight and barrel mechanisms; native arm winding and corrective shapes')
if not E.save_loaded_asset(mesh,False):raise RuntimeError('R5 mesh save failed')
runpy.run_path(str(O.parent/'install_arm_correctives.py'),init_globals={
    'TARGET_MESH':PATH,'RECEIPT_PATH':O/'arm_correctives_receipt.json'})
factory=u.DataAssetFactory();factory.set_editor_property('data_asset_class',u.WeaponGripProfile)
profile=A.create_asset('DA_SVCH_BaseGrip',ROOT,u.WeaponGripProfile,factory)
if not profile.set_shared_clips_from_json((O/'shared_profile_r5.json').read_text()):raise RuntimeError('R5 profile creation failed')
if not E.save_loaded_asset(profile,False):raise RuntimeError('R5 profile save failed')
path=P/'Content/ColdSteelData/modular_outfits.json';data=json.loads(path.read_text(encoding='utf-8-sig'))
entry=copy.deepcopy(data['profiles'][donor.get_path_name()])
arms=[i for i,s in enumerate(slots) if str(s.material_slot_name).startswith('MI_Manny_')]
entry['hide_source_materials']=arms;entry['shirt_covers']=arms
data['profiles'][mesh.get_path_name()]=entry
path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
receipt={'saved':True,'mesh':mesh.get_path_name(),'profile':profile.get_path_name(),
    'materials':[str(s.material_slot_name) for s in slots],'arm_slots':arms,
    'fbx_sha256':hashlib.sha256((O/'SK_SVCH_Refined_R5.fbx').read_bytes()).hexdigest(),
    'profile_sha256':hashlib.sha256((O/'shared_profile_r5.json').read_bytes()).hexdigest()}
(O/'install_receipt.json').write_text(json.dumps(receipt,indent=1))
print('SVCH_R5_SAVED',json.dumps(receipt),flush=True)
