"""Save scoped new fit assets; retain source UVs, material slots, masks and bones."""
import gc,hashlib,json,os
from array import array
from pathlib import Path
import unreal as u
P=Path('D:/FPS3D/FPSGAME');R=Path(os.environ.get('BACKPACK_FIT_RUN_DIR',P/'SourceAssets/BackpackFit20261024/ContactFitR3'))
read=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
def main():
    plan=read(R/'authored.json');receipt=R/'saved_assets.json'
    saved=read(receipt) if receipt.exists() else {'statics':{},'meshes':{}}
    limit=int(os.environ.get('BACKPACK_FIT_BATCH_SIZE','24'));count=0
    E,G,L=u.EditorAssetLibrary,u.GeometryScript_AssetUtils,u.GeometryScript_List
    editor=u.get_editor_subsystem(u.SkeletalMeshEditorSubsystem) or u.new_object(u.SkeletalMeshEditorSubsystem)
    for kind,rows in [('statics',plan['statics']),('meshes',plan['rows'])]:
        for row in rows:
            key=row['asset'];raw=Path(row['positions']).read_bytes();digest=hashlib.sha256(raw).hexdigest()
            previous=saved[kind].get(key,{})
            if previous.get('geometry_sha256')==digest and E.does_asset_exist(key):continue
            if not key.startswith('/Game/Characters/BackpackFit20261024/'+R.name+'/'):raise RuntimeError('Outside fit revision '+key)
            source_file=P/'Content'/(row['source'].split('.')[0].removeprefix('/Game/')+'.uasset')
            if hashlib.sha256(source_file.read_bytes()).hexdigest()!=row['source_sha256']:raise RuntimeError('Source changed during fitting '+row['source'])
            if E.does_asset_exist(key):raise RuntimeError('Preserve unreceipted target '+key)
            source=u.load_asset(row['source']);skeletal=kind=='meshes'
            target=E.duplicate_asset(row['source'].split('.')[0],key)
            if not target:raise RuntimeError('Cannot duplicate '+key)
            if skeletal:
                dm,status=G.copy_mesh_from_skeletal_mesh(source,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD())
            else:
                dm,status=G.copy_mesh_from_static_mesh(source,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD())
            if status!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Cannot read source '+key)
            values=array('f');values.frombytes(raw);it=iter(values);vectors=[u.Vector(x,y,z) for x,y,z in zip(it,it,it)]
            u.GeometryScript_MeshEdits.set_all_mesh_vertex_positions(dm,L.convert_array_to_vector_list(vectors))
            u.GeometryScript_Normals.recompute_normals(dm,u.GeometryScriptCalculateNormalsOptions())
            options=u.GeometryScriptCopyMeshToAssetOptions(enable_recompute_normals=False,enable_recompute_tangents=True)
            if skeletal:
                lods=editor.get_lod_count(target)
                _,status=G.copy_mesh_to_skeletal_mesh(dm,target,options,u.GeometryScriptMeshWriteLOD(lod_index=0))
                if status==u.GeometryScriptOutcomePins.SUCCESS and lods>1:
                    if not editor.regenerate_lod(target,lods,True,False):raise RuntimeError('LOD rebuild failed '+key)
                target.set_editor_property('positive_bounds_extension',u.Vector(6,6,6));target.set_editor_property('negative_bounds_extension',u.Vector(6,6,6))
            else:
                _,status=G.copy_mesh_to_static_mesh(dm,target,options,u.GeometryScriptMeshWriteLOD())
            if status!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Geometry write failed '+key)
            E.set_metadata_tag(target,'BackpackContactRevision',R.name);E.set_metadata_tag(target,'FitSourceSHA256',digest)
            target.modify()
            if not E.save_loaded_asset(target,False):raise RuntimeError('Asset save failed '+key)
            saved[kind][key]={'asset':target.get_path_name(),'geometry_sha256':digest,'source':row['source'],'source_sha256':row['source_sha256'],'saved':True}
            receipt.write_text(json.dumps(saved,indent=2));count+=1
            print('BACKPACK_FIT_SAVED',kind,key,flush=True)
            del source,target,dm,vectors,values,options;gc.collect();u.SystemLibrary.collect_garbage()
            if count>=limit:break
        if count>=limit:break
    saved['completed']=all(saved[kind].get(row['asset'],{}).get('geometry_sha256')==hashlib.sha256(Path(row['positions']).read_bytes()).hexdigest()
                           for kind,rows in [('statics',plan['statics']),('meshes',plan['rows'])] for row in rows)
    receipt.write_text(json.dumps(saved,indent=2));print('BACKPACK_FIT_SAVE_COMPLETE',saved['completed'],flush=True)
main()
gc.collect();u.SystemLibrary.collect_garbage()
