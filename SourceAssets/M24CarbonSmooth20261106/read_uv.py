from pathlib import Path
import unreal as u,json
O=Path(__file__).resolve().parent
Q=u.GeometryScript_MeshQueries;G=u.GeometryScript_AssetUtils;L=u.GeometryScript_List
R={'pie':u.get_editor_subsystem(u.LevelEditorSubsystem).is_in_play_in_editor(),'meshes':{}}
for kind in ('Native','Advanced'):
    m=u.load_asset('/Game/Weapons/M24/CarbonSpine20261104/Meshes/SM_M24_CarbonSpine_'+kind)
    dm,status=G.copy_mesh_from_static_mesh(m,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(apply_build_settings=False,use_build_scale=False),u.GeometryScriptMeshReadLOD(lod_type=u.GeometryScriptLODType.SOURCE_MODEL,lod_index=0))
    if status!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Cannot read UV source '+kind)
    _,ml,valid=u.GeometryScript_Materials.get_all_triangle_material_i_ds(dm)
    mat_ids=L.convert_index_list_to_array(ml);carbon=next(i for i,s in enumerate(m.static_materials) if str(s.material_slot_name)=='CS_Meshy')
    tids=[i for i,mi in enumerate(mat_ids) if mi==carbon]
    rows=[]
    for uvset in range(Q.get_num_uv_sets(dm)):
        vals=[]
        for ti in tids[::max(1,len(tids)//512)]:
            a,b,c,ok=Q.get_triangle_u_vs(dm,uvset,ti)
            if ok:vals.extend((v.x,v.y) for v in (a,b,c))
        rows.append({'channel':uvset,'sample_corners':len(vals),'nonzero':sum(abs(x)+abs(y)>1e-7 for x,y in vals),
            'min':[min(v[j] for v in vals) for j in (0,1)] if vals else None,'max':[max(v[j] for v in vals) for j in (0,1)] if vals else None})
    R['meshes'][kind]=rows
(O/'ue_uv_before.json').write_text(json.dumps(R,indent=2));print('M24_UV_SOURCE',R)
