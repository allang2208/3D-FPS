"""Save only the five live fitted guards; the R4 blade and framed icon have separate publishers."""
from pathlib import Path
import json
import re
import runpy
import unreal as u

P=Path(__file__).resolve().parent
spec=json.loads((P/'guard-authoring.json').read_text(encoding='utf-8'))
catalog=json.loads((P.parents[2]/'Content/ColdSteelData/highland-claymore-modules.json').read_text(encoding='utf-8-sig'))
guards=catalog['slots']['guard']
folder='/Game/Weapons/HighlandClaymore20260922/RidgePiercer20260927/FittedGuardsR2'
E=u.EditorAssetLibrary
tool=u.AssetToolsHelpers.get_asset_tools()
static=u.get_editor_subsystem(u.StaticMeshEditorSubsystem) or u.new_object(u.StaticMeshEditorSubsystem)
editor=u.get_editor_subsystem(u.UnrealEditorSubsystem)
if editor and editor.get_game_world() is not None:
    raise RuntimeError('End play before installing the matched blade and guards.')
targets={folder+'/'+v['mesh'].split('.')[-1] for v in guards.values()}
occupied={p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}.intersection(targets)
if occupied:
    raise RuntimeError('Preserving unsaved targets: '+str(occupied))
E.make_directory(folder)
world=editor.get_editor_world() if editor else None
if world:
    u.SystemLibrary.execute_console_command(world,'Interchange.FeatureFlags.Import.FBX 0')
installed={}
for option,data in guards.items():
    original=data['mesh'].split('.')[0]
    name=original.rsplit('/',1)[1]
    dest=folder+'/'+name
    donor=u.load_asset(original)
    if not E.does_asset_exist(dest) and not E.duplicate_asset(original,dest):
        raise RuntimeError('Could not derive fitted guard: '+dest)
    bindings={str(slot.material_slot_name):slot.material_interface for slot in donor.static_materials}
    opts=u.FbxImportUI()
    opts.automated_import_should_detect_type=False
    opts.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
    opts.import_as_skeletal=False
    opts.import_materials=False
    opts.import_textures=False
    opts.import_animations=False
    opts.import_mesh=True
    cfg=opts.static_mesh_import_data
    cfg.combine_meshes=True
    cfg.auto_generate_collision=False
    cfg.generate_lightmap_u_vs=False
    cfg.convert_scene=True
    cfg.convert_scene_unit=True
    cfg.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS
    cfg.vertex_color_import_option=u.VertexColorImportOption.REPLACE
    task=u.AssetImportTask()
    task.filename=str(P/'Export'/(name+'.fbx'))
    task.destination_path=folder
    task.destination_name=name
    task.options=opts
    task.factory=u.FbxFactory()
    task.automated=True
    task.replace_existing=True
    task.replace_existing_settings=True
    task.save=False
    tool.import_asset_tasks([task])
    if not task.imported_object_paths:
        raise RuntimeError('Missing fitted FBX: '+name)
    mesh=u.load_asset(dest)
    slots=list(mesh.static_materials)
    for slot in slots:
        key=re.sub(r'[._][0-9]{3}$','',str(slot.material_slot_name))
        if key not in bindings:
            raise RuntimeError('Unmapped guard slot '+key+' in '+str(list(bindings)))
        slot.material_interface=bindings[key]
        slot.material_slot_name=key
    mesh.static_materials=slots
    static.set_lod_build_settings(mesh,0,static.get_lod_build_settings(donor,0))
    E.set_metadata_tag(mesh,'HighlandJunctionRevision',spec['junction_revision'])
    E.set_metadata_tag(mesh,'HighlandSource',task.filename)
    if not E.save_loaded_asset(mesh,False):
        raise RuntimeError('Could not save '+dest)
    installed[option]=mesh.get_path_name()
(P/'guard_installation.json').write_text(json.dumps(installed,indent=2),encoding='utf-8')
print('RIDGE_LOW_SEAT_PUBLISHED '+str(len(installed))+' guards')
