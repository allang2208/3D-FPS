"""Record local binary dependencies and current evidence without copying assets to Git."""
from pathlib import Path
import hashlib,json
root=Path('D:/FPS3D/FPSGAME')
folders=['SourceAssets/PoisonMaggot20260911/delivery','Content/Monsters/PoisonMaggot','Content/Tests/PoisonMaggot']
files=[]
for folder in folders:
 for p in sorted((root/folder).rglob('*')):
  if p.is_file() and p.suffix in ['.blend','.fbx','.png','.wav','.uasset','.umap','.json']:
   files.append({'path':p.relative_to(root).as_posix(),'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
report={'date':'2026-09-11','host':'D:/FPS3D/FPSGAME','content_publication':'local binaries only; Git contains code, tools, documents and hashes','generated_candidate':'poison_maggot_v01','job_id':'1489949901173243904','mesh_vertices':20170,'source_quads':20168,'semantic_bones':37,'max_influences':4,'physics_support_hulls':9,'noncolliding_root_body':1,'files':files}
(root/'Docs/PoisonMaggotAssets.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('MAGGOT_MANIFEST_COMPLETE',len(files))
