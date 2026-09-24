"""Import only new packages; release each completed Nanite/collision build batch."""
import json,re,sys
from pathlib import Path
import unreal as u
ROOT=Path(__file__).resolve().parents[1];BASE='/Game/Dungeons/RoomVariants20260924/Meshes/'
sys.path.insert(0,str(ROOT.parents[1]/'Tools/AssetPipeline'))
from dungeon_material_usage import ensure_mesh_material_usage
if Path(u.Paths.project_dir()).resolve()!=ROOT.parents[1].resolve():raise RuntimeError('Wrong project')
E=u.EditorAssetLibrary;A=u.AssetToolsHelpers.get_asset_tools()
manifest=json.loads((ROOT/'Authored/manifest.json').read_text())
remap={}
for relative in ('DungeonSeamMetal20260923','DungeonWallDamage20260923'):
    remap.update(json.loads((ROOT.parent/relative/'Config/material-remap.json').read_text()))
receipt_file=ROOT/'Receipts/import.json'
receipt=json.loads(receipt_file.read_text()) if receipt_file.exists() else dict(stage='importing',meshes={},tests_run=False)
def import_mesh(item):
    path=BASE+item['name']
    task=u.AssetImportTask();task.filename=item['fbx'];task.destination_path=BASE.rstrip('/');task.destination_name=item['name']
    task.automated=True;task.replace_existing=False;task.save=False
    opt=u.FbxImportUI();opt.import_mesh=True;opt.import_materials=False;opt.import_textures=False;opt.import_as_skeletal=False
    opt.automated_import_should_detect_type=False;opt.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
    data=opt.static_mesh_import_data;data.combine_meshes=True;data.convert_scene=True;data.convert_scene_unit=True
    data.transform_vertex_to_absolute=True;data.auto_generate_collision=False;data.generate_lightmap_u_vs=False
    data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS;data.vertex_color_import_option=u.VertexColorImportOption.REPLACE
    task.options=opt;task.factory=u.FbxFactory();A.import_asset_tasks([task]);mesh=u.load_asset(path)
    if not mesh:raise RuntimeError('Mesh import failed '+path)
    for i,slot in enumerate(mesh.get_editor_property('static_materials')):
        key=re.sub(r'[._][0-9]{3}$','',str(slot.material_slot_name));old=item['materials'][key].split('.')[0]
        material=u.load_asset(remap.get(old,old))
        if not material:raise RuntimeError('Missing material '+old)
        mesh.set_material(i,material)
    ensure_mesh_material_usage(mesh)
    mesh.get_editor_property('body_setup').set_editor_property('collision_trace_flag',u.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE)
    settings=mesh.get_editor_property('nanite_settings').copy();settings.enabled=True;settings.explicit_tangents=True
    settings.generate_fallback=u.NaniteGenerateFallback.ENABLED;settings.fallback_target=u.NaniteFallbackTarget.PERCENT_TRIANGLES
    settings.fallback_percent_triangles=1.;settings.fallback_relative_error=0
    mesh.set_editor_property('nanite_settings',settings)
    if not u.PlazaInstanceTools.build_nanite_data(mesh):raise RuntimeError('Nanite build failed '+path)
    if not E.save_loaded_asset(mesh,False):raise RuntimeError('Asset save failed '+path)
    return path
for index,item in enumerate(manifest['objects']):
    if item['name'] in receipt['meshes']:continue
    receipt['meshes'][item['name']]=import_mesh(item)
    receipt_file.write_text(json.dumps(receipt,indent=2))
    if (index+1)%4==0:u.collect_garbage()
    print('ROOM_VARIANT_IMPORTED',len(receipt['meshes']),len(manifest['objects']),flush=True)
receipt['stage']='meshes_saved';receipt_file.write_text(json.dumps(receipt,indent=2))
print('ROOM_VARIANT_IMPORT_COMPLETE',len(receipt['meshes']),flush=True)
