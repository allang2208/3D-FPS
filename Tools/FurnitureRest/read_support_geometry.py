"""Read existing furniture source surfaces to choose rest anchors; no scene render."""
import bpy,json
from pathlib import Path
ROOT=Path('D:/FPS3D/FPSGAME');OUT=ROOT/'SourceAssets/FurnitureRest20261022'
result={}
for key,path in {
 'ward_bed':'SourceAssets/DungeonIsolationWard20260929/BedScatter/Authored/SM_Ward_HospitalBed.fbx',
 'waiting_bench':'SourceAssets/HospitalWaitingBench20260929/Exports/SM_Hospital_Waiting_Bench.fbx',
}.items():
 bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.fbx(filepath=str(ROOT/path))
 rows=[]
 for o in bpy.context.scene.objects:
  if o.type!='MESH' or o.name.startswith('UCX_'):continue
  vertices=[o.matrix_world@v.co for v in o.data.vertices]
  for i,mat in enumerate(o.data.materials):
   ids={j for p in o.data.polygons if p.material_index==i for j in p.vertices}
   if not ids:continue
   p=[(vertices[j].x*100,-vertices[j].y*100,vertices[j].z*100) for j in ids]
   # Horizontal triangle area by elevation identifies seat/mattress top.
   levels={}
   for face in o.data.polygons:
    if face.material_index!=i:continue
    normal=o.matrix_world.to_3x3()@face.normal
    if normal.z<.8:continue
    z=round(sum(vertices[j].z for j in face.vertices)/len(face.vertices)*100/2)*2
    levels[z]=levels.get(z,0)+face.area
   rows.append({'material':mat.name,'min':[min(v[j] for v in p) for j in range(3)],'max':[max(v[j] for v in p) for j in range(3)],'support_levels':sorted(levels.items(),key=lambda x:-x[1])[:10]})
 result[key]=rows
(OUT/'support_geometry.json').write_text(json.dumps(result,indent=2))
print('SUPPORT_GEOMETRY '+json.dumps(result))
