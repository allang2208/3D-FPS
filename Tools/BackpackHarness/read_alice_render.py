"""Read ALICE's active mesh, source/render LODs and material visibility rules."""
import json
from pathlib import Path
import unreal as u

P=Path('D:/FPS3D/FPSGAME')
R=P/'SourceAssets/BackpacksReview20261021'
job=json.loads((R/'alice_read_job.json').read_text())
out=R/'FacingRepair20261022'/job['phase'];out.mkdir(parents=True,exist_ok=True)
cfg=json.loads((P/'Content/ColdSteelData/player_body.json').read_text(encoding='utf-8-sig'))
mount=cfg['outfits']['ue_portable_backpack'];asset=u.load_asset(mount['world_static_mesh'])
S=u.get_editor_subsystem(u.StaticMeshEditorSubsystem) or u.new_object(u.StaticMeshEditorSubsystem)
Q,G,L=u.GeometryScript_MeshQueries,u.GeometryScript_AssetUtils,u.GeometryScript_List
vec=lambda v:[v.x,v.y,v.z]
materials=[{'slot':str(m.material_slot_name),'asset':m.material_interface.get_path_name()} for m in asset.static_materials]
receipt={'asset':asset.get_path_name(),'mount':mount,
         'lod_count':G.get_num_static_mesh_lods_of_type(asset,u.GeometryScriptLODType.SOURCE_MODEL),
         'nanite_settings':str(asset.get_editor_property('nanite_settings')),'materials':[],'meshes':[]}
for row in materials:
    mat=u.load_asset(row['asset']);chain=[]
    while mat:
        info={'asset':mat.get_path_name(),'class':mat.get_class().get_name()}
        if isinstance(mat,u.Material):
            info.update(two_sided=mat.get_editor_property('two_sided'),blend_mode=str(mat.get_editor_property('blend_mode')),inputs={})
            for prop in ('MP_OPACITY','MP_OPACITY_MASK','MP_WORLD_POSITION_OFFSET'):
                info['inputs'][prop]=str(u.MaterialEditingLibrary.get_material_property_input_node(mat,getattr(u.MaterialProperty,prop)))
            chain.append(info);break
        info['overrides']=str(mat.get_editor_property('base_property_overrides'));chain.append(info)
        mat=mat.get_editor_property('parent')
    receipt['materials'].append(dict(row,chain=chain))
for lod in range(receipt['lod_count']):
    for kind,typ in [('source',u.GeometryScriptLODType.SOURCE_MODEL),('render',u.GeometryScriptLODType.RENDER_DATA)]:
        dm,status=G.copy_mesh_from_static_mesh(asset,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD(lod_type=typ,lod_index=lod))
        if status!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Cannot read ALICE '+kind)
        _,points,_=Q.get_all_vertex_positions(dm,False);_,faces,_=Q.get_all_triangle_indices(dm,False)
        data={'asset':asset.get_path_name(),'lod':lod,'kind':kind,'materials':materials,
              'revision':u.EditorAssetLibrary.get_metadata_tag(asset,'AliceSidePocketsRevision'),
              'front_face_convention':u.EditorAssetLibrary.get_metadata_tag(asset,'AliceFrontFaceConvention'),
              'positions':[vec(v) for v in L.convert_vector_list_to_array(points)],
              'triangles':[vec(t) for t in L.convert_triangle_list_to_array(faces)],'uv':[],'normals':[],'triangle_materials':[]}
        for ti in range(len(data['triangles'])):
            a,b,c,valid=Q.get_triangle_u_vs(dm,0,ti);_,na,nb,nc,nvalid=Q.get_triangle_normals(dm,ti)
            if not valid or not nvalid:raise RuntimeError('Missing ALICE attributes')
            data['uv'].append([[v.x,v.y] for v in (a,b,c)]);data['normals'].append([vec(n) for n in (na,nb,nc)])
            data['triangle_materials'].append(u.GeometryScript_Materials.get_triangle_material_id(dm,ti)[0])
        (out/(kind+'_lod'+str(lod)+'.json')).write_text(json.dumps(data,separators=(',',':')))
        receipt['meshes'].append({'kind':kind,'lod':lod,'triangles':len(data['triangles']),'revision':data['revision']})
        print('ALICE_READ',kind,lod,len(data['triangles']),flush=True)
        del dm,data
        u.SystemLibrary.collect_garbage()
(out/'receipt.json').write_text(json.dumps(receipt,indent=2))
print('ALICE_READ_COMPLETE',flush=True)
