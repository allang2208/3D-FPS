"""Read saved backpack geometry and live component identities for strap repair."""
import json
from pathlib import Path
import unreal as u
P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/BackpackStraps20261012';R.mkdir(parents=True,exist_ok=True)
cfg=json.loads((P/'Content/ColdSteelData/player_body.json').read_text(encoding='utf-8-sig'))
path=cfg['outfits']['ue_mountain_backpack']['world_mesh']
worlds=u.EditorLevelLibrary.get_pie_worlds(False);runtime=[]
for world in worlds:
    for actor in u.GameplayStatics.get_all_actors_of_class(world,u.Character):
        if not actor.is_player_controlled():continue
        for c in actor.get_components_by_class(u.SkeletalMeshComponent):
            mesh=c.skeletal_mesh_asset
            if mesh and mesh.get_path_name()==path:
                runtime.append(dict(component=c.get_name(),asset=path,parent=c.get_attach_parent().get_name(),
                    relative=str(c.get_relative_transform()),materials=[c.get_material(i).get_path_name() if c.get_material(i) else None for i in range(c.get_num_materials())]))
(R/'runtime.json').write_text(json.dumps(dict(pie_active=bool(worlds),components=runtime),indent=2),encoding='utf-8')
print('BACKPACK_RUNTIME '+json.dumps(dict(pie_active=bool(worlds),components=runtime)))
asset=u.load_asset(path)
G=u.GeometryScript_AssetUtils;Q=u.GeometryScript_MeshQueries;L=u.GeometryScript_List;B=u.GeometryScript_BoneWeights
dm,status=G.copy_mesh_from_skeletal_mesh(asset,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD())
if status!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Cannot read saved backpack')
_,ps,_=Q.get_all_vertex_positions(dm,False);ps=L.convert_vector_list_to_array(ps)
_,ts,_=Q.get_all_triangle_indices(dm,False);ts=L.convert_triangle_list_to_array(ts)
_,bones=B.get_all_bones_info(dm)
weights=[];normals=[];uv=[]
for vi in range(len(ps)):
    _,ws,valid=B.get_vertex_bone_weights(dm,vi)
    if not valid:raise RuntimeError('Missing backpack weight')
    weights.append([[w.bone_index,w.weight] for w in ws if w.weight>0])
for ti in range(len(ts)):
    a,b,c,valid=Q.get_triangle_u_vs(dm,0,ti)
    if not valid:raise RuntimeError('Missing backpack UV')
    uv.append([[v.x,v.y] for v in [a,b,c]])
    _,a,b,c,valid=Q.get_triangle_normals(dm,ti)
    if not valid:raise RuntimeError('Missing backpack normal')
    normals.append([[v.x,v.y,v.z] for v in [a,b,c]])
data=dict(source=path,positions=[[v.x,v.y,v.z] for v in ps],triangles=[[t.x,t.y,t.z] for t in ts],
    weights=weights,uv=uv,normals=normals,
    triangle_materials=[u.GeometryScript_Materials.get_triangle_material_id(dm,i)[0] for i in range(len(ts))],
    bones=[dict(index=b.index,name=str(b.name),parent=b.parent_index) for b in bones],
    materials=[dict(slot=str(m.material_slot_name),asset=m.material_interface.get_path_name()) for m in asset.materials])
(R/'backpack_input.json').write_text(json.dumps(data,separators=(',',':')),encoding='utf-8')
print('BACKPACK_SOURCE_SAVED '+str(len(ps))+' vertices '+str(len(ts))+' triangles')
