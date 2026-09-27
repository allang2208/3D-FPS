"""Import the elastic bow bodies and contact-preserving actions; save only owned assets."""
import hashlib, json
from pathlib import Path
import unreal as u
P=Path(__file__).parent
DEST='/Game/Weapons/DarkBow20260925/ElasticV15'
E=u.EditorAssetLibrary; A=u.AssetToolsHelpers.get_asset_tools(); L=u.MaterialEditingLibrary
receipt=P/'import-receipt.json'
r=json.loads(receipt.read_text()) if receipt.exists() else {'saved':{},'hashes':{},'gameplay_tested':False}
dirty=[x.get_name() for x in u.EditorLoadingAndSavingUtils.get_dirty_content_packages() if x.get_name().startswith(DEST+'/')]
if dirty: raise RuntimeError('Preserving unsaved assets: '+str(dirty))
def save(asset):
    if not E.save_loaded_asset(asset,False): raise RuntimeError('Save failed '+asset.get_path_name())
    r['saved'][asset.get_name()]=asset.get_path_name()
    receipt.write_text(json.dumps(r,indent=2),encoding='utf8')
def fresh(name):
    if name not in r['saved'] and E.does_asset_exist(DEST+'/'+name): raise RuntimeError('Unowned existing asset '+name)
def imported(name,opt):
    source=P/'Export'/(name+'.fbx'); digest=hashlib.sha256(source.read_bytes()).hexdigest()
    if name in r['saved'] and r['hashes'].get(name)==digest: return u.load_asset(r['saved'][name])
    fresh(name)
    t=u.AssetImportTask(); t.filename=str(source); t.destination_path=DEST; t.destination_name=name
    t.automated=True; t.replace_existing=name in r['saved']; t.save=False; t.options=opt
    A.import_asset_tasks([t]); asset=u.load_asset(DEST+'/'+name)
    if not asset: raise RuntimeError('Import failed '+name)
    r['hashes'][name]=digest
    return asset
u.SystemLibrary.execute_console_command(None,'Interchange.FeatureFlags.Import.FBX 0')
E.make_directory(DEST)
skeleton=u.load_asset(r['saved']['SK_Bow_Flex_Original_Skeleton']) if 'SK_Bow_Flex_Original_Skeleton' in r['saved'] else None
for role in ('Original','Swift','Heavy','Steady'):
    name='M_Bow_Flex_'+role
    if name in r['saved']: mat=u.load_asset(r['saved'][name])
    else:
        fresh(name)
        source=('/Game/Weapons/DarkBow20260925/WoodLongbow20260925/M_WoodLongbow_PBR' if role=='Original' else '/Game/Weapons/DarkBow20260925/BodyVariantsV14/M_Bow_Body_'+role)
        mat=A.duplicate_asset(name,DEST,u.load_asset(source))
        if not mat: raise RuntimeError('Cannot duplicate '+source)
        L.set_material_usage(mat,u.MaterialUsage.MATUSAGE_SKELETAL_MESH)
        L.recompile_material(mat); save(mat)
    opt=u.FbxImportUI(); opt.automated_import_should_detect_type=False
    opt.mesh_type_to_import=u.FBXImportType.FBXIT_SKELETAL_MESH
    opt.import_mesh=True; opt.import_as_skeletal=True; opt.import_animations=False
    opt.import_materials=False; opt.import_textures=False; opt.create_physics_asset=False
    if skeleton: opt.skeleton=skeleton
    data=opt.skeletal_mesh_import_data
    data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS
    data.vertex_color_import_option=u.VertexColorImportOption.REPLACE
    mesh=imported('SK_Bow_Flex_'+role,opt)
    slots=list(mesh.materials)
    for slot in slots: slot.material_interface=mat
    mesh.materials=slots; save(mesh)
    if skeleton is None: skeleton=mesh.skeleton
    save(skeleton)
arms=u.load_asset('/Game/Weapons/DarkBow20260925/ContactV9/SK_Bow_BareArmsV7')
compression=u.load_asset('/Game/Weapons/M4InfimaRigV4/BC_M4Viewmodel')
info=json.loads((P/'authoring.json').read_text())
for role in info['durations']:
    opt=u.FbxImportUI(); opt.automated_import_should_detect_type=False
    opt.mesh_type_to_import=u.FBXImportType.FBXIT_ANIMATION
    opt.import_mesh=False; opt.import_animations=True; opt.import_materials=False; opt.import_textures=False
    opt.skeleton=arms.skeleton
    opt.anim_sequence_import_data.set_editor_property('use_default_sample_rate',False)
    opt.anim_sequence_import_data.set_editor_property('custom_sample_rate',info['fps'])
    opt.anim_sequence_import_data.set_editor_property('remove_redundant_keys',False)
    clip=imported('A_Bow_'+role,opt)
    if compression: clip.set_editor_property('bone_compression_settings',compression)
    clip.set_preview_skeletal_mesh(arms); save(clip)
print('BOW_ELASTIC_V15_SAVED '+json.dumps(r))
