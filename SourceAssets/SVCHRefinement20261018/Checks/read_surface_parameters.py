import unreal as u,json
from pathlib import Path
O=Path(__file__).parent
L=u.MaterialEditingLibrary
mesh=u.load_asset('/Game/Weapons/SVCH/Refined20261018/SK_SVCH_Refined_R3')
report={'materials':[]}
for slot in list(mesh.get_editor_property('materials'))[:9]:
    m=slot.material_interface
    report['materials'].append({'slot':str(slot.material_slot_name),
      'parameters':{str(n):L.get_material_instance_scalar_parameter_value(m,n) for n in L.get_scalar_parameter_names(m)}})
dm=u.DynamicMesh();lod=u.GeometryScriptMeshReadLOD();lod.lod_type=u.GeometryScriptLODType.SOURCE_MODEL
u.GeometryScript_AssetUtils.copy_mesh_from_skeletal_mesh(mesh,dm,u.GeometryScriptCopyMeshFromAssetOptions(),lod)
values=u.GeometryScript_MeshQueries.get_all_vertex_positions(dm,True)
vl=next(v for v in values if isinstance(v,u.GeometryScriptVectorList))
pts=u.GeometryScript_List.convert_vector_list_to_array(vl)
report['mesh_vertex_bounds']={s:[f(getattr(p,axis) for p in pts) for axis in ('x','y','z')] for s,f in (('min',min),('max',max))}
(O/'surface_parameters.json').write_text(json.dumps(report,indent=1))
print('SVCH_SURFACE_PARAMETERS',json.dumps(report),flush=True)
