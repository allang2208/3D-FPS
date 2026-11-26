"""Confirm R4 changes did not alter any visible original Meshy face corner."""
import hashlib,json,struct
from pathlib import Path
N=Path('D:/FPS3D/FPSGAME/SourceAssets/ChapelNun20261115');R=N/'RefinementR4'
def fingerprint(path,slots):
 d=json.loads(path.read_text());h=hashlib.sha256();count=0
 for t,n,uv,m in zip(d['triangles'],d['normals'],d['uv'],d['triangle_materials']):
  if m not in slots:continue
  count+=1
  for vi,normal,texcoord in zip(t,n,uv):
   h.update(struct.pack('<I8d',vi,*(d['positions'][vi]+normal+texcoord)))
 return dict(triangles=count,sha256=h.hexdigest())
before=fingerprint(N/'OriginalMeshyFaceR3/Authored/head.json',{0})
after=fingerprint(R/'Authored/head.json',{0,2})
report={'r3_face':before,'r4_face':after,'positions_topology_normals_uv_exact_match':before==after,'scope':'Visible Meshy source faces before and after R4 authoring; native neck and hair excluded'}
(R/'face_preservation.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
if before!=after:raise RuntimeError('Original face changed')
print(json.dumps(report))
