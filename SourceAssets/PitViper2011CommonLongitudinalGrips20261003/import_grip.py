"""Save only the shared 2011 grip surface at its existing runtime asset path."""
import json,hashlib,shutil,re
from pathlib import Path
import unreal as u
O=Path(__file__).parent;P=O.parents[1];auth=json.loads((O/'authoring.json').read_text(encoding='utf8'))
PATH=auth['mesh'];E=u.EditorAssetLibrary
if Path(u.Paths.project_dir()).resolve()!=P.resolve():raise RuntimeError('Wrong production project')
dirty={p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
if PATH in dirty:raise RuntimeError('Preserve unsaved common grip surface')
mesh=u.load_asset(PATH)
if not mesh:raise RuntimeError('Expected existing installed common grip surface')
canon=lambda name:re.sub(r'[._]\d{3}$','',str(name))
materials={canon(slot.material_slot_name):slot.material_interface for slot in mesh.static_materials}
source=P/'Content'/(PATH.removeprefix('/Game/')+'.uasset');backup=O/'Before/Content'/(PATH.removeprefix('/Game/')+'.uasset')
if source.exists() and not backup.exists():backup.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,backup)
flag='Interchange.FeatureFlags.Import.FBX';oldflag=u.SystemLibrary.get_console_variable_int_value(flag)
u.SystemLibrary.execute_console_command(None,flag+' 0')
signature=hashlib.sha256(Path(auth['fbx']).read_bytes()).hexdigest()
try:
    opt=u.FbxImportUI();opt.automated_import_should_detect_type=False;opt.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
    opt.import_mesh=True;opt.import_materials=False;opt.import_textures=False;opt.import_animations=False;opt.override_full_name=True
    settings=opt.static_mesh_import_data;settings.combine_meshes=True;settings.auto_generate_collision=False
    settings.generate_lightmap_u_vs=False;settings.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS
    task=u.AssetImportTask();task.filename=auth['fbx'];task.destination_path=PATH.rsplit('/',1)[0];task.destination_name=auth['name']
    task.automated=True;task.replace_existing=True;task.replace_existing_settings=True;task.save=False;task.options=opt;task.factory=u.FbxFactory()
    u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task]);mesh=u.load_asset(PATH)
    if not mesh:raise RuntimeError('Common grip import failed')
    slots=list(mesh.static_materials)
    for i,slot in enumerate(slots):slot.material_interface=materials[canon(slot.material_slot_name)];slots[i]=slot
    mesh.set_editor_property('static_materials',slots)
    editor=u.get_editor_subsystem(u.StaticMeshEditorSubsystem)
    if editor:
        build=editor.get_lod_build_settings(mesh,0);build.use_full_precision_u_vs=True;editor.set_lod_build_settings(mesh,0,build)
    E.set_metadata_tag(mesh,'GripSurfaceFrame',auth['frame']);E.set_metadata_tag(mesh,'GripSurfaceSource',auth['blend'])
    E.set_metadata_tag(mesh,'GripSurfaceRevision',auth['revision']);E.set_metadata_tag(mesh,'SourceAttribution',auth['provenance'])
    E.set_metadata_tag(mesh,'PitViperAttachmentSourceSHA256',signature)
    if not u.EditorLoadingAndSavingUtils.save_packages([mesh.get_outermost()],False):raise RuntimeError('Common grip save failed')
finally:u.SystemLibrary.execute_console_command(None,flag+' '+str(oldflag))
receipt={'status':'imported_and_saved','saved':[mesh.get_path_name()],'mesh':mesh.get_path_name(),
    'fbx':auth['fbx'],'fbx_sha256':signature,'revision':auth['revision'],'affected_parts':auth['affected_parts'],
    'materials':{str(s.material_slot_name):s.material_interface.get_path_name() for s in slots},
    'uv_mapping':auth['uv_mapping'],'catalog_bindings_changed':False,'textures_changed':False,'stats_changed':False,
    'shared_icons_regenerated':False,'vip_changed':False,'native_build_required':False,'game_tested':False,'acceptance_rendered':False}
(O/'import_receipt.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf8')
legacy=O.parent/'PitViper2011Attachments20261002/import_receipt.json'
if legacy.exists():
    record=json.loads(legacy.read_text(encoding='utf8'));record['common_longitudinal_revision']=receipt
    record['meshes']['GripSurface'].update(asset=receipt['mesh'],source=auth['fbx'],materials=receipt['materials'],sockets_cm={})
    legacy.write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf8')
print('PIT_VIPER_COMMON_LONGITUDINAL_GRIPS_IMPORTED_AND_SAVED',flush=True)
