from pathlib import Path
import json,hashlib,datetime
W=Path(__file__).resolve().parent;P=Path('D:/FPS3D/FPSGAME');baseline=json.loads((W/'baseline.json').read_text())
paths=json.loads((W/'code_paths.json').read_text());sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
for rel in paths:
    p=P/rel
    if rel in baseline:assert sha(p)==baseline[rel]['sha256'],('Concurrent edit',rel)
    else:assert not p.exists(),('New destination exists',rel)
receipt=[]
for rel in paths:
    p=P/rel;p.write_bytes((W/'Staged'/rel).read_bytes());receipt.append({'path':rel,'sha256':sha(p)})
(W/'code_publish_receipt.json').write_text(json.dumps({'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'files':receipt},indent=2))
print('CODE_PUBLISHED',len(receipt))
