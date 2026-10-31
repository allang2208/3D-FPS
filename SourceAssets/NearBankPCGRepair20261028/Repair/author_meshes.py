from pathlib import Path
import json,unreal as u
R=Path(__file__).resolve().parent
def main():
    jobs=json.loads((R/'mesh_jobs.json').read_text());saved=[]
    for job in jobs:
        dm=u.DynamicMesh();sm=u.load_asset(job['asset'])
        if job['kind']=='edit_vertices':
            if not sm:raise RuntimeError('Missing owned surface '+job['asset'])
            lod=u.GeometryScriptMeshReadLOD();lod.lod_type=u.GeometryScriptLODType.SOURCE_MODEL
            u.GeometryScript_AssetUtils.copy_mesh_from_static_mesh(sm,dm,u.GeometryScriptCopyMeshFromAssetOptions(),lod)
            positions=u.GeometryScript_List.convert_array_to_vector_list([u.Vector(*v) for v in job['vertices_cm']])
            u.GeometryScript_MeshEdits.set_all_mesh_vertex_positions(dm,positions)
        else:
            buf=u.GeometryScriptSimpleMeshBuffers()
            buf.vertices=[u.Vector(*v) for v in job['vertices_cm']]
            buf.triangles=[u.IntVector(*t) for t in job['triangles']]
            buf.normals=[u.Vector(0,0,1) for v in job['vertices_cm']]
            buf.uv0=[u.Vector2D(v[0]/200,v[1]/200) for v in job['vertices_cm']]
            u.GeometryScript_MeshEdits.append_buffers_to_mesh(dm,buf,0,False)
        if sm:
            opts=u.GeometryScriptCopyMeshToAssetOptions()
            u.GeometryScript_AssetUtils.copy_mesh_to_static_mesh(dm,sm,opts,u.GeometryScriptMeshWriteLOD())
        else:
            opts=u.GeometryScriptCreateNewStaticMeshAssetOptions();opts.enable_collision=True;opts.collision_mode=u.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE
            result=u.GeometryScript_NewAssetUtils.create_new_static_mesh_asset_from_mesh(dm,job['asset'],opts)
            sm=result[0] if isinstance(result,tuple) else result
        if not sm:raise RuntimeError('Cannot manufacture '+job['asset'])
        if job.get('material'):sm.set_material(0,u.load_asset(job['material']))
        body=sm.get_editor_property('body_setup')
        body.set_editor_property('collision_trace_flag',u.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE)
        body.set_editor_property('double_sided_geometry',True)
        if not u.EditorAssetLibrary.save_loaded_asset(sm,False):raise RuntimeError('Cannot save '+job['asset'])
        saved.append(dict(asset=sm.get_path_name(),triangles=dm.get_triangle_count(),hidden=job.get('hidden',False),collision=str(body.get_editor_property('collision_trace_flag'))))
        print('REPAIR_MESH_SAVED',sm.get_name(),dm.get_triangle_count(),flush=True)
    (R/'meshes_saved.json').write_text(json.dumps(saved,indent=2))
if __name__=='__main__':main()
