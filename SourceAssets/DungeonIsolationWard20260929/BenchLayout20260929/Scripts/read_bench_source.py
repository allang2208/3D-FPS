"""Read imported source coordinates to choose the bench's inward-facing yaw."""
import json
from pathlib import Path
import bpy

ROOT=Path(__file__).resolve().parents[1]
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath='D:/FPS3D/FPSGAME/SourceAssets/HospitalWaitingBench20260929/Exports/SM_Hospital_Waiting_Bench.fbx')
points=[o.matrix_world@v.co for o in bpy.context.scene.objects if o.type=='MESH' for v in o.data.vertices]
back=[v for v in points if v.z>.7]
info=dict(source_bounds_m=dict(min=[min(v[i] for v in points) for i in range(3)],
                               max=[max(v[i] for v in points) for i in range(3)]),
          backrest_above_70cm=dict(min=[min(v[i] for v in back) for i in range(3)],
                                   max=[max(v[i] for v in back) for i in range(3)],
                                   mean_y=sum(v.y for v in back)/len(back)))
(ROOT/'source-shape.json').write_text(json.dumps(info,indent=2),encoding='utf-8')
print('BENCH_SOURCE_GEOMETRY',json.dumps(info),flush=True)
