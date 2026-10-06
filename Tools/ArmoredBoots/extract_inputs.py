"""Read the active body and trousers for native armored-boot authoring."""
import json
from pathlib import Path
import unreal as u

P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/ArmoredBoots20261004'
config=json.loads((P/'Content/ColdSteelData/modular_outfits.json').read_text(encoding='utf-8-sig'))
body=json.loads((P/'Content/ColdSteelData/player_body.json').read_text(encoding='utf-8-sig'))
profile_key=body['body_mesh'];profile=config['profiles'][profile_key]
sources={'base':profile['base']}
for key,definition in [('jeans','ue_jeans'),('cargo','ue_cargo_pants')]:
    sources[key]=config['items'][definition]['rig_meshes']['Jason']
G=u.GeometryScript_AssetUtils;B=u.GeometryScript_BoneWeights;Q=u.GeometryScript_MeshQueries
def xyz(v):return [v.x,v.y,v.z]
for key,path in sources.items():
    asset=u.load_asset(path)
    if not asset:raise RuntimeError('Missing native source '+path)
    dm,status=G.copy_mesh_from_skeletal_mesh(asset,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD())
    if status!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Cannot read '+path)
    _,bones=B.get_all_bones_info(dm)
    _,vectors,_=Q.get_all_vertex_positions(dm,False);positions=u.GeometryScript_List.convert_vector_list_to_array(vectors)
    _,indices,_=Q.get_all_triangle_indices(dm,False);triangles=u.GeometryScript_List.convert_triangle_list_to_array(indices)
    weights=[]
    for vi in range(len(positions)):
        _,bindings,valid=B.get_vertex_bone_weights(dm,vi)
        if not valid:raise RuntimeError('Missing native weights')
        weights.append([[w.bone_index,w.weight] for w in bindings if w.weight>0])
    data=dict(source=asset.get_path_name(),skeleton=asset.skeleton.get_path_name(),positions=[xyz(v) for v in positions],
        triangles=[xyz(t) for t in triangles],weights=weights,
        triangle_materials=[u.GeometryScript_Materials.get_triangle_material_id(dm,i)[0] for i in range(len(triangles))],
        materials=[dict(slot=str(m.material_slot_name),asset=m.material_interface.get_path_name() if m.material_interface else '') for m in asset.materials],
        bones=[dict(name=str(b.name),index=b.index,parent=b.parent_index,position=xyz(b.world_transform.translation),
            axes=[xyz(b.world_transform.transform_location(v)-b.world_transform.translation) for v in (u.Vector(1,0,0),u.Vector(0,1,0),u.Vector(0,0,1))]) for b in bones])
    (R/(key+'.json')).write_text(json.dumps(data,separators=(',',':')),encoding='utf-8')
    print('ARMORED_BOOT_INPUT',key,len(positions),len(triangles),flush=True)
(R/'profile.json').write_text(json.dumps(dict(profile_key=profile_key,previous_base=sources['base'],trouser_sources=sources),indent=2))
print('ARMORED_BOOT_INPUTS_SAVED',flush=True)
