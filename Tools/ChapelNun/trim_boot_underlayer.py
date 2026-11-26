"""Keep the ankle underlayer comfortably below the robe's moving knee region."""
import json
from pathlib import Path
P=Path('D:/FPS3D/FPSGAME/SourceAssets/ChapelNun20261115/RefinementR4/Authored/boots.json')
d=json.loads(P.read_text());keep=[i for i,(t,m) in enumerate(zip(d['triangles'],d['triangle_materials'])) if m!=7 or max(d['positions'][v][2] for v in t)<=40.01]
for key in ('triangles','normals','uv','triangle_materials'):d[key]=[d[key][i] for i in keep]
P.write_text(json.dumps(d,separators=(',',':')),encoding='utf-8');print('ANKLE_UNDERLAYER',sum(m==7 for m in d['triangle_materials']))
