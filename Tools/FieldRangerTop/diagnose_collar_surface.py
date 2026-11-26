"""Focused diagnosis of the reported neck/chest defect, in native reference pose."""
import json,sys
from pathlib import Path
import numpy as np
P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/FieldRangerTop20261020/CollarRepair20261021'
sys.path.insert(0,str(P/'Tools/FieldRangerTop'))
import export_collar_repair as export
original=export.io.mat
def clay(name,family=None,color=None,rough=.7,metal=0):
    return original(name,color=(.16,.075,.035) if name=='RangerLeather' else color or (.10,.15,.055),rough=rough,metal=metal)
export.io.mat=clay
d=export.read(R/'Authored/ue_field_sweater/Jason.json')
export.diagnosis(d,'Jason_Geometry_Diagnosis')
ps=np.array(d['positions']);fs=np.array(d['triangles']);slots=np.array(d['triangle_materials'])
# Quantitative mesh evidence for this repair only, not a gameplay acceptance run.
uv=np.array(d['uv']);areas=abs(np.cross(uv[:,1]-uv[:,0],uv[:,2]-uv[:,0]))
result=dict(vertices=len(ps),triangles=len(fs),bounds=[ps.min(0).tolist(),ps.max(0).tolist()],zero_uv_triangles=int(np.sum(areas<1e-10)),zero_uv_by_slot={str(s):int(np.sum((areas<1e-10)&(slots==s))) for s in set(slots)},finite_positions=bool(np.isfinite(ps).all()))
print(json.dumps(result),flush=True)
(R/'Evidence/geometry_diagnosis.json').write_text(json.dumps(result,indent=2))
