"""Read saved distance LODs in a fresh process, including their deformation attributes."""
import gc,hashlib,json,sys
from pathlib import Path
import unreal as u
sys.path.insert(0,str(Path(__file__).parent));from boot_paths import *
from distance_lods import geometry
A=R/'Audit/DistanceLODs';saved=read(A/'saved.json');report=dict(meshes={},completed=False,rendered=False)
G=u.GeometryScript_AssetUtils;Q=u.GeometryScript_MeshQueries;L=u.GeometryScript_List;B=u.GeometryScript_BoneWeights;sub=u.get_editor_subsystem(u.SkeletalMeshEditorSubsystem)
for path,row in saved['meshes'].items():
    mesh=u.load_asset(path);assert sub.get_lod_count(mesh)==3
    regular='/Jason/' in path;expected=read(R/'materials.json')['materials' if regular else 'robe_materials']
    assert [m.material_interface.get_path_name() for m in mesh.materials]==expected
    lods=[]
    for lod in range(3):
        dm,stats=geometry(mesh,lod);assert stats==row['lods'][lod],(path,lod)
        assert sub.get_lod_build_settings(mesh,lod).use_full_precision_u_vs
        lods.append(stats)
        if regular and lod:
            _,vs,_=Q.get_all_vertex_positions(dm,False);_,fs,_=Q.get_all_triangle_indices(dm,False)
            xyz=lambda v:[v.x,v.y,v.z]
            data=dict(positions=[xyz(v) for v in L.convert_vector_list_to_array(vs)],triangles=[xyz(v) for v in L.convert_triangle_list_to_array(fs)],weights=[],uv=[],normals=[],triangle_materials=[],colors=[[1.,1.,1.,1.] for _ in range(stats['vertices'])])
            weight_file=A/('LOD'+str(lod)+'_render_weights.json')
            assert u.LeatherBootsAuditLibrary.export_render_weights(mesh,lod,str(weight_file))
            native=read(weight_file)['vertices'];by_position={}
            for vertex in native:by_position.setdefault(tuple(vertex['p']),[]).append(vertex['weights'])
            for vi,position in enumerate(data['positions']):
                if vi<len(native):assert position==native[vi]['p'];weights=native[vi]['weights']
                else:
                    candidates=by_position[tuple(position)];weights=candidates[0]
                    assert all(w==weights for w in candidates),'Ambiguous non-manifold render vertex'
                data['weights'].append(weights)
            for ti in range(stats['triangles']):
                a,b,c,ok=Q.get_triangle_u_vs(dm,0,ti);assert ok;data['uv'].append([[v.x,v.y] for v in (a,b,c)])
                _,a,b,c,ok=Q.get_triangle_normals(dm,ti);assert ok;data['normals'].append([xyz(v) for v in (a,b,c)])
                data['triangle_materials'].append(u.GeometryScript_Materials.get_triangle_material_id(dm,ti)[0])
                _,a,b,c,ok=Q.get_triangle_vertex_colors(dm,ti);assert ok
                for vi,color in zip(data['triangles'][ti],(a,b,c)):data['colors'][vi]=[color.r,color.g,color.b,color.a]
            (A/('LOD'+str(lod)+'.json')).write_text(json.dumps(data,separators=(',',':')),encoding='utf-8');del data
        del dm;gc.collect()
    report['meshes'][path]=dict(lods=lods,skeleton=mesh.skeleton.get_path_name(),materials=expected)
assert len(report['meshes'])==2
rows=list(report['meshes'].values());assert rows[0]['lods']==rows[1]['lods'] and rows[0]['skeleton']==rows[1]['skeleton']
report['completed']=True;write(A/'read_back.json',report);print('BOOT_DISTANCE_LODS_READ_COMPLETE',flush=True)
