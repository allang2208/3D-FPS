"""Import the independent revision and apply it to the current A762 ext-mag slot."""
import hashlib,json,shutil
from pathlib import Path
import unreal as u
O=Path(__file__).parent;P=Path(u.Paths.project_dir()).resolve()
if P!=Path('D:/FPS3D/FPSGAME').resolve():raise RuntimeError('Wrong project')
E=u.EditorAssetLibrary;A=u.AssetToolsHelpers.get_asset_tools()
meta=json.loads((O/'Input/current.json').read_text())
TARGET=meta['path'].split('.')[0]
CANDIDATE='/Game/Weapons/A762/ExtendedMagazine20261001/SM_A762_ext_mag_Continuous07'
RP=O/'install_receipt.json'
receipt=json.loads(RP.read_text()) if RP.exists() else {'saved':{},'runtime_tested':False,'complete':False}
def record():RP.write_text(json.dumps(receipt,indent=2))
def disk(path):return P/'Content'/(path.removeprefix('/Game/')+'.uasset')
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
SOURCE_SHA=sha(O/'Exports/SM_A762_ext_mag_Continuous07.fbx')
def recipe(path):return 'continuous_mesh_copy_v1' if path==TARGET else 'keep_small_faces_preimport'
def save(asset):
    if not E.save_loaded_asset(asset,False):raise RuntimeError('Save failed '+asset.get_path_name())
def keep_small_faces(mesh):
    subsystem=u.get_editor_subsystem(u.StaticMeshEditorSubsystem) or u.new_object(u.StaticMeshEditorSubsystem)
    build=subsystem.get_lod_build_settings(mesh,0)
    build.set_editor_property('remove_degenerates',False)
    build.set_editor_property('recompute_normals',False)
    build.set_editor_property('recompute_tangents',True)
    subsystem.set_lod_build_settings(mesh,0,build)
commandlet='-run=pythonscript' in u.SystemLibrary.get_command_line().lower()
if not commandlet:
    editor=u.get_editor_subsystem(u.UnrealEditorSubsystem)
    if editor and editor.get_game_world():raise RuntimeError('PIE is active; retain source and wait before replacing the magazine')
    dirty={p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
    if dirty.intersection((TARGET,CANDIDATE)):raise RuntimeError('Unsaved target assets; preserve the editor state')
expected=receipt['saved'].get(TARGET,{}).get('sha256',meta['sha256'])
if sha(disk(TARGET))!=expected:raise RuntimeError('Current magazine changed since capture')
old=u.load_asset(TARGET)
bindings={str(s.material_slot_name):s.material_interface for s in old.static_materials}
if {k:v.get_path_name() for k,v in bindings.items()}!={s['name']:s['material'] for s in meta['slots']}:
    raise RuntimeError('Current material bindings changed; preserve Refine06/parallel work')
backup=O/'Before/SM_A762_ext_mag.uasset';backup.parent.mkdir(exist_ok=True)
if not backup.exists():shutil.copy2(disk(TARGET),backup)
receipt['backup']=str(backup);record()
flag='Interchange.FeatureFlags.Import.FBX';prior=u.SystemLibrary.get_console_variable_int_value(flag)
u.SystemLibrary.execute_console_command(None,flag+' 0')
try:
    for path in ((CANDIDATE,) if globals().get('CANDIDATE_ONLY') else (CANDIDATE,TARGET)):
        previous=receipt['saved'].get(path,{})
        if previous.get('source_sha256')==SOURCE_SHA and previous.get('import_recipe')==recipe(path):continue
        if path==CANDIDATE and E.does_asset_exist(path) and path not in receipt['saved']:raise RuntimeError('Unowned candidate asset '+path)
        if path==TARGET:
            source=u.load_asset(CANDIDATE);mesh=old
            dm=u.DynamicMesh();read=u.GeometryScriptCopyMeshFromAssetOptions(apply_build_settings=False)
            lod=u.GeometryScriptMeshReadLOD(lod_type=u.GeometryScriptLODType.SOURCE_MODEL,lod_index=0)
            u.GeometryScript_AssetUtils.copy_mesh_from_static_mesh(source,dm,read,lod)
            count=dm.get_triangle_count()
            if count!=json.loads((O/'authoring.json').read_text())['triangles']:
                raise RuntimeError('Independent revision is missing faces: '+str(count))
            source_slots=source.static_materials
            opt=u.GeometryScriptCopyMeshToAssetOptions(replace_materials=True,
                new_materials=[bindings[str(s.material_slot_name)] for s in source_slots],
                new_material_slot_names=[s.material_slot_name for s in source_slots],
                enable_recompute_normals=False,enable_recompute_tangents=True,enable_remove_degenerates=False)
            result=u.GeometryScript_AssetUtils.copy_mesh_to_static_mesh(dm,mesh,opt,u.GeometryScriptMeshWriteLOD(lod_index=0))
            if result[-1]!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Full source geometry copy failed')
            mesh.get_editor_property('asset_import_data').scripted_add_filename(str(O/'Exports/SM_A762_ext_mag_Continuous07.fbx'),0,'Continuous07 complete source geometry')
        else:
            opt=u.FbxImportUI();opt.automated_import_should_detect_type=False
            opt.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
            opt.import_materials=False;opt.import_textures=False;opt.import_animations=False
            opt.set_editor_property('reset_to_fbx_on_material_conflict',True)
            d=opt.static_mesh_import_data;d.combine_meshes=True;d.auto_generate_collision=False
            d.generate_lightmap_u_vs=False;d.remove_degenerates=False
            d.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS
            d.normal_generation_method=u.FBXNormalGenerationMethod.MIKK_T_SPACE
            t=u.AssetImportTask();t.filename=str(O/'Exports/SM_A762_ext_mag_Continuous07.fbx')
            t.destination_path,t.destination_name=path.rsplit('/',1)
            t.options=opt;t.factory=u.FbxFactory();t.automated=True;t.replace_existing=path in receipt['saved']
            t.replace_existing_settings=True;t.save=False
            existing=u.load_asset(path) if E.does_asset_exist(path) else None
            if existing:keep_small_faces(existing)
            A.import_asset_tasks([t]);mesh=u.load_asset(path)
            if not mesh or not t.imported_object_paths:raise RuntimeError('FBX import failed '+path)
        slots=mesh.static_materials
        for i,s in enumerate(slots):
            key=str(s.material_slot_name)
            if key not in bindings:raise RuntimeError('Unexpected imported material slot '+key)
            s.material_interface=bindings[key];slots[i]=s
        mesh.set_editor_property('static_materials',slots)
        # Reimport can retain the asset's old build flags independently of
        # FbxStaticMeshImportData. Preserve the authored small rim/rib faces.
        keep_small_faces(mesh)
        E.set_metadata_tag(mesh,'A762ExtMagRevision','Continuous07-20261001')
        E.set_metadata_tag(mesh,'A762ExtMagSource','SourceAssets/A762ExtendedMagazine20261001/author.py')
        save(mesh)
        receipt['saved'][path]={'sha256':sha(disk(path)),'source_sha256':SOURCE_SHA,'import_recipe':recipe(path),
            'materials':{str(s.material_slot_name):s.material_interface.get_path_name() for s in slots}}
        record()
finally:u.SystemLibrary.execute_console_command(None,flag+' '+str(prior))
receipt['complete']=all(receipt['saved'].get(p,{}).get('source_sha256')==SOURCE_SHA and receipt['saved'].get(p,{}).get('import_recipe')==recipe(p) for p in (CANDIDATE,TARGET));record()
print('A762_SURFACE_EXTMAG_SAVED',CANDIDATE if globals().get('CANDIDATE_ONLY') else TARGET,flush=True)
