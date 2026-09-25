import collections,json
from pathlib import Path
import unreal as u
root=Path('D:/FPS3D/FPSGAME/Saved/M4RefinedSkinRepair20260924')
path='/Game/Characters/ModularOutfit20260924/OriginalShapeBareM4RefinedV3/SK_M4_OriginalShape_BareHands'
a=u.load_asset(path);r={'lods':[]}
for lod in range(3):
    dm,result=u.GeometryScript_AssetUtils.copy_mesh_from_skeletal_mesh(a,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD(lod_index=lod))
    _,pl,_=u.GeometryScript_MeshQueries.get_all_vertex_positions(dm,False)
    ps=u.GeometryScript_List.convert_vector_list_to_array(pl)
    _,tl,_=u.GeometryScript_MeshQueries.get_all_triangle_indices(dm,False)
    ts=u.GeometryScript_List.convert_triangle_list_to_array(tl)
    data={'positions':[[p.x,p.y,p.z] for p in ps],'triangles':[[t.x,t.y,t.z] for t in ts],'uv':[],'normals':[],'materials':[],'weights':[]}
    _,bones=u.GeometryScript_BoneWeights.get_all_bones_info(dm);names={b.index:str(b.name) for b in bones}
    for ti,t in enumerate(ts):
        data['materials'].append(u.GeometryScript_Materials.get_triangle_material_id(dm,ti)[0])
        uv=u.GeometryScript_MeshQueries.get_triangle_u_vs(dm,0,ti)
        data['uv'].append([[x.x,x.y] for x in uv[:3]])
        _,x,y,z,valid=u.GeometryScript_MeshQueries.get_triangle_normals(dm,ti)
        data['normals'].append([[n.x,n.y,n.z] for n in (x,y,z)])
    for vi in range(len(ps)):
        _,ws,valid=u.GeometryScript_BoneWeights.get_vertex_bone_weights(dm,vi)
        data['weights'].append({names[w.bone_index]:w.weight for w in ws if w.weight>0})
    (root/('surface-lod'+str(lod)+'.json')).write_text(json.dumps(data,separators=(',',':')))
    r['lods'].append({'lod':lod,'vertices':len(ps),'triangles':len(ts),'materials':dict(collections.Counter(data['materials']))})
(root/'surface-summary.json').write_text(json.dumps(r,indent=2))
print(json.dumps(r))
