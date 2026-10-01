"""Import the reused cart and save one parked instance in the warehouse sample."""
import hashlib,json,re,shutil
from pathlib import Path
import unreal as u

ROOT=Path(__file__).resolve().parents[1];HALL=ROOT.parent;PROJECT=HALL.parents[1]
ITEM=json.loads((ROOT/'Authored/manifest.json').read_text('utf-8'))
PATH=ITEM['asset'];LABEL='Reused_PalletJack'
POSITION=[-5.1,3.7,.002];YAW=180
if Path(u.Paths.project_dir()).resolve()!=PROJECT.resolve():raise RuntimeError('Wrong project')
if '-run=pythonscript' not in u.SystemLibrary.get_command_line().lower():raise RuntimeError('Use the background import commandlet')
receipt=ROOT/'Receipts/install.json'
report=dict(stage='importing',asset=PATH,tests_run=False,rendered=False,game_launched=False)
def record():receipt.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
record()
E=u.EditorAssetLibrary
mesh=u.load_asset(PATH) if E.does_asset_exist(PATH) else None
if mesh is None:
    task=u.AssetImportTask();task.filename=ITEM['fbx'];task.destination_path=PATH.rsplit('/',1)[0];task.destination_name=ITEM['name']
    task.automated=True;task.replace_existing=False;task.save=False
    opts=u.FbxImportUI();opts.import_mesh=True;opts.import_materials=False;opts.import_textures=False;opts.import_as_skeletal=False
    opts.automated_import_should_detect_type=False;opts.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
    data=opts.static_mesh_import_data;data.combine_meshes=True;data.convert_scene=True;data.convert_scene_unit=True
    data.transform_vertex_to_absolute=True;data.auto_generate_collision=False;data.one_convex_hull_per_ucx=True;data.generate_lightmap_u_vs=False
    data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS
    data.vertex_color_import_option=u.VertexColorImportOption.REPLACE;task.options=opts;task.factory=u.FbxFactory()
    u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    mesh=u.load_asset(PATH)
    if not mesh:raise RuntimeError('Cart import failed')
    for i,slot in enumerate(mesh.get_editor_property('static_materials')):
        key=re.sub(r'[._][0-9]{3}$','',str(slot.material_slot_name));mat=u.load_asset(ITEM['materials'][key])
        if not mat:raise RuntimeError('Missing original cart material '+key)
        mesh.set_material(i,mat)
    mesh.get_editor_property('body_setup').set_editor_property('collision_trace_flag',u.CollisionTraceFlag.CTF_USE_SIMPLE_AND_COMPLEX)
    sub=u.get_editor_subsystem(u.StaticMeshEditorSubsystem) or u.new_object(u.StaticMeshEditorSubsystem)
    build=sub.get_lod_build_settings(mesh,0);build.set_editor_property('use_full_precision_u_vs',True)
    build.set_editor_property('use_high_precision_tangent_basis',True);sub.set_lod_build_settings(mesh,0,build)
    n=mesh.get_editor_property('nanite_settings').copy();n.enabled=True;n.explicit_tangents=True
    n.generate_fallback=u.NaniteGenerateFallback.ENABLED;n.fallback_target=u.NaniteFallbackTarget.PERCENT_TRIANGLES
    n.fallback_percent_triangles=1.;n.fallback_relative_error=0;mesh.set_editor_property('nanite_settings',n)
    if not u.PlazaInstanceTools.build_nanite_data(mesh):raise RuntimeError('Cart Nanite build failed')
    if not E.save_loaded_asset(mesh,False):raise RuntimeError('Cart asset save failed')
report.update(stage='asset_saved',source_sha256=hashlib.sha256(Path(ITEM['fbx']).read_bytes()).hexdigest());record()
