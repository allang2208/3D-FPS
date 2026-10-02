"""Read the current M16 glove surfaces for the matching left-hand binding repair."""
import hashlib, json
from pathlib import Path
import unreal as u

P=Path(u.Paths.project_dir()).resolve()
O=Path(__file__).parent
OUT=O/'Input/Outfits'
OUT.mkdir(parents=True,exist_ok=True)
rows=json.loads((O/'outfit_sources.json').read_text())
Q,B,G=u.GeometryScript_MeshQueries,u.GeometryScript_BoneWeights,u.GeometryScript_AssetUtils

def xyz(v):
    return [v.x,v.y,v.z]

for row in rows:
    if any(s in row['path'] for s in ('OriginalGloves','Chainmail','Charcoal','FieldSweater')):
        continue
    a=u.load_asset(row['path'])
    dm,status=G.copy_mesh_from_skeletal_mesh(a,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD())
    if status!=u.GeometryScriptOutcomePins.SUCCESS:
        raise RuntimeError('Cannot read '+row['path'])
    _,bones=B.get_all_bones_info(dm);names={b.index:str(b.name) for b in bones}
    _,pos,_=Q.get_all_vertex_positions(dm,False);ps=u.GeometryScript_List.convert_vector_list_to_array(pos)
    weights=[]
    for i in range(len(ps)):
        _,ws,valid=B.get_vertex_bone_weights(dm,i)
        if not valid:
            raise RuntimeError('Missing binding '+row['path'])
        weights.append({names[w.bone_index]:w.weight for w in ws if w.weight>0})
    file=P/'Content'/(row['path'].split('.')[0].removeprefix('/Game/')+'.uasset')
    data=dict(path=row['path'],skeleton=a.skeleton.get_path_name(),source_sha256=hashlib.sha256(file.read_bytes()).hexdigest(),
        positions=[xyz(v) for v in ps],weights=weights,
        bones={str(b.name):dict(index=b.index,parent=b.parent_index,position=xyz(b.world_transform.translation),
            axes=[xyz(b.world_transform.transform_location(v)-b.world_transform.translation)
            for v in (u.Vector(1,0,0),u.Vector(0,1,0),u.Vector(0,0,1))]) for b in bones})
    key=Path(row['path'].split('.')[0]).name
    (OUT/(key+'.json')).write_text(json.dumps(data,separators=(',',':')),encoding='utf-8')
    u.log('CLOVEN_M16_OUTFIT_INPUT '+key+' vertices='+str(len(ps)))
u.log('CLOVEN_M16_OUTFIT_GEOMETRY_READ')
