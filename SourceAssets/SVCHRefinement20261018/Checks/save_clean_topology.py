"""Import cleaned topology as a new revision, preserving R2 and materials."""
import json,copy,hashlib
from pathlib import Path
import unreal as u
O=Path(__file__).parent
P=Path(u.Paths.project_dir()).resolve()
ROOT='/Game/Weapons/SVCH/Refined20261018'
E=u.EditorAssetLibrary
old=u.load_asset(ROOT+'/SK_SVCH_Refined_'+globals().get('SOURCE_REVISION','R2'))
revision=globals().get('TARGET_REVISION','R3')
target=ROOT+'/SK_SVCH_Refined_'+revision
if E.does_asset_exist(target):raise RuntimeError(revision+' exists; do not overwrite')
options=u.FbxImportUI();options.automated_import_should_detect_type=False
options.mesh_type_to_import=u.FBXImportType.FBXIT_SKELETAL_MESH
options.import_as_skeletal=True;options.import_mesh=True;options.import_animations=False
options.import_materials=False;options.import_textures=False;options.create_physics_asset=False
options.skeleton=old.skeleton
options.skeletal_mesh_import_data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS
task=u.AssetImportTask();task.filename=str(O.parent/'Exports/SK_SVCH_Refined.fbx')
task.destination_path=ROOT;task.destination_name='SK_SVCH_Refined_'+revision
task.automated=True;task.save=False;task.options=options;task.factory=u.FbxFactory()
u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
mesh=u.load_asset(target)
materials={str(s.material_slot_name):s.material_interface for s in old.get_editor_property('materials')}
slots=list(mesh.get_editor_property('materials'))
if [str(s.material_slot_name) for s in slots]!=list(materials):raise RuntimeError('Material identities changed')
for slot in slots:slot.material_interface=materials[str(slot.material_slot_name)]
mesh.set_editor_property('materials',slots)
editor=u.get_editor_subsystem(u.SkeletalMeshEditorSubsystem)
build=editor.get_lod_build_settings(old,0)
editor.set_lod_build_settings(mesh,0,build)
E.set_metadata_tag(mesh,'Attribution',E.get_metadata_tag(old,'Attribution'))
E.set_metadata_tag(mesh,'SVCHTopology','Post-bevel weld, remove collapsed triangles, deterministic triangulation')
if revision=='R4':E.set_metadata_tag(mesh,'SVCHArmWinding','Restored native UE donor winding; UVs and normals follow source vertices')
if not E.save_loaded_asset(mesh,False):raise RuntimeError('Save failed')
path=P/'Content/ColdSteelData/modular_outfits.json'
data=json.loads(path.read_text(encoding='utf-8-sig'))
data['profiles'][mesh.get_path_name()]=copy.deepcopy(data['profiles'][old.get_path_name()])
path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
receipt={'saved':True,'mesh':mesh.get_path_name(),'preserved':old.get_path_name(),
         'fbx_sha256':hashlib.sha256((O.parent/'Exports/SK_SVCH_Refined.fbx').read_bytes()).hexdigest(),
         'materials':[str(s.material_slot_name) for s in slots]}
(O/globals().get('RECEIPT','topology_save.json')).write_text(json.dumps(receipt,indent=1))
print('SVCH_CLEAN_TOPOLOGY_SAVED',json.dumps(receipt),flush=True)
