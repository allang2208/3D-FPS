"""Complete the existing read-only scene capture with actual source mesh geometry."""
from pathlib import Path
import json,unreal as u,gc
R=Path(__file__).resolve().parent
S=json.loads((R/'saved_scene.json').read_text());errors=[];count=0
near_bank_labels={a['label'] for a in S['actors'] if a['label'].startswith('NB28_Bank_') and a['p'][0]+a['extent'][0]>-55000 and a['p'][0]-a['extent'][0]<55000}
near_bank_meshes={r['mesh'] for r in S['rows'] if r['actor'] in near_bank_labels}
try:S['default_shape_complexity']=str(u.get_default_object(u.PhysicsSettings).get_editor_property('default_shape_complexity'))
except Exception as e:S['default_shape_complexity']='unavailable: '+str(e)
for p,b in S['meshes'].items():
    wanted=any(t in p for t in ['/Roads/','/Road/Kit_Sidewalk','/Meshes/JunctionAsphalt','/Meshes/BuildingPads','/Meshes/RoofSurfaces','/Meshes/ParkGround','NearBank20261028/Meshes/','/Vehicle/','StreetLamp','Road_Sign','Parking_Meter','Hydrant'])
    if not wanted or 'vertices' in b:continue
    if '/SM_NB_Bank_' in p and p not in near_bank_meshes:continue
    try:
        sm=u.load_asset(p)
        if not sm:raise RuntimeError('Missing mesh')
        dm=u.DynamicMesh();lod=u.GeometryScriptMeshReadLOD();lod.lod_type=u.GeometryScriptLODType.SOURCE_MODEL
        u.GeometryScript_AssetUtils.copy_mesh_from_static_mesh(sm,dm,u.GeometryScriptCopyMeshFromAssetOptions(),lod)
        q=u.GeometryScript_MeshQueries;lu=u.GeometryScript_List
        pl=next(x for x in q.get_all_vertex_positions(dm,False) if isinstance(x,u.GeometryScriptVectorList))
        tl=next(x for x in q.get_all_triangle_indices(dm,False) if isinstance(x,u.GeometryScriptTriangleList))
        b['vertices']=[list(x.to_tuple()) for x in lu.convert_vector_list_to_array(pl)]
        b['triangles']=[[x.x,x.y,x.z] for x in lu.convert_triangle_list_to_array(tl)]
        if not b['triangles']:raise RuntimeError('Empty source geometry')
        count+=1;print('AUDIT_GEOMETRY',count,p,len(b['triangles']),flush=True)
    except Exception as e:errors.append(dict(mesh=p,error=str(e)))
    if count%12==0:gc.collect();u.SystemLibrary.collect_garbage()
S['geometry_errors']=errors
(R/'saved_scene.json').write_text(json.dumps(S,separators=(',',':')),encoding='utf8')
print('AUDIT_GEOMETRY_COMPLETED',count,'errors',errors,flush=True)
