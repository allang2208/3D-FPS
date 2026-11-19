"""Read back the saved isolated candidate and donor; never save loaded assets."""
import json
from pathlib import Path
import unreal as u

OUT=Path(globals().get('variant_output','D:/FPS3D/FPSGAME/SourceAssets/JasonStrong20261117/R2_LongLegs'))
REVIEW=OUT/'AnatomyReview'
REVIEW.mkdir(parents=True,exist_ok=True)
saved=json.loads((OUT/'variant_saved.json').read_text())
G,Q,B,L=u.GeometryScript_AssetUtils,u.GeometryScript_MeshQueries,u.GeometryScript_BoneWeights,u.GeometryScript_List

def xyz(v):
    return [v.x,v.y,v.z]

def transform(t):
    return {'position':xyz(t.translation),'axes':[xyz(t.transform_location(v)-t.translation)
        for v in (u.Vector(1,0,0),u.Vector(0,1,0),u.Vector(0,0,1))]}

for label,path in [('original',saved['source']),('derived',saved['asset'])]:
    asset=u.load_asset(path)
    if not asset:raise RuntimeError('Missing '+path)
    reader=u.SkeletonModifier()
    if not reader.set_skeletal_mesh(asset):raise RuntimeError('Cannot read skeleton')
    dm,result=G.copy_mesh_from_skeletal_mesh(asset,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD())
    if result!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Cannot read mesh')
    _,plist,_=Q.get_all_vertex_positions(dm,False)
    positions=L.convert_vector_list_to_array(plist)
    _,tlist,_=Q.get_all_triangle_indices(dm,False)
    triangles=L.convert_triangle_list_to_array(tlist)
    _,bones=B.get_all_bones_info(dm)
    weights=[]
    for vi in range(len(positions)):
        _,ws,valid=B.get_vertex_bone_weights(dm,vi)
        if not valid:raise RuntimeError('Missing weights '+str(vi))
        weights.append([[w.bone_index,w.weight] for w in ws if w.weight>0])
    uv,mids=[],[]
    for ti in range(len(triangles)):
        a,b,c,valid=Q.get_triangle_u_vs(dm,0,ti)
        uv.append([[v.x,v.y] for v in (a,b,c)])
        mid,valid=u.GeometryScript_Materials.get_triangle_material_id(dm,ti)
        mids.append(mid)
    data={'source':path,'skeleton':asset.skeleton.get_path_name(),
        'physics_asset':asset.physics_asset.get_path_name() if asset.physics_asset else None,
        'positions':[xyz(p) for p in positions],'triangles':[xyz(t) for t in triangles],
        'triangle_uvs':uv,'triangle_materials':mids,'weights':weights,
        'materials':[{'slot':str(m.material_slot_name),'asset':m.material_interface.get_path_name() if m.material_interface else ''} for m in asset.materials],
        'bones':[dict(name=str(b.name),index=b.index,parent=b.parent_index,
            **transform(reader.get_bone_transform(b.name,True)),
            local=transform(reader.get_bone_transform(b.name,False)),
            geometry_bone=transform(b.world_transform)) for b in bones]}
    (REVIEW/(label+'_saved_mesh.json')).write_text(json.dumps(data,separators=(',',':')),encoding='utf-8')
    print('JASON_ANATOMY_CAPTURE '+label+' '+str(len(positions))+' vertices '+str(len(bones))+' bones',flush=True)
print('JASON_ANATOMY_READBACK_COMPLETE',flush=True)
