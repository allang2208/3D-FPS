"""Read current fitted rear grips for surface authoring, without rendering."""
import array, hashlib, json
from pathlib import Path
import unreal as u

O=Path(__file__).parent; P=Path(u.Paths.project_dir()).resolve()
(O/'Input').mkdir(parents=True,exist_ok=True)
AU,Q,LU,MAT=u.GeometryScript_AssetUtils,u.GeometryScript_MeshQueries,u.GeometryScript_List,u.GeometryScript_Materials
L=u.MaterialEditingLibrary
def pick(r,c): return next(x for x in r if isinstance(x,c)) if isinstance(r,tuple) else r
def disk(p): return P/'Content'/(p.split('.')[0].removeprefix('/Game/')+'.uasset')
def sha(p): return hashlib.sha256(disk(p).read_bytes()).hexdigest()
def read_material(m):
    p=m.get_path_name()
    if p in materials:return
    row={'class':m.get_class().get_name(),'sha256':sha(p),'base':m.get_base_material().get_path_name(),'scalars':{},'textures':{}}
    if isinstance(m,u.MaterialInstanceConstant):
        row['parent']=m.get_editor_property('parent').get_path_name()
        for n in L.get_scalar_parameter_names(m.get_base_material()):
            row['scalars'][str(n)]=L.get_material_instance_scalar_parameter_value(m,n)
        for n in L.get_texture_parameter_names(m.get_base_material()):
            t=L.get_material_instance_texture_parameter_value(m,n)
            row['textures'][str(n)]=t.get_path_name() if t else None
    else:
        row['parameter_names']=[str(n) for n in L.get_scalar_parameter_names(m)]
        row['outputs']={name: str(L.get_material_property_input_node(m,prop)) for name,prop in
            [('normal',u.MaterialProperty.MP_NORMAL),('roughness',u.MaterialProperty.MP_ROUGHNESS),('color',u.MaterialProperty.MP_BASE_COLOR)]}
    materials[p]=row

meshes={}; materials={}
for family in ['M4','AKM','QBZ191','HK416','M16','A762','PKM','LMG201']:
    for kind,variant,name in [('phantom','phantom_reargrip','Phantom'),('balanced','balanced_reargrip','Balanced'),('stable','stable_antislip_reargrip','StableAntiSlip')]:
        if family in ['M4','AKM','QBZ191']:
            path=f'/Game/Weapons/StableAntiSlipRearGrip/Selected91727/{family}/SM_StableAntiSlipRearGrip' if kind=='stable' else f'/Game/Weapons/RearGripFinish20260913/{family}/{kind}/'+('Seam20260914/' if family=='M4' and kind=='balanced' else '')+f'SM_{name}RearGrip'
        else:
            base={'HK416':'HK416/CommonAttachments20260930','M16':'M16A2/UniversalAttachments20260920','A762':'A762/Accessories05','PKM':'PKMLowpoly20260922/Accessories14','LMG201':'LMG201/Accessories22'}[family]
            path=f'/Game/Weapons/{base}/Meshes/SM_{family}_{variant}'
        key=family+'_'+kind; mesh=u.load_asset(path)
        if not mesh:raise RuntimeError('Missing '+path)
        dm=u.DynamicMesh()
        result=AU.copy_mesh_from_static_mesh(mesh,dm,u.GeometryScriptCopyMeshFromAssetOptions(apply_build_settings=False),u.GeometryScriptMeshReadLOD(lod_type=u.GeometryScriptLODType.SOURCE_MODEL,lod_index=0))
        if pick(result,u.GeometryScriptOutcomePins)!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Source read failed '+path)
        if Q.get_has_vertex_id_gaps(dm) or Q.get_has_triangle_id_gaps(dm):raise RuntimeError('Noncompact source '+key)
        positions=LU.convert_vector_list_to_array(pick(Q.get_all_vertex_positions(dm,True),u.GeometryScriptVectorList))
        triangles=LU.convert_triangle_list_to_array(pick(Q.get_all_triangle_indices(dm,True),u.GeometryScriptTriangleList))
        mids=LU.convert_index_list_to_array(pick(MAT.get_all_triangle_material_i_ds(dm),u.GeometryScriptIndexList))
        slots=mesh.get_editor_property('static_materials')
        row={'path':path,'sha256':sha(path),'family':family,'kind':kind,'vertices':len(positions),'triangles':len(triangles),'uv_sets':Q.get_num_uv_sets(dm),
             'slots':[str(s.material_slot_name) for s in slots],'materials':[s.material_interface.get_path_name() if s.material_interface else None for s in slots]}
        for s in slots:
            if s.material_interface:read_material(s.material_interface)
        pos=array.array('f',(c for v in positions for c in (v.x,v.y,v.z)))
        tri=array.array('i',(c for v in triangles for c in (v.x,v.y,v.z)))
        mid=array.array('i',list(mids)[:len(triangles)]);norm=array.array('f')
        for t in range(len(triangles)):
            ns=[x for x in Q.get_triangle_normals(dm,t) if isinstance(x,u.Vector)]
            for n in ns[:3]:norm.extend((n.x,n.y,n.z))
        with (O/'Input'/(key+'.bin')).open('wb') as f:
            f.write((json.dumps(row)+'\n').encode())
            for a in (pos,tri,mid,norm):a.tofile(f)
        meshes[key]=row
        (O/'Input/current.json').write_text(json.dumps({'meshes':meshes,'materials':materials},indent=2))
        print('REARGRIP_SOURCE',key,len(triangles),flush=True)
print('REARGRIP_SOURCES_SAVED',len(meshes),len(materials),flush=True)
