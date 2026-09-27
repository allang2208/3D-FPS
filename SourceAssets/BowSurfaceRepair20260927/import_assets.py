"""Reimport only the four repaired staves into their existing referenced assets."""
import unreal as u,json,hashlib,shutil
from pathlib import Path
P=Path(__file__).parent;ROOT=P.parents[1]
DEST='/Game/Weapons/DarkBow20260925/ElasticV15'
E=u.EditorAssetLibrary;A=u.AssetToolsHelpers.get_asset_tools()
if u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world():
    raise RuntimeError('Finish play mode before saving bow surfaces')
rows=json.loads((P/'authoring.json').read_text())['assets']
paths=[DEST+'/'+r['mesh'] for r in rows]
dirty=[x.get_name() for x in u.EditorLoadingAndSavingUtils.get_dirty_content_packages() if x.get_name() in paths]
if dirty:raise RuntimeError('Preserving unsaved bow packages '+str(dirty))
receipt=P/'import-receipt.json'
r=json.loads(receipt.read_text()) if receipt.exists() else {'saved':{},'hashes':{},'gameplay_tested':False}
u.SystemLibrary.execute_console_command(None,'Interchange.FeatureFlags.Import.FBX 0')
for row in rows:
    name=row['mesh'];path=DEST+'/'+name;source=P/'Export'/(name+'.fbx')
    digest=hashlib.sha256(source.read_bytes()).hexdigest()
    if r['hashes'].get(name)==digest:continue
    mesh=u.load_asset(path)
    if not isinstance(mesh,u.SkeletalMesh):raise RuntimeError('Expected retained skeletal mesh '+path)
    binary=ROOT/'Content/Weapons/DarkBow20260925/ElasticV15'/(name+'.uasset')
    backup=ROOT/'Saved/BowSurfaceRepair20260927/Before/Content/Weapons/DarkBow20260925/ElasticV15'/(name+'.uasset')
    backup.parent.mkdir(parents=True,exist_ok=True)
    if not backup.exists():shutil.copy2(binary,backup)
    skeleton=mesh.skeleton;slots=list(mesh.materials)
    opt=u.FbxImportUI();opt.automated_import_should_detect_type=False
    opt.mesh_type_to_import=u.FBXImportType.FBXIT_SKELETAL_MESH
    opt.import_mesh=True;opt.import_as_skeletal=True;opt.import_animations=False
    opt.import_materials=False;opt.import_textures=False;opt.create_physics_asset=False;opt.skeleton=skeleton
    opt.skeletal_mesh_import_data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS
    opt.skeletal_mesh_import_data.vertex_color_import_option=u.VertexColorImportOption.REPLACE
    opt.skeletal_mesh_import_data.set_editor_property('update_skeleton_reference_pose',False)
    opt.skeletal_mesh_import_data.set_editor_property('use_t0_as_ref_pose',False)
    task=u.AssetImportTask();task.filename=str(source);task.destination_path=DEST;task.destination_name=name
    task.automated=True;task.replace_existing=True;task.replace_existing_settings=True;task.save=False;task.options=opt
    A.import_asset_tasks([task]);mesh=u.load_asset(path)
    if not mesh or mesh.skeleton!=skeleton:raise RuntimeError('Retained skeleton changed for '+name)
    mesh.materials=slots
    if not E.save_loaded_asset(mesh,False):raise RuntimeError('Could not save repaired bow '+name)
    r['saved'][name]=mesh.get_path_name();r['hashes'][name]=digest
    receipt.write_text(json.dumps(r,indent=2),encoding='utf8')
print('BOW_OUTWARD_SURFACES_SAVED',json.dumps(r))
