from pathlib import Path
from datetime import datetime
import unreal as u,json,hashlib,shutil
R=Path(__file__).resolve().parent;P=R.parent;PROJECT=P.parents[1];CONTENT=(PROJECT/'Content').resolve();HOST=P/'PublicationHost/Content'
relative=[Path('GameMaps/L_CyberpunkApartment.umap')]+[p.relative_to(CONTENT) for p in (CONTENT/'NativeNearBank20261028').rglob('*') if p.is_file()]
dirty={p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_map_packages()}|{p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
loaded=[]
for rel in relative:
    if rel.suffix not in ['.umap','.uasset']:continue
    package='/Game/'+rel.with_suffix('').as_posix()
    if package in dirty or u.find_object(None,package) or u.find_object(None,package+'.'+rel.stem):loaded.append(package)
if loaded:raise RuntimeError('Preserve loaded district packages '+str(loaded[:20]))
audit=json.loads((P/'Audit/snapshot.json').read_text());known={x['path']:x['sha256'].lower() for x in audit['files']}
rows=[]
for rel in relative:
    src=CONTENT/rel;dst=HOST/rel;sha=hashlib.sha256(src.read_bytes()).hexdigest()
    if rel.as_posix() in known and known[rel.as_posix()]!=sha:raise RuntimeError('Source changed since geometry audit '+str(rel))
    if not dst.resolve().is_relative_to(HOST.resolve()):raise RuntimeError('Publication host package must be a physical private copy '+str(dst))
    dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dst);rows.append(dict(relative=rel.as_posix(),source_sha256=sha))
(R/'publication_source.json').write_text(json.dumps(dict(files=rows,prepared_at=datetime.now().astimezone().isoformat()),indent=2))
print('ISOLATED_REPAIR_SOURCE_READY',len(rows))
