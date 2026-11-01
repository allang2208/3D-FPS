"""Read existing lens surfaces and socket frames for the shared physical optics."""
import json
from pathlib import Path
import unreal as u

O=Path(__file__).resolve().parent
paths={
 'lpvo':'/Game/Weapons/AttachmentFinish20260913/M4/Meshes/SM_LPVO1to6X',
 'prism':'/Game/Weapons/AttachmentFinish20260913/M4/Meshes/SM_PrismScope2X',
 'kv':'/Game/Weapons/KVScope20261019/SM_KVScope_Common',
 'thermal':'/Game/Weapons/ThermalScope20261006/Runtime/SM_Thermal_Common',
 'pso':'/Game/Weapons/PSO1Russian20260923/AKM/SM_PSO1_AKM',
 'm24':'/Game/Weapons/M24/Surface20261027/SM_M24_m24_custom_scope_6x',
 'm24_lpvo':'/Game/Weapons/M24/CommonOptics20261028/Meshes/SM_M24_lpvo_1_6x',
 'm24_prism':'/Game/Weapons/M24/CommonOptics20261028/Meshes/SM_M24_prism_scope_2x',
 'm24_kv':'/Game/Weapons/M24/CommonOptics20261028/Meshes/SM_M24_kv_scope_4x',
 'm24_thermal':'/Game/Weapons/M24/CommonOptics20261028/Meshes/SM_M24_thermal_scope',
}
auth=json.loads((O.parent/'DanWesson715CompactScope20260927/authoring.json').read_text())
for key in auth['parts']:
 if 'scope' in key.lower():paths['handgun']='/Game/Weapons/DanWesson715/CompactScope20260927/Meshes/SM_'+key
report={}
for key,path in paths.items():
 mesh=u.load_asset(path)
 if not mesh:raise RuntimeError(path)
 row={'path':path,'slots':[str(s.material_slot_name) for s in mesh.static_materials], 'sockets':{},'surfaces':{}}
 for n in ('SightRear','SightFront','SightUp','AimCenter','MountForward','MountUp'):
  s=mesh.find_socket(n)
  if s:row['sockets'][n]=list(s.relative_location.to_tuple())
 dm=u.DynamicMesh()
 u.GeometryScript_AssetUtils.copy_mesh_from_static_mesh_v2(mesh,dm,u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD(),False)
 wanted={i for i,s in enumerate(row['slots']) if any(k in s.lower() for k in ('glass','lens','display','reticle','optic'))}
 points={i:[] for i in wanted}
 for tid in range(dm.get_triangle_count()):
  mid,valid=u.GeometryScript_Materials.get_triangle_material_id(dm,tid)
  if valid and mid in wanted:
   valid,a,b,c=u.GeometryScript_MeshQueries.get_triangle_positions(dm,tid)
   if valid:points[mid].extend([list(p.to_tuple()) for p in (a,b,c)])
 for mid,ps in points.items():
  if ps:row['surfaces'][row['slots'][mid]]={'min':[min(p[i] for p in ps) for i in range(3)],'max':[max(p[i] for p in ps) for i in range(3)],'vertices':ps}
 report[key]=row
 (O/'authoring_inputs.json').write_text(json.dumps(report),encoding='utf-8')
 print('READ_SCOPE',key,json.dumps({k:v for k,v in row.items() if k!='surfaces'}),flush=True)
 u.SystemLibrary.collect_garbage()
