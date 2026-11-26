"""Read the two current native head surfaces and attachment frames for authoring."""
import json,hashlib,gc
from pathlib import Path
import unreal as u
P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/ModernTacticalSet20261113/HelmetDetailR1';O=R/'Inputs'
O.mkdir(parents=True,exist_ok=True)
read=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
cfg=read(P/'Content/ColdSteelData/player_body.json');item=read(P/'Content/ColdSteelData/items.json')['ue_modern_tactical_helmet']
G,Q,B,L=u.GeometryScript_AssetUtils,u.GeometryScript_MeshQueries,u.GeometryScript_BoneWeights,u.GeometryScript_List
xyz=lambda v:[v.x,v.y,v.z]
rows=[];before={}
for rig,profile in [('Jason',cfg),('Kaitlin',cfg['body_variants']['kaitlin'])]:
    before[rig]=profile['head_equipment']['ue_modern_tactical_helmet']
    paths={'Head':profile['heads'][profile['default_head']]['mesh'],'Body':profile['body_mesh']}
    for kind,path in paths.items():
        mesh=u.load_asset(path)
        if not mesh:raise RuntimeError('Missing native source '+path)
        dm,status=G.copy_mesh_from_skeletal_mesh(mesh,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD())
        if status!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Cannot read '+path)
        _,bs=B.get_all_bones_info(dm)
        bones={str(b.name):dict(index=b.index,parent=b.parent_index,position=xyz(b.world_transform.translation),axes=[xyz(b.world_transform.transform_location(v)-b.world_transform.translation) for v in [u.Vector(1,0,0),u.Vector(0,1,0),u.Vector(0,0,1)]]) for b in bs}
        file=O/(rig+'_'+kind+'.json');disk=P/'Content'/(path.split('.')[0].removeprefix('/Game/')+'.uasset');sha=hashlib.sha256(disk.read_bytes()).hexdigest()
        d=dict(source=path,sha256=sha,bones=bones)
        if kind=='Head':
            _,ps,_=Q.get_all_vertex_positions(dm,False);_,fs,_=Q.get_all_triangle_indices(dm,False)
            d.update(positions=[xyz(v) for v in L.convert_vector_list_to_array(ps)],triangles=[xyz(f) for f in L.convert_triangle_list_to_array(fs)])
        file.write_text(json.dumps(d,separators=(',',':')),encoding='utf-8');rows.append(dict(rig=rig,kind=kind,file=str(file),source=path,sha256=sha));print('HELMET_NATIVE_READ',rig,kind,flush=True)
        del d,dm,mesh;gc.collect();u.SystemLibrary.collect_garbage()
(R/'captured.json').write_text(json.dumps(dict(completed=True,rows=rows),indent=2),encoding='utf-8')
if not (R/'before.json').exists():(R/'before.json').write_text(json.dumps(dict(head_equipment=before,item=item),ensure_ascii=False,indent=2),encoding='utf-8')
