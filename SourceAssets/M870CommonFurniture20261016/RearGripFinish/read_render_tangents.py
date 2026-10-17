"""Targeted read of the saved render LOD tangent frames behind the UE warning."""
import unreal as u,json,hashlib
from pathlib import Path
O=Path(__file__).parent;P=O.parents[2];R={'meshes':{},'gameplay_tested':False}
G=u.GeometryScript_AssetUtils;N=u.GeometryScript_Normals;L=u.GeometryScript_List
for key in ('phantom_reargrip','stable_antislip_reargrip','balanced_reargrip'):
    path='/Game/Weapons/M870/CommonFurniture20261016/Meshes/SM_M870_'+key;m=u.load_asset(path)
    ed=u.get_editor_subsystem(u.StaticMeshEditorSubsystem) or u.new_object(u.StaticMeshEditorSubsystem)
    lods=[]
    for lod in range(ed.get_lod_count(m)):
        dm,status=G.copy_mesh_from_static_mesh(m,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(apply_build_settings=False,request_tangents=True),u.GeometryScriptMeshReadLOD(lod_type=u.GeometryScriptLODType.RENDER_DATA,lod_index=lod))
        if status!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Render data read failed '+key)
        _,xs,ys,valid,gaps=N.get_mesh_per_vertex_tangents(dm,False)
        _,ns,nvalid,ngaps=N.get_mesh_per_vertex_normals(dm,False)
        if not valid or not nvalid or gaps or ngaps:raise RuntimeError('Incomplete render tangent data '+key)
        xs,ys,ns=[L.convert_vector_list_to_array(a) for a in (xs,ys,ns)]
        zero=lambda v:all(abs(c)<=1e-4 for c in (v.x,v.y,v.z))
        row={'lod':lod,'render_vertices':len(xs),'zero_tangents':sum(zero(v) for v in xs),'zero_bitangents':sum(zero(v) for v in ys),'zero_normals':sum(zero(v) for v in ns)}
        _,pv,_=u.GeometryScript_MeshQueries.get_all_vertex_positions(dm,False);ps=L.convert_vector_list_to_array(pv)
        row['bad_positions_cm']=[[ps[i].x,ps[i].y,ps[i].z] for i in range(len(xs)) if zero(xs[i]) or zero(ys[i]) or zero(ns[i])][:24]
        row['build_settings']=str(ed.get_lod_build_settings(m,lod))
        lods.append(row)
    R['meshes'][key]={'path':path,'import_method':str(m.get_editor_property('asset_import_data').get_editor_property('normal_import_method')),'nanite_settings':str(m.get_editor_property('nanite_settings')),'render_lods':lods,'materials':[{'slot':str(s.material_slot_name),'source_slot':str(s.get_editor_property('imported_material_slot_name')),'material':s.material_interface.get_path_name()} for s in m.static_materials]}
    dm,status=G.copy_mesh_from_static_mesh(m,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(apply_build_settings=False,request_tangents=True),u.GeometryScriptMeshReadLOD(lod_type=u.GeometryScriptLODType.SOURCE_MODEL))
    _,xs,ys,valid,gaps=N.get_mesh_per_vertex_tangents(dm,False)
    xs,ys=[L.convert_vector_list_to_array(a) for a in (xs,ys)]
    R['meshes'][key]['source_tangents']={'valid':valid,'zero_tangents':sum(zero(v) for v in xs),'zero_bitangents':sum(zero(v) for v in ys)}
protected=json.loads((O/'protected_assets.json').read_text())
R['protected_assets_count']=len(protected)
R['protected_assets_changed']=[name for name,sha in protected.items() if hashlib.sha256((P/name).read_bytes()).hexdigest()!=sha]
R['tangent_warnings_resolved']=all(not any(lod[k] for k in ('zero_tangents','zero_bitangents','zero_normals')) for row in R['meshes'].values() for lod in row['render_lods'])
(O/'saved_render_tangents.json').write_text(json.dumps(R,indent=2),encoding='utf-8')
print('M870_RENDER_TANGENTS',json.dumps({k:v['render_lods'] for k,v in R['meshes'].items()}),flush=True)
print('M870_PROTECTED_ASSETS',R['protected_assets_count'],R['protected_assets_changed'],flush=True)
