"""Import this batch's eight assemblies, preserving authored simple collision and existing PBR materials."""
import hashlib,json,re,sys
from pathlib import Path
import unreal as u
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parents[1]
BASE='/Game/Dungeons/FacilityScenes20260927/Meshes'
if Path(u.Paths.project_dir()).resolve()!=PROJECT.resolve():raise RuntimeError('Wrong project')
ue=u.get_editor_subsystem(u.UnrealEditorSubsystem)
if ue and ue.get_game_world():raise RuntimeError('Preserve active play; facility import pending')
sys.path.insert(0,str(PROJECT/'Tools/AssetPipeline'))
from dungeon_material_usage import ensure_material_usage
initial_dirty={p.get_name() for p in list(u.EditorLoadingAndSavingUtils.get_dirty_map_packages())+list(u.EditorLoadingAndSavingUtils.get_dirty_content_packages())}
E=u.EditorAssetLibrary;A=u.AssetToolsHelpers.get_asset_tools()
def guard_material(material):
    if material.get_path_name().split('.')[0] in initial_dirty:raise RuntimeError('Preserve unsaved material '+material.get_path_name())
remap={}
for batch in ('DungeonSeamMetal20260923','DungeonWallDamage20260923'):
    remap.update(json.loads((ROOT.parent/batch/'Config/material-remap.json').read_text(encoding='utf-8')))
manifest=json.loads((ROOT/'Authored/manifest.json').read_text(encoding='utf-8'))
receipt_path=ROOT/'Receipts/import.json';receipt_path.parent.mkdir(exist_ok=True)
receipt=json.loads(receipt_path.read_text(encoding='utf-8')) if receipt_path.exists() else dict(stage='importing',meshes={},tests_run=False)
# The first interrupted import returned an asset but stopped before its receipt:
# retain ownership of that exact new package when continuing this production batch.
first_call=ROOT/'import-call-01.txt'
if 'SM_Facility_PumpSkid' not in receipt['meshes'] and first_call.exists() and 'Imported UCX collision missing '+BASE+'/SM_Facility_PumpSkid' in first_call.read_text(encoding='utf-8',errors='replace'):
    receipt.setdefault('pending',{}).setdefault('SM_Facility_PumpSkid',dict(path=BASE+'/SM_Facility_PumpSkid'))
for item in manifest['objects']:
    name=item['name'];path=BASE+'/'+name
    digest=hashlib.sha256(Path(item['fbx']).read_bytes()).hexdigest()
    previous=receipt['meshes'].get(name)
    if previous and previous['source_sha256']==digest:continue
    pending=receipt.get('pending',{}).get(name)
    if path in initial_dirty and not pending:raise RuntimeError('Preserve unsaved mesh '+path)
    if E.does_asset_exist(path) and not previous and not pending:raise RuntimeError('Existing mesh has no ownership receipt '+path)
    receipt.setdefault('pending',{})[name]=dict(path=path,source_sha256=digest)
    receipt_path.write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf-8')
    task=u.AssetImportTask();task.filename=item['fbx'];task.destination_path=BASE;task.destination_name=name
    task.automated=True;task.replace_existing=bool(previous or pending);task.save=False
    options=u.FbxImportUI();options.import_mesh=True;options.import_materials=False;options.import_textures=False
    options.import_as_skeletal=False;options.automated_import_should_detect_type=False;options.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
    data=options.static_mesh_import_data;data.combine_meshes=True;data.convert_scene=True;data.convert_scene_unit=True
    data.transform_vertex_to_absolute=True;data.auto_generate_collision=False;data.one_convex_hull_per_ucx=True
    data.generate_lightmap_u_vs=False;data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS
    data.normal_generation_method=u.FBXNormalGenerationMethod.MIKK_T_SPACE;data.vertex_color_import_option=u.VertexColorImportOption.REPLACE
    task.options=options;task.factory=u.FbxFactory();A.import_asset_tasks([task])
    mesh=u.load_asset(path)
    if not mesh:raise RuntimeError('Import failed '+path)
    for index,slot in enumerate(mesh.get_editor_property('static_materials')):
        key=re.sub(r'[._][0-9]{3}$','',str(slot.material_slot_name))
        source=item['materials'][key];material=u.load_asset(remap.get(source,source))
        if not material:raise RuntimeError('Missing facility material '+source)
        ensure_material_usage(material,guard_material);mesh.set_material(index,material)
    mesh.get_editor_property('body_setup').set_editor_property('collision_trace_flag',u.CollisionTraceFlag.CTF_USE_SIMPLE_AND_COMPLEX)
    nanite=mesh.get_editor_property('nanite_settings').copy();nanite.enabled=True;nanite.explicit_tangents=True
    nanite.generate_fallback=u.NaniteGenerateFallback.ENABLED;nanite.fallback_target=u.NaniteFallbackTarget.PERCENT_TRIANGLES
    nanite.fallback_percent_triangles=1.;nanite.fallback_relative_error=0
    mesh.set_editor_property('nanite_settings',nanite)
    if not u.PlazaInstanceTools.build_nanite_data(mesh):raise RuntimeError('Nanite build failed '+path)
    # Missing UCX would silently remove the large obstacle's collision. This is an import
    # output requirement, not a gameplay or performance acceptance run.
    aggregate=mesh.get_editor_property('body_setup').get_editor_property('agg_geom')
    simple_count=sum(len(aggregate.get_editor_property(key)) for key in ('box_elems','sphere_elems','sphyl_elems'))
    convex_count=len(aggregate.get_editor_property('convex_elems'))
    shape_count=simple_count+convex_count
    if item['collision'] and shape_count<item['collision_boxes']:raise RuntimeError('Imported UCX collision missing '+path)
    if not E.save_loaded_asset(mesh,False):raise RuntimeError('Save failed '+path)
    receipt['meshes'][name]=dict(path=path,source_sha256=digest,collision_shapes=shape_count,
        convex_shapes=convex_count,collision_mode='simple_and_complex',nanite=True,source_triangles=item['triangles'])
    receipt['pending'].pop(name,None)
    receipt_path.write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf-8')
    print('FACILITY_MESH_SAVED',name,shape_count,flush=True)
receipt['stage']='meshes_saved'
receipt_path.write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf-8')
print('FACILITY_IMPORT_COMPLETE',len(receipt['meshes']),flush=True)
