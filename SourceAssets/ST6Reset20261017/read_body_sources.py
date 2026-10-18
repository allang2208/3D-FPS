"""Export saved native bodies as material/authoring inputs; no scene operation."""
import json
from pathlib import Path
import unreal as u
O=Path(__file__).parent;R=O.parents[1]
OUT=O/'Read';OUT.mkdir(exist_ok=True)
G=u.GeometryScript_AssetUtils;B=u.GeometryScript_BoneWeights;Q=u.GeometryScript_MeshQueries;L=u.GeometryScript_List
cfg=json.loads((R/'Content/ColdSteelData/modular_outfits.json').read_text(encoding='utf-8-sig'))
paths={}
for source,p in cfg['profiles'].items():
    if p['rig_profile']=='Body':paths['Body']=p['native_bare_skin']
    if 'EquipmentFit20261003/SK_Jason_Base' in source:paths['Jason']=p['native_bare_skin']
for key,path in paths.items():
    mesh=u.load_asset(path)
    if not mesh:raise RuntimeError('Missing body '+path)
    dm,status=G.copy_mesh_from_skeletal_mesh(mesh,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD())
    if status!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Cannot read body '+path)
    _,ps,_=Q.get_all_vertex_positions(dm,False);ps=L.convert_vector_list_to_array(ps)
    _,fs,_=Q.get_all_triangle_indices(dm,False);fs=L.convert_triangle_list_to_array(fs)
    _,bones=B.get_all_bones_info(dm);names={b.index:str(b.name) for b in bones}
    def xyz(v):return [v.x,v.y,v.z]
    d=dict(source=path,skeleton=mesh.skeleton.get_path_name(),positions=[xyz(v) for v in ps],triangles=[xyz(v) for v in fs],uv=[],normals=[],triangle_materials=[],weights=[],
           bones={str(b.name):dict(index=b.index,parent=b.parent_index,position=xyz(b.world_transform.translation),axes=[xyz(b.world_transform.transform_location(v)-b.world_transform.translation) for v in (u.Vector(1,0,0),u.Vector(0,1,0),u.Vector(0,0,1))]) for b in bones},
           materials=[s.material_interface.get_path_name() for s in mesh.materials],material_slots=[str(s.material_slot_name) for s in mesh.materials])
    for i in range(len(fs)):
        a,b,c,_=Q.get_triangle_u_vs(dm,0,i);_,x,y,z,_=Q.get_triangle_normals(dm,i)
        d['uv'].append([[v.x,v.y] for v in (a,b,c)]);d['normals'].append([xyz(v) for v in (x,y,z)])
        material,_=u.GeometryScript_Materials.get_triangle_material_id(dm,i);d['triangle_materials'].append(material)
    for i in range(len(ps)):
        _,weights,_=B.get_vertex_bone_weights(dm,i);d['weights'].append({names[v.bone_index]:v.weight for v in weights if v.weight>0})
    (OUT/(key+'.json')).write_text(json.dumps(d,separators=(',',':')))
    print('ST6_BODY_INPUT',key,len(ps),len(fs),flush=True)
