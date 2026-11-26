"""Read saved native shirt geometry, never live pose components."""
import json,hashlib,gc
from pathlib import Path
import unreal as u
P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/ModernTacticalSet20261113/CombatShirtR1'
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
plan=read(R/'plan.json');record=read(R/'captured.json') if (R/'captured.json').exists() else {}
G,Q,L,B=u.GeometryScript_AssetUtils,u.GeometryScript_MeshQueries,u.GeometryScript_List,u.GeometryScript_BoneWeights
def xyz(v):return [v.x,v.y,v.z]
for row in plan['rows']:
    path=row['source'];digest=hashlib.sha256((P/'Content'/(path.split('.')[0][6:]+'.uasset')).read_bytes()).hexdigest()
    file=R/'Inputs'/row['file']
    if record.get(path,{}).get('sha256')==digest and file.exists():continue
    asset=u.load_asset(path)
    if not asset:raise RuntimeError('Missing native shirt '+path)
    dm,status=G.copy_mesh_from_skeletal_mesh(asset,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD())
    if status!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Cannot capture '+path)
    _,vs,_=Q.get_all_vertex_positions(dm,False);vs=L.convert_vector_list_to_array(vs)
    _,fs,_=Q.get_all_triangle_indices(dm,False);fs=L.convert_triangle_list_to_array(fs)
    _,bones=B.get_all_bones_info(dm)
    d=dict(source=path,source_sha256=digest,rig=row['rig'],positions=[xyz(v) for v in vs],triangles=[xyz(f) for f in fs],weights=[],normals=[],uv=[],triangle_materials=[],
        materials=[m.material_interface.get_path_name() if m.material_interface else '' for m in asset.materials],material_slots=[str(m.material_slot_name) for m in asset.materials],
        bones=[dict(name=str(b.name),index=b.index,parent=b.parent_index,position=xyz(b.world_transform.translation),axes=[xyz(b.world_transform.transform_location(v)-b.world_transform.translation) for v in [u.Vector(1,0,0),u.Vector(0,1,0),u.Vector(0,0,1)]]) for b in bones])
    for i in range(len(vs)):
        _,ws,valid=B.get_vertex_bone_weights(dm,i)
        if not valid:raise RuntimeError('Invalid native weights '+path)
        d['weights'].append([[w.bone_index,w.weight] for w in ws if w.weight>0])
    for i in range(len(fs)):
        a,b,c,_=Q.get_triangle_u_vs(dm,0,i);_,na,nb,nc,_=Q.get_triangle_normals(dm,i)
        d['uv'].append([[v.x,v.y] for v in (a,b,c)]);d['normals'].append([xyz(v) for v in (na,nb,nc)]);d['triangle_materials'].append(u.GeometryScript_Materials.get_triangle_material_id(dm,i)[0])
    file.write_text(json.dumps(d,separators=(',',':')),encoding='utf-8');record[path]=dict(file=str(file),sha256=digest,rig=row['rig'])
    (R/'captured.json').write_text(json.dumps(record,indent=2),encoding='utf-8')
    print('TS01_SHIRT_CAPTURED',len(record),len(plan['rows']),asset.get_name(),flush=True)
    del d,dm,asset,vs,fs,bones;gc.collect();u.SystemLibrary.collect_garbage()
(R/'capture-complete.json').write_text(json.dumps(dict(completed=True,count=len(record))),encoding='utf-8')
