"""Read back only the repaired glass UVs and linen shader inputs; no gameplay."""
import unreal as u
from pathlib import Path
import json
R=Path(__file__).parent;D='/Game/Weapons/WoodSteelLongbow20261026/'
Q=u.GeometryScript_MeshQueries;G=u.GeometryScript_AssetUtils;L=u.GeometryScript_List
report={'optics':{},'linen':{},'gameplay_tested':False}
for power in (2,4):
    name='SM_WoodSteelLongbow_Optic'+str(power)+'x';mesh=u.load_asset(D+name)
    glass=next(i for i,s in enumerate(mesh.static_materials) if 'Glass' in str(s.material_slot_name))
    lod=u.GeometryScriptMeshReadLOD();lod.lod_type=u.GeometryScriptLODType.RENDER_DATA
    dm,status=G.copy_mesh_from_static_mesh_v2(mesh,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(),lod)
    if status!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Cannot read imported mesh '+name)
    _,vlist,_=Q.get_all_vertex_positions(dm,False);verts=L.convert_vector_list_to_array(vlist)
    _,tlist,_=Q.get_all_triangle_indices(dm,False);triangles=L.convert_triangle_list_to_array(tlist)
    coords=[];centres=[]
    for ti,t in enumerate(triangles):
        mi,valid=u.GeometryScript_Materials.get_triangle_material_id(dm,ti)
        if not valid or mi!=glass:continue
        a,b,c,valid=Q.get_triangle_u_vs(dm,0,ti)
        if not valid:raise RuntimeError('Missing glass UV0')
        for vi,uv in zip((t.x,t.y,t.z),(a,b,c)):
            pos=verts[vi];coords.append([uv.x,uv.y])
            if abs(pos.y+10.223)<.002 and abs(pos.z-24.3328)<.002:centres.append([uv.x,uv.y])
    if not centres:raise RuntimeError('Missing physical lens centre '+name)
    error=max(abs(v-.5) for pair in centres for v in pair)
    if error>.001:raise RuntimeError('Imported reticle centre differs '+name)
    report['optics'][name]={'uv_min':[min(v[k] for v in coords) for k in (0,1)],'uv_max':[max(v[k] for v in coords) for k in (0,1)],'centre_uv':centres[0],'centre_error':error}
for finish in ('Linen','WaxedLinen'):
    name='M_WoodSteelLongbow_'+finish+'_Static';m=u.load_asset(D+name)
    row={}
    for label,prop in [('base',u.MaterialProperty.MP_BASE_COLOR),('normal',u.MaterialProperty.MP_NORMAL),('roughness',u.MaterialProperty.MP_ROUGHNESS),('ao',u.MaterialProperty.MP_AMBIENT_OCCLUSION)]:
        node=u.MaterialEditingLibrary.get_material_property_input_node(m,prop)
        if not node:raise RuntimeError('Missing linen shader input '+label)
        row[label]=node.get_class().get_name()
    report['linen'][name]=row
(R/'saved-asset-readback.json').write_text(json.dumps(report,indent=2),encoding='utf8')
print(json.dumps(report,indent=2))
