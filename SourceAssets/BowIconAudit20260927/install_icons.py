"""Deploy only the 21 audited bow modification PNGs, preserving previous files."""
import hashlib,json,shutil
from pathlib import Path
P=Path(__file__).resolve().parent;ROOT=P.parents[1]
before=json.loads((P/'before-audit.json').read_text(encoding='utf8'))
backup=ROOT/'Saved/BowIconAudit20260927/Before';backup.mkdir(parents=True,exist_ok=True)
receipt=P/'icon-install-receipt.json'
if receipt.exists():raise RuntimeError('This deployment already has a receipt; preserve it')
rows=[]
for row in before['icons']:
    dst=Path(row['resolved']);src=P/'Icons'/(row['name']+'.png')
    if hashlib.sha256(dst.read_bytes()).hexdigest()!=row['sha256']:raise RuntimeError('PNG changed since audit: '+str(dst))
    if not src.exists():raise RuntimeError('Render missing '+str(src))
for row in before['icons']:
    dst=Path(row['resolved']);src=P/'Icons'/(row['name']+'.png')
    for suffix in ['.png','.uasset','.uexp','.ubulk']:
        previous=dst.with_suffix(suffix)
        if previous.exists():
            saved=backup/previous.name
            if saved.exists():raise RuntimeError('Preserve prior backup '+str(saved))
            shutil.copy2(previous,saved)
    shutil.copy2(src,dst)
    rows.append(dict(name=row['name'],png=str(dst),asset_folder='/Game/ColdSteelData/AttachmentIcons20260913',
        old_sha256=row['sha256'],sha256=hashlib.sha256(dst.read_bytes()).hexdigest(),label=row['label'],runtime_visual=row['visual']))
receipt.write_text(json.dumps(dict(pngs=rows,backup=str(backup),texture_import_pending=True),ensure_ascii=False,indent=2),encoding='utf8')
print('BOW_MONOCHROME_PNG_INSTALLED',len(rows))
