"""Save dedicated Bow rig/actions, a separated riser, and the authored arrow.

Uses only stock UE asset types, and can run through the existing locked Python
bridge or an unattended commandlet. Never starts PIE or renders.
"""
import json
from pathlib import Path
import unreal as u
P=Path(__file__).parent
DEST='/Game/Weapons/DarkBow20260925/ContactV9'
E=u.EditorAssetLibrary;A=u.AssetToolsHelpers.get_asset_tools();G=u.GeometryScript_AssetUtils
INFO=json.loads((P/'authoring.json').read_text())
receipt={'saved':{},'runtime_tested':False}
receipt_file=P/'import_receipt.json'
if receipt_file.exists():receipt=json.loads(receipt_file.read_text())
# Every output is in this new candidate directory. Running play may continue:
# no active gameplay asset or class is overwritten by this import batch.
dirty=[p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages() if p.get_name().startswith(DEST+'/')]
if dirty:raise RuntimeError('Preserve unsaved Bow candidate edits: '+str(dirty))
def save(asset):
    if not E.save_loaded_asset(asset,False):raise RuntimeError('Save failed: '+asset.get_path_name())
    receipt['saved'][asset.get_name()]=asset.get_path_name()
    receipt_file.write_text(json.dumps(receipt,indent=2),encoding='utf-8')
def import_fbx(name,kind,skeleton=None):
    if name in receipt['saved']:return u.load_asset(receipt['saved'][name])
    if E.does_asset_exist(DEST+'/'+name):raise RuntimeError('Preserve pre-existing unowned asset '+name)
    opt=u.FbxImportUI();opt.automated_import_should_detect_type=False
    opt.mesh_type_to_import=kind;opt.import_materials=False;opt.import_textures=False
    opt.import_mesh=kind!=u.FBXImportType.FBXIT_ANIMATION
    opt.import_animations=kind==u.FBXImportType.FBXIT_ANIMATION
    if skeleton:opt.skeleton=skeleton
    if kind==u.FBXImportType.FBXIT_ANIMATION:
        opt.anim_sequence_import_data.set_editor_property('use_default_sample_rate',False)
        opt.anim_sequence_import_data.set_editor_property('custom_sample_rate',INFO['fps'])
        opt.anim_sequence_import_data.set_editor_property('remove_redundant_keys',False)
    if kind==u.FBXImportType.FBXIT_SKELETAL_MESH:
        opt.import_as_skeletal=True
        opt.create_physics_asset=False
        opt.skeletal_mesh_import_data.set_editor_property('use_t0_as_ref_pose',True)
        opt.skeletal_mesh_import_data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS
    if kind==u.FBXImportType.FBXIT_STATIC_MESH:
        opt.static_mesh_import_data.combine_meshes=True
        opt.static_mesh_import_data.auto_generate_collision=False
    task=u.AssetImportTask();task.filename=str(P/'Export'/(name+'.fbx'))
    task.destination_path=DEST;task.destination_name=name;task.automated=True;task.replace_existing=False
    task.options=opt;task.save=False;A.import_asset_tasks([task])
    asset=u.load_asset(DEST+'/'+name)
    if not asset:raise RuntimeError('Import did not produce '+name)
    return asset
u.SystemLibrary.execute_console_command(None,'Interchange.FeatureFlags.Import.FBX 0')
original=u.load_asset('/Game/Weapons/DarkBow20260925/ArmsV4/SK_Bow_BareArmsV7')
if not original:raise RuntimeError('ArmsV4 reference mesh missing')
mesh=import_fbx('SK_Bow_BareArmsV7',u.FBXImportType.FBXIT_SKELETAL_MESH,original.skeleton)
skin='/Game/Characters/ModularOutfit20260924/BarePalmV7/Materials/MI_BareFamily_'
arm=u.load_asset(skin+'Arms');hand=u.load_asset(skin+'Hands')
if not arm or not hand:raise RuntimeError('Accepted V7 skin materials missing')
slots=list(mesh.materials)
for s in slots:s.material_interface=hand if 'Hand' in str(s.material_slot_name) else arm
mesh.materials=slots
mesh.set_editor_property('physics_asset',None)
S=u.get_editor_subsystem(u.SkeletalMeshEditorSubsystem)
build=S.get_lod_build_settings(mesh,0);build.use_full_precision_u_vs=True;S.set_lod_build_settings(mesh,0,build)
# Arms pass beyond the reference A-pose during a draw; save generous authored bounds.
mesh.set_editor_property('positive_bounds_extension',u.Vector(100,40,35))
mesh.set_editor_property('negative_bounds_extension',u.Vector(40,40,25))
save(mesh)
for role in INFO['durations']:
    name='A_Bow_'+role
    if name in receipt['saved']:continue
    asset=import_fbx(name,u.FBXImportType.FBXIT_ANIMATION,mesh.skeleton)
    compression=u.load_asset('/Game/Weapons/M4InfimaRigV4/BC_M4Viewmodel')
    if compression:asset.set_editor_property('bone_compression_settings',compression)
    asset.set_preview_skeletal_mesh(mesh);save(asset)


print('BOW_V9_SURFACE_AND_CONTACT_ACTIONS_SAVED',len(receipt['saved']))
