"""Read actual saved geometry and deformation masks; no asset mutation or gameplay."""
import gc,hashlib,json,os
from array import array
from pathlib import Path
import unreal as u
P=Path('D:/FPS3D/FPSGAME');R=Path(os.environ.get('BACKPACK_FIT_RUN_DIR',P/'SourceAssets/BackpackFit20261024/ContactAuditR1'))
plan=json.loads((R/'plan.json').read_text(encoding='utf-8'))
G,Q,L,B=u.GeometryScript_AssetUtils,u.GeometryScript_MeshQueries,u.GeometryScript_List,u.GeometryScript_BoneWeights
status=R/'capture_status.json';status.write_text('{"state":"running"}')
def main():
    records={}
    previous=json.loads((R/'captured.json').read_text()) if (R/'captured.json').exists() else {}
    def save_array(path,values,kind):
        data=array(kind,values);path.write_bytes(data.tobytes())
    try:
        for row in plan['assets']:
            path=row['path'];package=P/'Content'/(path.split('.')[0].removeprefix('/Game/')+'.uasset')
            digest=hashlib.sha256(package.read_bytes()).hexdigest();folder=R/'Capture'/row['key'];folder.mkdir(exist_ok=True)
            record_file=folder/'mesh.json'
            cached=previous.get(path,{})
            if cached.get('package_sha256')==digest and (Path(cached['folder'])/'positions.bin').exists():
                records[path]=cached;continue
            if record_file.exists():
                old=json.loads(record_file.read_text())
                if old.get('package_sha256')==digest:
                    records[path]=old;continue
            asset=u.load_asset(path)
            if not asset:raise RuntimeError('Cannot load '+path)
            skeletal=isinstance(asset,u.SkeletalMesh)
            options=u.GeometryScriptCopyMeshFromAssetOptions()
            fn=G.copy_mesh_from_skeletal_mesh if skeletal else G.copy_mesh_from_static_mesh
            dm,outcome=fn(asset,u.DynamicMesh(),options,u.GeometryScriptMeshReadLOD())
            if outcome!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Cannot read '+path)
            _,points,_=Q.get_all_vertex_positions(dm,False);points=L.convert_vector_list_to_array(points)
            _,faces,_=Q.get_all_triangle_indices(dm,False);faces=L.convert_triangle_list_to_array(faces)
            save_array(folder/'positions.bin',(c for v in points for c in (v.x,v.y,v.z)),'f')
            save_array(folder/'triangles.bin',(int(c) for v in faces for c in (v.x,v.y,v.z)),'i')
            mask_valid=False
            if 'pack' in row['roles']:
                _,colors,valid,gaps=u.GeometryScript_VertexColors.get_mesh_per_vertex_colors(dm,False)
                if valid and not gaps:
                    colors=L.convert_color_list_to_array(colors);save_array(folder/'mask.bin',(c.r for c in colors),'f');mask_valid=True
            record={'path':path,'key':row['key'],'folder':str(folder),'package_sha256':digest,'vertices':len(points),'triangles':len(faces),
                    'skeletal':skeletal,'mask_valid':mask_valid,'roles':row['roles'],'geometry':'saved SourceModel; exact full geometry for Nanite statics'}
            if 'body' in row['roles']:
                _,bones=B.get_all_bones_info(dm)
                record['bones']=[{'index':b.index,'name':str(b.name),'parent':b.parent_index,'position':[b.world_transform.translation.x,b.world_transform.translation.y,b.world_transform.translation.z],
                                  'rotation':[getattr(b.world_transform.rotation,c) for c in 'xyzw']} for b in bones]
            if skeletal and 'pack' in row['roles']:
                render,render_status=fn(asset,u.DynamicMesh(),options,u.GeometryScriptMeshReadLOD(lod_type=u.GeometryScriptLODType.RENDER_DATA,lod_index=0))
                if render_status!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Cannot read actual built LOD '+path)
                _,rp,_=Q.get_all_vertex_positions(render,False);rp=L.convert_vector_list_to_array(rp)
                _,rt,_=Q.get_all_triangle_indices(render,False);rt=L.convert_triangle_list_to_array(rt)
                save_array(folder/'render_positions.bin',(c for v in rp for c in (v.x,v.y,v.z)),'f')
                save_array(folder/'render_triangles.bin',(int(c) for v in rt for c in (v.x,v.y,v.z)),'i')
                record.update(render_vertices=len(rp),render_triangles=len(rt));del render,rp,rt
            record_file.write_text(json.dumps(record,indent=2));records[path]=record
            (R/'captured.json').write_text(json.dumps(records,indent=2))
            print('BACKPACK_FIT_CAPTURED',len(records),len(plan['assets']),path,flush=True)
            del asset,dm,points,faces;gc.collect();u.SystemLibrary.collect_garbage()
        (R/'captured.json').write_text(json.dumps(records,indent=2));status.write_text(json.dumps({'state':'completed','assets':len(records)}))
        # Release reflected value wrappers before UE starts unloading Python types.
        for name in ['colors','bones','points','faces','render','rp','rt','asset','dm']:
            globals().pop(name,None)
        gc.collect();u.SystemLibrary.collect_garbage()
    except Exception as error:
        status.write_text(json.dumps({'state':'failed','error':str(error)}));raise

main()
gc.collect()
u.SystemLibrary.collect_garbage()
