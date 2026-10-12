"""Read component identities and saved mesh sources for the reported waist gap."""
import json
from pathlib import Path
import unreal as u

P=Path('D:/FPS3D/FPSGAME')
R=P/'SourceAssets/PlayerWaistSeam20261012'
R.mkdir(parents=True,exist_ok=True)
cfg=json.loads((P/'Content/ColdSteelData/modular_outfits.json').read_text(encoding='utf-8-sig'))
body=json.loads((P/'Content/ColdSteelData/player_body.json').read_text(encoding='utf-8-sig'))
profile=cfg['profiles'][body['body_mesh']] if 'profiles' in cfg else None
if profile is None:
    profile=next(v[body['body_mesh']] for v in cfg.values() if isinstance(v,dict) and body['body_mesh'] in v)
worlds=u.EditorLevelLibrary.get_pie_worlds(False)
runtime=[]
for world in worlds:
    for actor in u.GameplayStatics.get_all_actors_of_class(world,u.Character):
        if not actor.is_player_controlled():continue
        for c in actor.get_components_by_class(u.SkeletalMeshComponent):
            asset=c.skeletal_mesh_asset
            if not asset or 'Jason' not in asset.get_path_name():continue
            runtime.append(dict(component=c.get_name(),asset=asset.get_path_name(),visible=c.is_visible(),
                materials=[c.get_material(i).get_path_name() if c.get_material(i) else None for i in range(c.get_num_materials())],
                sections=[c.is_material_section_shown(i,0) for i in range(c.get_num_materials())]))
(R/'runtime.json').write_text(json.dumps(dict(pie_active=bool(worlds),components=runtime),indent=2),encoding='utf-8')
print('WAIST_RUNTIME '+json.dumps(dict(pie_active=bool(worlds),components=runtime)))
sources={'body':profile['base'],'capri':cfg['items']['ue_smoke_grey_capri']['rig_meshes']['Jason']}
Q=u.GeometryScript_MeshQueries;L=u.GeometryScript_List;B=u.GeometryScript_BoneWeights
for key,path in sources.items():
    mesh=u.load_asset(path)
    if not mesh:raise RuntimeError('Missing '+path)
    dm,status=u.GeometryScript_AssetUtils.copy_mesh_from_skeletal_mesh(mesh,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD())
    if status!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Cannot read '+path)
    _,vs,_=Q.get_all_vertex_positions(dm,False);vs=L.convert_vector_list_to_array(vs)
    _,ts,_=Q.get_all_triangle_indices(dm,False);ts=L.convert_triangle_list_to_array(ts)
    data=dict(source=path,positions=[[v.x,v.y,v.z] for v in vs],triangles=[[t.x,t.y,t.z] for t in ts],
        triangle_materials=[u.GeometryScript_Materials.get_triangle_material_id(dm,i)[0] for i in range(len(ts))],
        materials=[dict(slot=str(m.material_slot_name),asset=m.material_interface.get_path_name() if m.material_interface else None) for m in mesh.materials])
    (R/(key+'.json')).write_text(json.dumps(data,separators=(',',':')),encoding='utf-8')
    print('WAIST_SOURCE '+json.dumps(dict(key=key,path=path,vertices=len(vs),triangles=len(ts),materials=data['materials'])))
