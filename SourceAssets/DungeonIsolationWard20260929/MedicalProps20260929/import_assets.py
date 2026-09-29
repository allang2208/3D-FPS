"""Import private ward derivatives and preserve the original imported props."""
import json,re,sys
from pathlib import Path
import unreal as u

ROOT=Path(__file__).resolve().parent
PROJECT=ROOT.parents[2]
if Path(u.Paths.project_dir()).resolve()!=PROJECT.resolve():raise RuntimeError('Wrong project')
editor=u.get_editor_subsystem(u.UnrealEditorSubsystem)
if editor and editor.get_game_world():raise RuntimeError('Preserve active PIE')
dirty={p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
def guard(asset):
    if asset.get_path_name().split('.')[0] in dirty:raise RuntimeError('Preserve unsaved asset '+asset.get_path_name())
sys.path.insert(0,str(PROJECT/'Tools/AssetPipeline'))
from dungeon_material_usage import ensure_material_usage
manifest=json.loads((ROOT/'manifest.json').read_text(encoding='utf-8'))
records=[]
for entry in manifest['objects']:
    base='/Game/Dungeons/IsolationWard20260929/Props'
    path=base+'/'+entry['name']
    if path in dirty:raise RuntimeError('Preserve unsaved ward prop '+path)
    source=u.load_asset(entry['source_mesh'])
    if not source:raise RuntimeError('Missing approved prop '+entry['source_mesh'])
    task=u.AssetImportTask();task.filename=entry['fbx'];task.destination_path=base;task.destination_name=entry['name']
    task.automated=True;task.replace_existing=True;task.replace_existing_settings=True;task.save=False
    options=u.FbxImportUI();options.automated_import_should_detect_type=False
    options.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
    options.import_materials=False;options.import_textures=False;options.import_as_skeletal=False
    data=options.static_mesh_import_data
    data.combine_meshes=True;data.convert_scene=True;data.convert_scene_unit=True
    data.transform_vertex_to_absolute=True;data.auto_generate_collision=False;data.one_convex_hull_per_ucx=True
    data.generate_lightmap_u_vs=False;data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS
    task.options=options;task.factory=u.FbxFactory()
    flag='Interchange.FeatureFlags.Import.FBX';previous=u.SystemLibrary.get_console_variable_int_value(flag)
    try:
        u.SystemLibrary.execute_console_command(None,flag+' 0')
        u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    finally:u.SystemLibrary.execute_console_command(None,flag+' '+str(previous))
    mesh=u.load_asset(path)
    if not mesh:raise RuntimeError('Prop import failed '+path)
    for index,slot in enumerate(mesh.get_editor_property('static_materials')):
        name=re.sub(r'[._][0-9]{3}$','',str(slot.material_slot_name))
        material=u.load_asset(entry['materials'][name])
        if not material:raise RuntimeError('Missing source material '+name)
        ensure_material_usage(material,guard);mesh.set_material(index,material)
    body=mesh.get_editor_property('body_setup')
    body.set_editor_property('collision_trace_flag',u.CollisionTraceFlag.CTF_USE_SIMPLE_AND_COMPLEX)
    instance=body.get_editor_property('default_instance')
    instance.set_editor_property('collision_profile_name',u.Name('BlockAll' if entry['blocking'] else 'NoCollision'))
    body.set_editor_property('default_instance',instance)
    hulls=len(body.get_editor_property('agg_geom').get_editor_property('convex_elems'))
    if hulls!=entry['collision_hulls']:raise RuntimeError('UCX import incomplete '+path)
    mesh.set_editor_property('nanite_settings',source.get_editor_property('nanite_settings').copy())
    if mesh.get_editor_property('nanite_settings').enabled and not u.PlazaInstanceTools.build_nanite_data(mesh):
        raise RuntimeError('Prop Nanite build failed '+path)
    u.EditorAssetLibrary.set_metadata_tag(mesh,'SourceCredit',entry['credit'])
    if not u.EditorAssetLibrary.save_loaded_asset(mesh,False):raise RuntimeError('Prop save failed '+path)
    records.append(dict(mesh=path,scale=entry['scale'],collision_hulls=hulls,blocking=entry['blocking']))
receipt=dict(stage='medical_prop_assets_saved',assets=records,tested=False,rendered=False)
(ROOT/'Receipts/assets.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
print('WARD_MEDICAL_ASSETS_SAVED',json.dumps(receipt),flush=True)
