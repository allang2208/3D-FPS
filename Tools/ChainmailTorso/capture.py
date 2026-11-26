"""Read active third-person mail sources without changing any UE assets."""
import gc, hashlib, json
from pathlib import Path
import unreal as u

P=Path('D:/FPS3D/FPSGAME')
R=P/'SourceAssets/ChainmailTorsoRepair20261021'
G,Q,B,L=u.GeometryScript_AssetUtils,u.GeometryScript_MeshQueries,u.GeometryScript_BoneWeights,u.GeometryScript_List
def write(p,d):
    p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(d,ensure_ascii=False,separators=(',',':')),encoding='utf-8')
def xyz(v): return [v.x,v.y,v.z]
def capture(path,profile):
    mesh=u.load_asset(path)
    if not mesh: raise RuntimeError('Missing source '+path)
    dm,status=G.copy_mesh_from_skeletal_mesh(mesh,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD())
    if status!=u.GeometryScriptOutcomePins.SUCCESS: raise RuntimeError('Cannot read '+path)
    _,vs,_=Q.get_all_vertex_positions(dm,False); _,fs,_=Q.get_all_triangle_indices(dm,False); _,bones=B.get_all_bones_info(dm)
    names={b.index:str(b.name) for b in bones}
    source_file=P/'Content'/(path.split('.')[0].removeprefix('/Game/')+'.uasset')
    d=dict(profile=profile,source=path,binding_source=path,skeleton=mesh.skeleton.get_path_name(),
        source_sha256=hashlib.sha256(source_file.read_bytes()).hexdigest(),
        positions=[xyz(v) for v in L.convert_vector_list_to_array(vs)],triangles=[xyz(f) for f in L.convert_triangle_list_to_array(fs)],
        weights=[],triangle_materials=[],normals=[],uv=[],
        materials=[s.material_interface.get_path_name() for s in mesh.materials],
        material_slots=[str(s.material_slot_name) for s in mesh.materials],
        bones={str(b.name):dict(index=b.index,parent=b.parent_index,position=xyz(b.world_transform.translation),
            axes=[xyz(b.world_transform.transform_location(v)-b.world_transform.translation) for v in (u.Vector(1,0,0),u.Vector(0,1,0),u.Vector(0,0,1))]) for b in bones})
    for i in range(len(d['positions'])):
        _,ws,valid=B.get_vertex_bone_weights(dm,i)
        if not valid: raise RuntimeError('Missing native weights')
        d['weights'].append({names[w.bone_index]:w.weight for w in ws if w.weight>0})
    for i in range(len(d['triangles'])):
        a,b,c,_=Q.get_triangle_u_vs(dm,0,i); _,na,nb,nc,_=Q.get_triangle_normals(dm,i)
        d['uv'].append([[v.x,v.y] for v in (a,b,c)])
        d['normals'].append([xyz(v) for v in (na,nb,nc)])
        d['triangle_materials'].append(u.GeometryScript_Materials.get_triangle_material_id(dm,i)[0])
    write(R/'Sources'/(profile+'.json'),d)
    print('CHAINMAIL_SOURCE',profile,len(d['positions']),len(d['triangles']),flush=True)
    del dm,mesh;gc.collect();u.SystemLibrary.collect_garbage()

cfg=json.loads((P/'Content/ColdSteelData/modular_outfits.json').read_text(encoding='utf-8-sig'))
recipe=cfg['items']['ue_chainmail_shirt']
before=R/'before.json'
if not before.exists():write(before,dict(recipe=recipe))
for profile in ('Body','Jason'):capture(recipe['rig_meshes'][profile],profile)
capture(recipe['owner_body_meshes']['Jason'],'Owner_Jason')
capture('/Game/AsianMale_Jason/Mesh/Body/SKM_Jason_body.SKM_Jason_body','NativeSkin_Jason')
print('CHAINMAIL_CAPTURE_COMPLETE',flush=True)
