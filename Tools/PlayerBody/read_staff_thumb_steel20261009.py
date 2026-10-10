"""Read the current Jason steel layers and original plate topology for repair."""
import json
from pathlib import Path
import unreal as u
root=Path('D:/FPS3D/FPSGAME');out=root/'SourceAssets/ThirdPersonStaffThumbSteel20261009'
out.mkdir(parents=True,exist_ok=True)
cfg=json.loads((root/'Content/ColdSteelData/modular_outfits.json').read_text(encoding='utf-8-sig'))
item=cfg['items']['ue_steel_gauntlets']
def xyz(p):return [p.x,p.y,p.z]
G=u.GeometryScript_AssetUtils;Q=u.GeometryScript_MeshQueries;L=u.GeometryScript_List;B=u.GeometryScript_BoneWeights
for label,path in [('production',item['rig_meshes']['Jason']),('original',item['rig_meshes']['Body'])]:
    asset=u.load_asset(path)
    dm,status=G.copy_mesh_from_skeletal_mesh(asset,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD())
    if status!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError(path)
    _,points,_=Q.get_all_vertex_positions(dm,False);points=L.convert_vector_list_to_array(points)
    _,tri,_=Q.get_all_triangle_indices(dm,False);tri=L.convert_triangle_list_to_array(tri)
    _,bones=B.get_all_bones_info(dm)
    weights=[]
    for i in range(len(points)):
        _,ws,valid=B.get_vertex_bone_weights(dm,i)
        if not valid:raise RuntimeError('Missing weights')
        weights.append([[w.bone_index,w.weight] for w in ws if w.weight>0])
    mats=[dict(slot=str(m.material_slot_name),asset=m.material_interface.get_path_name() if m.material_interface else '') for m in asset.materials]
    data=dict(source=path,positions=[xyz(p) for p in points],triangles=[xyz(t) for t in tri],weights=weights,
        triangle_materials=[u.GeometryScript_Materials.get_triangle_material_id(dm,i)[0] for i in range(len(tri))],materials=mats,
        bones=[dict(name=str(b.name),index=b.index,parent=b.parent_index,position=xyz(b.world_transform.translation),
        axes=[xyz(b.world_transform.transform_location(v)-b.world_transform.translation) for v in (u.Vector(1,0,0),u.Vector(0,1,0),u.Vector(0,0,1))]) for b in bones])
    (out/(label+'.json')).write_text(json.dumps(data,separators=(',',':')))
    print('STAFF_STEEL_INPUT '+label+' '+str(len(points))+' '+str(mats))
