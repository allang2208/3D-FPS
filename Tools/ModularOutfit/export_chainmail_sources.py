"""Read the current equipped shirt meshes into isolated chainmail author inputs."""
import json
from pathlib import Path
import unreal as u

P=Path('D:/FPS3D/FPSGAME')
R=P/'SourceAssets/ChainmailShirt20260928'
Q=u.GeometryScript_MeshQueries; B=u.GeometryScript_BoneWeights; G=u.GeometryScript_AssetUtils


def xyz(v): return [v.x,v.y,v.z]


def main():
    out=R/'Sources';out.mkdir(parents=True,exist_ok=True)
    config=json.loads((P/'Content/ColdSteelData/modular_outfits.json').read_text(encoding='utf-8-sig'))
    sources=config['items']['ue_field_sweater']['rig_meshes']
    for name,path in sources.items():
        mesh=u.load_asset(path)
        if not mesh: raise RuntimeError('Missing current shirt '+path)
        dm,status=G.copy_mesh_from_skeletal_mesh(mesh,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD())
        if status!=u.GeometryScriptOutcomePins.SUCCESS: raise RuntimeError('Cannot read shirt '+name)
        _,bones=B.get_all_bones_info(dm); names={b.index:str(b.name) for b in bones}
        _,positions,_=Q.get_all_vertex_positions(dm,False)
        _,triangles,_=Q.get_all_triangle_indices(dm,False)
        ps=u.GeometryScript_List.convert_vector_list_to_array(positions)
        ts=u.GeometryScript_List.convert_triangle_list_to_array(triangles)
        faces=[]; normals=[]; uv=[]
        for i,t in enumerate(ts):
            a,b,c,valid=Q.get_triangle_u_vs(dm,0,i)
            if not valid: raise RuntimeError('Missing shirt UV '+name)
            _,n0,n1,n2,valid=Q.get_triangle_normals(dm,i)
            if not valid: raise RuntimeError('Missing shirt normals '+name)
            faces.append(xyz(t));uv.append([[v.x,v.y] for v in (a,b,c)]);normals.append([xyz(v) for v in (n0,n1,n2)])
        used=sorted({v for f in faces for v in f});remap={v:i for i,v in enumerate(used)};weights=[]
        for i in used:
            _,ws,valid=B.get_vertex_bone_weights(dm,i)
            if not valid: raise RuntimeError('Missing shirt weights '+name)
            weights.append({names[w.bone_index]:w.weight for w in ws if w.weight>0})
        data=dict(profile=name,source=path,binding_source=path,skeleton=mesh.get_editor_property('skeleton').get_path_name(),
                  positions=[xyz(ps[i]) for i in used],weights=weights,
                  triangles=[[remap[v] for v in f] for f in faces],normals=normals,uv=uv,triangle_materials=[0]*len(faces),
                  bones={str(b.name):dict(index=b.index,parent=b.parent_index,position=xyz(b.world_transform.translation),
                      axes=[xyz(b.world_transform.transform_location(v)-b.world_transform.translation)
                            for v in (u.Vector(1,0,0),u.Vector(0,1,0),u.Vector(0,0,1))]) for b in bones})
        (out/(name+'.json')).write_text(json.dumps(data,separators=(',',':')),encoding='utf-8')
        print('CHAINMAIL_NATIVE_SOURCE',name,len(faces),flush=True)
    (R/'native-sources.json').write_text(json.dumps(sources,indent=2)+'\n',encoding='utf-8')
    print('CHAINMAIL_SOURCE_EXPORT_COMPLETE',len(sources),flush=True)


if __name__=='__main__': main()
