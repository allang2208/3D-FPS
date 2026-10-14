"""Read the current 201 factory reference and three fitted rear grips."""
import array,json,hashlib
from pathlib import Path
import unreal as u
O=Path(__file__).parent;(O/'Input').mkdir(parents=True,exist_ok=True)
P=Path(u.Paths.project_dir()).resolve();AU,Q,LU,M=u.GeometryScript_AssetUtils,u.GeometryScript_MeshQueries,u.GeometryScript_List,u.GeometryScript_Materials
def pick(r,c):return next(x for x in r if isinstance(x,c)) if isinstance(r,tuple) else r
def sha(p):return hashlib.sha256((P/'Content'/(p.removeprefix('/Game/')+'.uasset')).read_bytes()).hexdigest()
def material(m):
    L=u.MaterialEditingLibrary;base=m.get_base_material()
    scalars={str(n):L.get_material_instance_scalar_parameter_value(m,n) for n in L.get_scalar_parameter_names(base)} if isinstance(m,u.MaterialInstanceConstant) else {}
    custom=[]
    for n in L.get_material_expressions(base):
        if isinstance(n,u.MaterialExpressionCustom):
            desc=str(n.get_editor_property('description'))
            if any(s in desc.lower() for s in ('neck','normal','roughness')):custom.append({'description':desc,'code':n.get_editor_property('code')})
    return {'path':m.get_path_name(),'base':base.get_path_name(),'scalars':scalars,'custom':custom}
bodypath='/Game/Weapons/LMG201/Cover10/SK_LMG201_Cover10';body=u.load_asset(bodypath)
dm=u.DynamicMesh();AU.copy_mesh_from_skeletal_mesh(body,dm,u.GeometryScriptCopyMeshFromAssetOptions(apply_build_settings=False),u.GeometryScriptMeshReadLOD(lod_type=u.GeometryScriptLODType.SOURCE_MODEL,lod_index=0))
bones=next(x for x in u.GeometryScript_BoneWeights.get_all_bones_info(dm) if isinstance(x,(list,u.Array)))
root=next(b.world_transform for b in bones if str(b.name)=='WPN_root')
slots=body.materials;factory={i for i,s in enumerate(slots) if 'FactoryRearGrip' in str(s.material_slot_name)}
tris=LU.convert_triangle_list_to_array(pick(Q.get_all_triangle_indices(dm,True),u.GeometryScriptTriangleList))
mids=LU.convert_index_list_to_array(pick(M.get_all_triangle_material_i_ds(dm),u.GeometryScriptIndexList))
ref={'factory':{'vertices':{},'triangles':[]},'receiver':{'vertices':{},'triangles':[]},'body_path':bodypath,'body_sha256':sha(bodypath),'factory_materials':{}}
for ti,t in enumerate(tris):
    if mids[ti] in factory:category='factory'
    elif any(s in str(slots[mids[ti]].material_slot_name) for s in ('Receiver','Trigger','G43_EdgeCoat')):category='receiver'
    else:continue
    ids=[t.x,t.y,t.z];points=[]
    for v in ids:
        p=root.inverse_transform_location(Q.get_vertex_position(dm,v)[0]);points.append([p.x,-p.y,p.z])
    if category=='receiver' and not any(-.045<p[0]<.045 and -.07<p[1]<.09 and -.035<p[2]<.025 for p in points):continue
    for vi,p in zip(ids,points):ref[category]['vertices'][vi]=p
    ref[category]['triangles'].append(ids)
    if category=='factory':
        name=str(slots[mids[ti]].material_slot_name)
        if name not in ref['factory_materials']:ref['factory_materials'][name]=material(slots[mids[ti]].material_interface)
(O/'Input/factory.json').write_text(json.dumps(ref))
summary={}
for kind,variant in [('phantom','phantom_reargrip'),('balanced','balanced_reargrip'),('stable','stable_antislip_reargrip')]:
    path='/Game/Weapons/LMG201/Accessories22/Meshes/SM_LMG201_'+variant;mesh=u.load_asset(path)
    d=u.DynamicMesh();AU.copy_mesh_from_static_mesh(mesh,d,u.GeometryScriptCopyMeshFromAssetOptions(apply_build_settings=False),u.GeometryScriptMeshReadLOD(lod_type=u.GeometryScriptLODType.SOURCE_MODEL,lod_index=0))
    if Q.get_has_vertex_id_gaps(d) or Q.get_has_triangle_id_gaps(d):raise RuntimeError('Source index gaps')
    vs=LU.convert_vector_list_to_array(pick(Q.get_all_vertex_positions(d,True),u.GeometryScriptVectorList))
    ts=LU.convert_triangle_list_to_array(pick(Q.get_all_triangle_indices(d,True),u.GeometryScriptTriangleList))
    mids=LU.convert_index_list_to_array(pick(M.get_all_triangle_material_i_ds(d),u.GeometryScriptIndexList))
    pos=array.array('f',(c for v in vs for c in (v.x,v.y,v.z)));tri=array.array('i',(c for v in ts for c in (v.x,v.y,v.z)))
    normals=array.array('f');mask=array.array('f')
    for ti in range(len(ts)):
        for n in [x for x in Q.get_triangle_normals(d,ti) if isinstance(x,u.Vector)][:3]:normals.extend((n.x,n.y,n.z))
        for uv in Q.get_triangle_u_vs(d,4,ti)[:3]:mask.extend((uv.x,uv.y))
    row={'path':path,'sha256':sha(path),'vertices':len(vs),'triangles':len(ts),'uv_sets':Q.get_num_uv_sets(d),'slots':[str(s.material_slot_name) for s in mesh.static_materials],
         'materials':[s.material_interface.get_path_name() for s in mesh.static_materials],'material_details':[material(s.material_interface) for s in mesh.static_materials]}
    with (O/'Input'/(kind+'.bin')).open('wb') as f:
        f.write((json.dumps(row)+'\n').encode())
        for a in (pos,tri,array.array('i',list(mids)[:len(ts)]),normals,mask):a.tofile(f)
    summary[kind]=row;(O/'Input/current.json').write_text(json.dumps(summary,indent=2))
    print('JUNCTION_SOURCE_READ',kind,len(ts),flush=True)
print('JUNCTION_FACTORY_READ',len(ref['factory']['triangles']),len(ref['receiver']['triangles']),flush=True)
