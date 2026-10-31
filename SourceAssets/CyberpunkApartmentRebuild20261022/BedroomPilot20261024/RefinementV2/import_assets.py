"""Import revised geometry at source-hash paths; retain all prior production assets."""
from pathlib import Path
import unreal as u,json,sys,hashlib,gc,traceback
sys.path.insert(0,str(Path(__file__).resolve().parent))
from design import *
E=u.EditorAssetLibrary;A=u.AssetToolsHelpers.get_asset_tools()
SM=u.get_editor_subsystem(u.StaticMeshEditorSubsystem) or u.new_object(u.StaticMeshEditorSubsystem)
materials=json.loads((R.parent/'assets_saved.json').read_text('utf8'))['materials']
report=dict(stage='importing',materials=materials,meshes={},geometry_checked=True)
def record():(R/'assets_saved.json').write_text(json.dumps(report,indent=2),encoding='utf8')
def main():
    for row in json.loads((R/'assembly.json').read_text('utf8'))['meshes']:
        sha=hashlib.sha256(Path(row['fbx']).read_bytes()).hexdigest();folder=BASE+'/Meshes/'+sha[:10];path=folder+'/'+row['name']
        mesh=u.load_asset(path) if E.does_asset_exist(path) else None
        if not mesh:
            task=u.AssetImportTask();task.filename=row['fbx'];task.destination_path=folder;task.destination_name=row['name'];task.automated=True;task.replace_existing=False;task.save=False;task.factory=u.FbxFactory()
            opt=u.FbxImportUI();opt.automated_import_should_detect_type=False;opt.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH;opt.import_mesh=True;opt.import_materials=False;opt.import_textures=False;opt.import_animations=False
            d=opt.static_mesh_import_data
            for k,v in dict(combine_meshes=True,convert_scene=True,convert_scene_unit=True,transform_vertex_to_absolute=True,auto_generate_collision=False,generate_lightmap_u_vs=False,one_convex_hull_per_ucx=True).items():d.set_editor_property(k,v)
            d.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS;task.options=opt;A.import_asset_tasks([task]);mesh=u.load_asset(path)
            if not mesh:raise RuntimeError('Import failed '+path)
            for i,slot in enumerate(mesh.static_materials):mesh.set_material(i,u.load_asset(materials[str(slot.material_slot_name)]))
            bs=SM.get_lod_build_settings(mesh,0);bs.use_full_precision_u_vs=True;bs.recompute_normals=False;bs.recompute_tangents=True;bs.use_mikk_t_space=True;SM.set_lod_build_settings(mesh,0,bs)
            body=mesh.get_editor_property('body_setup');body.set_editor_property('collision_trace_flag',u.CollisionTraceFlag.CTF_USE_SIMPLE_AND_COMPLEX)
            ns=mesh.get_editor_property('nanite_settings').copy();ns.enabled=row['nanite'];ns.explicit_tangents=True;ns.generate_fallback=u.NaniteGenerateFallback.ENABLED;ns.fallback_target=u.NaniteFallbackTarget.PERCENT_TRIANGLES;ns.fallback_percent_triangles=1.;mesh.set_editor_property('nanite_settings',ns)
            if row['nanite'] and not u.PlazaInstanceTools.build_nanite_data(mesh):raise RuntimeError('Nanite build failed '+row['key'])
            if not E.save_loaded_asset(mesh,False):raise RuntimeError('Mesh save failed '+path)
        report['meshes'][row['key']]=dict(path=mesh.get_path_name(),sha256=sha,triangles=row['triangles'],simple_hulls=row['simple_hulls'],nanite=row['nanite'])
        record();print('BEDROOM_V2_MESH_SAVED',row['key']);mesh=None;gc.collect();u.SystemLibrary.collect_garbage()
    report['stage']='assets_saved';record()
if __name__=='__main__':main()
