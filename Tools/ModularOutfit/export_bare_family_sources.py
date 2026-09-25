"""Read current first-person native surfaces/binds for the accepted V6 rollout."""
import hashlib,json
from pathlib import Path
import unreal as u

PROJECT=Path('D:/FPS3D/FPSGAME')
ROOT=PROJECT/'SourceAssets/ModularOutfit20260925/BareArmsFamilyV6'
OUT=ROOT/'Sources';OUT.mkdir(parents=True,exist_ok=True)
config=json.loads((PROJECT/'Content/ColdSteelData/modular_outfits.json').read_text(encoding='utf-8-sig'))
Q=u.GeometryScript_MeshQueries;B=u.GeometryScript_BoneWeights;G=u.GeometryScript_AssetUtils
def xyz(v):return [v.x,v.y,v.z]
completed=0
for path,profile in config['profiles'].items():
    key=profile['rig_profile']
    if key=='Body' or (OUT/(key+'.json')).exists():continue
    asset=u.load_asset(path)
    if not asset:raise RuntimeError('Missing native source '+key)
    dm,status=G.copy_mesh_from_skeletal_mesh(asset,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD())
    if status!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Cannot read '+key)
    _,bones=B.get_all_bones_info(dm);names={b.index:str(b.name) for b in bones}
    _,positions,_=Q.get_all_vertex_positions(dm,False);ps=u.GeometryScript_List.convert_vector_list_to_array(positions)
    _,triangles,_=Q.get_all_triangle_indices(dm,False);ts=u.GeometryScript_List.convert_triangle_list_to_array(triangles)
    armids=profile['hide_source_materials'];faces=[];uvs=[];ns=[];materials=[]
    for i,t in enumerate(ts):
        mat,valid=u.GeometryScript_Materials.get_triangle_material_id(dm,i)
        if not valid or mat not in armids:continue
        a,b,c,valid=Q.get_triangle_u_vs(dm,0,i)
        if not valid:raise RuntimeError('Missing native UV '+key)
        _,n0,n1,n2,valid=Q.get_triangle_normals(dm,i)
        if not valid:raise RuntimeError('Missing native normals '+key)
        faces.append(xyz(t));uvs.append([[v.x,v.y] for v in (a,b,c)])
        ns.append([xyz(v) for v in (n0,n1,n2)]);materials.append(mat)
    ids=sorted({v for t in faces for v in t});mapping={v:i for i,v in enumerate(ids)};weights=[]
    for i in ids:
        _,ws,valid=B.get_vertex_bone_weights(dm,i)
        if not valid:raise RuntimeError('Missing native bindings '+key)
        weights.append({names[w.bone_index]:w.weight for w in ws if w.weight>0})
    source_file=PROJECT/'Content'/(path.split('.')[0].removeprefix('/Game/')+'.uasset')
    data={'profile':key,'source':path,'skeleton':asset.skeleton.get_path_name(),
        'source_sha256':hashlib.sha256(source_file.read_bytes()).hexdigest(),
        'arm_materials':armids,'positions':[xyz(ps[i]) for i in ids],
        'weights':weights,'triangles':[[mapping[v] for v in t] for t in faces],
        'uv':uvs,'normals':ns,'triangle_materials':materials,
        'bones':{str(b.name):{'index':b.index,'parent':b.parent_index,'position':xyz(b.world_transform.translation),
            'axes':[xyz(b.world_transform.transform_location(v)-b.world_transform.translation)
                    for v in (u.Vector(1,0,0),u.Vector(0,1,0),u.Vector(0,0,1))]} for b in bones}}
    (OUT/(key+'.json')).write_text(json.dumps(data,separators=(',',':')),encoding='utf-8')
    print('BARE_FAMILY_SOURCE',key,len(ids),len(faces))
    completed+=1
    if completed>=20:break
if not (ROOT/'geometry_uv_api.txt').exists():
    (ROOT/'geometry_uv_api.txt').write_text(str(u.GeometryScriptSimpleMeshBuffers.__doc__)+'\n'+
        '\n'.join(n+'\n'+str(getattr(u.GeometryScript_UVs,n).__doc__) for n in dir(u.GeometryScript_UVs) if 'uv' in n.lower()),encoding='utf-8')
print('BARE_FAMILY_SOURCE_BATCH',completed)
