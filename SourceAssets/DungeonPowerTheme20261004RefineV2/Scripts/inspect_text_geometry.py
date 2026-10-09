"""Read source FBX text faces for the requested stretch/flicker diagnosis. No render."""
import bpy, json
from pathlib import Path
from mathutils import Vector
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
PROJECT=ROOT.parents[1]
SPECS=[(p,4096,4096,['PW_Labels']) for p in ROOT.joinpath('Authored').glob('*.fbx')
       if '_Signs' in p.stem or p.stem in ('SM_Power_ControlConsole_Refined','SM_Power_Accumulator')]
SPECS += [(PROJECT/'SourceAssets/DungeonFacilityPropPolish20260928/Authored/SM_Facility_PowerCabinet.fbx',4096,2048,['FacilityProp_Atlas']),
 (PROJECT/'SourceAssets/DungeonDataArchive20260930/Equipment20260930/Authored/SM_Archive_ServerRack_V1.fbx',4096,4096,['ArchiveEquipment_Atlas']),
 (PROJECT/'SourceAssets/StationWorkshop20261003/RefineV2/Authored/SM_SW_RackSpares_0.fbx',2048,2048,['RS_Labels']),
 (PROJECT/'SourceAssets/StationWorkshop20261003/RefineV2/Authored/SM_SW_MotorService.fbx',2048,2048,['RS_Labels'])]
SPECS += [(p,800,2000,['RS_Labels']) for p in (PROJECT/'SourceAssets/IncineratorContainers20261003/Authored').glob('*.fbx')]
report=[]
for path,W,H,slots in SPECS:
 bpy.ops.wm.read_factory_settings(use_empty=True)
 bpy.ops.import_scene.fbx(filepath=str(path))
 records=[]
 for obj in bpy.context.scene.objects:
  if obj.type!='MESH' or obj.name.startswith('UCX_'):continue
  mesh=obj.data;uv=mesh.uv_layers.active
  if not uv:continue
  print('TEXT_SOURCE',path.stem,obj.name,[m.name for m in mesh.materials],flush=True)
  for face in mesh.polygons:
   mat=mesh.materials[face.material_index].name
   if not any(mat.startswith(s) for s in slots):continue
   lis=list(face.loop_indices)[:3]
   p=[obj.matrix_world @ mesh.vertices[mesh.loops[i].vertex_index].co for i in lis]
   t=[Vector((uv.data[i].uv.x*W,uv.data[i].uv.y*H)) for i in lis]
   T=np.array([t[1]-t[0],t[2]-t[0]]).T
   if abs(np.linalg.det(T))<1e-10:continue
   J=np.array([p[1]-p[0],p[2]-p[0]]).T @ np.linalg.inv(T)
   ss=np.linalg.svd(J,compute_uv=False)
   pixels=[(uv.data[i].uv.x*W,(1-uv.data[i].uv.y)*H) for i in face.loop_indices]
   bounds=[round(min(p[k] for p in pixels),2) for k in range(2)]+[round(max(p[k] for p in pixels),2) for k in range(2)]
   if path.stem=='SM_Facility_PowerCabinet' and not (bounds[0]>3080 and bounds[1]>1030):continue
   if path.stem=='SM_Archive_ServerRack_V1' and not (3635<bounds[1]<3746 and bounds[2]<1010):continue
   records.append(dict(face=face.index,mat=mat,stretch=round(float(ss[0]/ss[-1]),4),
     center=[round(x,5) for x in obj.matrix_world@face.center],
     normal=[round(x,5) for x in face.normal],
     uv_px=bounds))
 report.append(dict(source=str(path),records=records))
 print('TEXT_METRICS',path.stem,'faces',len(records),'stretch_range',
   (min((r['stretch'] for r in records),default=0),max((r['stretch'] for r in records),default=0)),flush=True)
out=ROOT/'TextCards20261005/Receipts';out.mkdir(parents=True,exist_ok=True)
(out/'source-diagnosis.json').write_text(json.dumps(report,indent=2),encoding='utf8')
