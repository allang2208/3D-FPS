"""Read current M24 source corner attributes for a shading-only repair."""
import unreal as u, json, gzip, hashlib
from pathlib import Path
O=Path(__file__).resolve().parent
Q,G,L=u.GeometryScript_MeshQueries,u.GeometryScript_AssetUtils,u.GeometryScript_List
paths={
 'standard':'/Game/Weapons/M24/AdvancedAction20261029/Meshes/SM_M24_m24_advanced_action',
 'skeleton_front':'/Game/Weapons/M24/ReceiverGripRebuild20261031/Meshes/SM_M24_AdvancedFront_ForIndependentGrip',
 'skeleton_seat':'/Game/Weapons/M24/ReceiverGripRebuild20261031/Meshes/SM_M24_ReceiverStock_Advanced',
}
def xyz(v):return [v.x,v.y,v.z]
def disk(p):return Path(u.Paths.project_content_dir())/(p.split('.')[0].removeprefix('/Game/')+'.uasset')
report={'meshes':{},'materials':{}}
SM=u.get_editor_subsystem(u.StaticMeshEditorSubsystem) or u.new_object(u.StaticMeshEditorSubsystem)
for key,path in paths.items():
    asset=u.load_asset(path)
    if not asset:raise RuntimeError('Missing '+path)
    row={'path':path,'sha256':hashlib.sha256(disk(path).read_bytes()).hexdigest(),
         'slots':[{'slot':str(s.material_slot_name),'material':s.material_interface.get_path_name()} for s in asset.static_materials],
         'lods':[]}
    for li in range(1 if key=='standard' else asset.get_num_lods()):
        opts=u.GeometryScriptCopyMeshFromAssetOptions(apply_build_settings=False,use_build_scale=False)
        lod=u.GeometryScriptMeshReadLOD(lod_type=u.GeometryScriptLODType.SOURCE_MODEL,lod_index=li)
        dm,status=G.copy_mesh_from_static_mesh(asset,u.DynamicMesh(),opts,lod)
        if status!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Source LOD missing '+path+' '+str(li))
        _,vs,_=Q.get_all_vertex_positions(dm,False)
        _,ts,_=Q.get_all_triangle_indices(dm,False)
        _,ids,_=Q.get_all_triangle_i_ds(dm)
        _,ms,_=u.GeometryScript_Materials.get_all_triangle_material_i_ds(dm)
        tids=list(L.convert_index_list_to_array(ids));ns={}
        for ti in tids:
            _,a,b,c,valid=Q.get_triangle_normals(dm,ti)
            if not valid:raise RuntimeError('Missing corner normals '+str(ti))
            ns[str(ti)]=[xyz(a),xyz(b),xyz(c)]
        settings=SM.get_lod_build_settings(asset,li)
        row['lods'].append({'index':li,'positions':[xyz(v) for v in L.convert_vector_list_to_array(vs)],
             'triangles':[[int(t.x),int(t.y),int(t.z)] for t in L.convert_triangle_list_to_array(ts)],
             'triangle_ids':tids,'material_ids':list(L.convert_index_list_to_array(ms)), 'normals':ns,
             'uv_channels':Q.get_num_uv_sets(dm),'build_scale':xyz(settings.build_scale3d)})
    report['meshes'][key]=row
    print('M24_SHADING_SOURCE',key,[len(x['triangle_ids']) for x in row['lods']],flush=True)
    for slot in row['slots']:
        path=slot['material']
        if path in report['materials']:continue
        mi=u.load_asset(path);base=mi.get_base_material();values={}
        for kind in ('scalar','vector','texture'):
            result={}
            for name in getattr(u.MaterialEditingLibrary,'get_'+kind+'_parameter_names')(base):
                v=getattr(u.MaterialEditingLibrary,'get_material_instance_'+kind+'_parameter_value')(mi,name)
                result[str(name)]=v.get_path_name() if isinstance(v,u.Object) else [v.r,v.g,v.b,v.a] if isinstance(v,u.LinearColor) else v
            values[kind]=result
        report['materials'][path]={'sha256':hashlib.sha256(disk(path).read_bytes()).hexdigest(),'parameters':values}
with gzip.open(O/'inputs.json.gz','wt',encoding='utf-8') as f:json.dump(report,f,separators=(',',':'))
(O/'input_receipt.json').write_text(json.dumps({k:{'path':v['path'],'sha256':v['sha256'],'slots':v['slots'],'lods':[{'index':r['index'],'triangles':len(r['triangle_ids']),'uv_channels':r['uv_channels']} for r in v['lods']]} for k,v in report['meshes'].items()},indent=2),encoding='utf-8')
