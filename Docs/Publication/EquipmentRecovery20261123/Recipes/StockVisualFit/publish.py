from pathlib import Path
import json, hashlib, tempfile, shutil, os
batch=Path(__file__).resolve().parent
def read(name):return json.loads((batch/name).read_text(encoding='utf-8'))
plan=read('inputs.json');metrics=read('alignment.json');joins=read('joins.json');build=read('authored.json')
content=Path(plan['project'])/'Content'
entries={}
def sha(path):
    with path.open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()
for k,p in plan['entries'].items():
    rel=Path(p['relative']);before=batch/'Before'/rel;product=batch/'Host/Content'/rel;live=content/rel
    if sha(before)!=p['before'] or sha(live)!=p['before']:raise RuntimeError('Formal asset changed: '+k)
    if any(live.with_suffix(s).exists() or product.with_suffix(s).exists() for s in ('.uexp','.ubulk','.uptnl')):raise RuntimeError('Package has separate export data: '+k)
    if not all(joins[k]['after'].values()) or metrics[k]['after_degrees']>.2 or build[k]['lods']!=3:raise RuntimeError('Saved mesh fit is incomplete: '+k)
    entries[k]=dict(p,after=sha(product),bytes=product.stat().st_size,geometry=build[k],alignment=metrics[k],seam=joins[k]['after'])
temps={};replaced=[]
try:
    for k,p in entries.items():
        dest=content/p['relative']
        with tempfile.NamedTemporaryFile(prefix='.stockfit_',suffix='.tmp',dir=dest.parent,delete=False) as tmp:
            temps[k]=Path(tmp.name)
            with (batch/'Host/Content'/p['relative']).open('rb') as f:shutil.copyfileobj(f,tmp,1024*1024)
    for k,p in entries.items():
        dest=content/p['relative']
        if sha(dest)!=p['before']:raise RuntimeError('Concurrent write: '+k)
        os.replace(temps[k],dest);replaced.append(k)
    receipt=dict(revision='VisualFitR2',project=plan['project'],review=plan['review'],method='UE render geometry and game presentation frame',files=entries,play_test=False)
    stage=batch/'installed.new';stage.write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');os.replace(stage,batch/'installed.json')
except BaseException:
    for k in reversed(replaced):
        p=entries[k];rel=p['relative'];dest=content/rel
        if sha(dest)==p['after']:
            with tempfile.NamedTemporaryFile(prefix='.stockfit_revert_',suffix='.tmp',dir=dest.parent,delete=False) as tmp:
                with (batch/'Before'/rel).open('rb') as f:shutil.copyfileobj(f,tmp)
            os.replace(tmp.name,dest)
    raise
finally:
    for p in temps.values():p.unlink(missing_ok=True)
print('Saved formal mesh revisions:',[(k,v['after']) for k,v in entries.items()])
