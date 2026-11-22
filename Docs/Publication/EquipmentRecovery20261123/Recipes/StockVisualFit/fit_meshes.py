from pathlib import Path
import json, gzip, os
import unreal as u

batch=Path(__file__).resolve().parent
if Path(u.Paths.convert_relative_path_to_full(u.Paths.project_dir())).resolve()!=batch/'Host':
    raise RuntimeError('Requires isolated art project')
inputs=json.loads((batch/'inputs.json').read_text())
frames=json.loads((batch/'frames.json').read_text())
A=u.GeometryScript_AssetUtils
M=u.GeometryScript_Materials
Q=u.GeometryScript_MeshQueries
L=u.GeometryScript_List
S=u.get_editor_subsystem(u.StaticMeshEditorSubsystem) or u.new_object(u.StaticMeshEditorSubsystem)
SUCCESS=u.GeometryScriptOutcomePins.SUCCESS
family_filter=os.environ.get('FPS_STOCK_FIT_FAMILY')
report=json.loads((batch/'authored.json').read_text()) if family_filter else {}
def asset(path):
    obj=u.load_asset(path)
    if not obj:raise RuntimeError('Cannot load '+path)
    return obj
def static(mesh,index,kind):
    dyn,done=A.copy_mesh_from_static_mesh(mesh,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD(lod_type=kind,lod_index=index))
    if done!=SUCCESS:raise RuntimeError('Cannot copy saved LOD '+str(index))
    return dyn
def transform(mesh,spec):
    tr=u.Transform(location=u.Vector(*spec['translation']),rotation=u.Quat(*spec['quaternion']).rotator(),scale=u.Vector(1,1,1))
    u.GeometryScript_MeshTransforms.transform_mesh(mesh,tr)
def extract(mesh,triangles):
    sub=u.DynamicMesh()
    u.GeometryScript_MeshDecomposition.get_sub_mesh_from_mesh(mesh,sub,triangles)
    if not sub.get_triangle_count():raise RuntimeError('Empty mesh section')
    return sub
def xyz(v):return [v.x,v.y,v.z]
def capture(mesh,family,phase):
    dyn=static(mesh,0,u.GeometryScriptLODType.RENDER_DATA)
    _,verts,_=Q.get_all_vertex_positions(dyn,False)
    _,faces,_=Q.get_all_triangle_indices(dyn,False)
    _,ids,valid=M.get_all_triangle_material_i_ds(dyn)
    if not valid:raise RuntimeError('No render sections')
    samples={'positions':[xyz(v) for v in L.convert_vector_list_to_array(verts)],'triangles':[[int(x) for x in xyz(t)] for t in L.convert_triangle_list_to_array(faces)],'material_ids':list(L.convert_index_list_to_array(ids))}
    with gzip.open(batch/(family+'_'+phase+'.json.gz'),'wt',compresslevel=1) as f:json.dump(samples,f,separators=(',',':'))
def native_trim(row):
    host=asset(row['host'])
    geom,ok=A.copy_mesh_from_skeletal_mesh(host,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD())
    if ok!=SUCCESS or geom.get_triangle_count()!=row['host_faces']:raise RuntimeError('Native trim topology changed')
    trim=extract(geom,L.convert_array_to_index_list(row['trim_ids']))
    transform(trim,row['native_to_stock'])
    return trim,asset(row['factory_material'])
def existing_trim(row):
    peer=asset(row['peer'])
    index=next(n for n,s in enumerate(peer.static_materials) if str(s.material_slot_name)=='SVD_StockAdapterSteel')
    dyn=static(peer,0,u.GeometryScriptLODType.SOURCE_MODEL)
    _,ids=M.get_triangles_by_material_id(dyn,index)
    return extract(dyn,ids),peer.get_material(index)
for family,row in frames.items():
    if family_filter and family!=family_filter:continue
    mesh=asset('/Game/'+inputs['entries'][family]['relative'].rsplit('.',1)[0])
    capture(mesh,family,'before')
    trim,surface=existing_trim(row) if family=='SVD' else native_trim(row)
    M.clear_material_i_ds(trim,1)
    # SVD has separately baked source LODs. SVCh uses the original LOD0 plus automatic reductions.
    lod_count=S.get_lod_count(mesh)
    levels=[static(mesh,i,u.GeometryScriptLODType.SOURCE_MODEL) for i in range(lod_count if family=='SVD' else 1)]
    materials=list(mesh.static_materials)
    if [str(s.material_slot_name) for s in materials]!=['SniperStock_MeshySurface','SniperStock_Interface']:raise RuntimeError('Unexpected release mesh section layout')
    opts=u.GeometryScriptCopyMeshToAssetOptions(enable_recompute_normals=False,enable_recompute_tangents=False,replace_materials=True,new_materials=[materials[0].material_interface,surface],new_material_slot_names=[s.material_slot_name for s in materials])
    for i,dyn in enumerate(levels):
        _,removed=M.delete_triangles_by_material_id(dyn,1,True)
        if not removed:raise RuntimeError('Old trim section is missing')
        transform(dyn,row['body_transform'])
        u.GeometryScript_MeshEdits.append_mesh(dyn,trim,u.Transform())
        _,ok=A.copy_mesh_to_static_mesh(dyn,mesh,opts,u.GeometryScriptMeshWriteLOD(lod_index=i))
        if ok!=SUCCESS:raise RuntimeError('Cannot write '+family+' mesh LOD '+str(i))
    if family=='SVD' and not u.M24ChassisAssetTools.bake_stock_tangent_basis(mesh):raise RuntimeError('Cannot bake authored LODs')
    if not u.EditorAssetLibrary.save_loaded_asset(mesh,False):raise RuntimeError('Cannot save '+family)
    capture(mesh,family,'after')
    report[family]={'mesh':mesh.get_path_name(),'lods':S.get_lod_count(mesh),'screen_sizes':list(S.get_lod_screen_sizes(mesh)),'surface':surface.get_path_name(),'trim_triangles':trim.get_triangle_count()}
    print('STOCK_FIT_SAVED',family,report[family],flush=True)
lod_samples={}
for family,entry in inputs['entries'].items():
    mesh=asset('/Game/'+entry['relative'].rsplit('.',1)[0])
    lod_samples[family]={}
    for i in (1,2):
        dm=static(mesh,i,u.GeometryScriptLODType.RENDER_DATA)
        _,indices=M.get_triangles_by_material_id(dm,0)
        body=extract(dm,indices)
        _,coords,_=Q.get_all_vertex_positions(body,False)
        vs=L.convert_vector_list_to_array(coords)
        _,trim_ids=M.get_triangles_by_material_id(dm,1)
        trim_count=len(L.convert_index_list_to_array(trim_ids))
        lod_samples[family][i]={'points':[xyz(vs[j]) for j in range(0,len(vs),max(1,len(vs)//4500))],'trim_triangles':trim_count}
(batch/'lod-samples.json').write_text(json.dumps(lod_samples,separators=(',',':')))
(batch/'authored.json').write_text(json.dumps(report,indent=2))
