from pathlib import Path
import hashlib, json, os, shutil, tempfile
batch=Path(__file__).resolve().parent
plan=json.loads((batch/'plan.json').read_text())
authored=json.loads((batch/'authored.json').read_text())
if set(authored)!={'SVCH','SVD','KeeperFixR2','IntegrationR1'}:
    raise RuntimeError('Authoring batch is incomplete')
root=Path(plan['project'])/'Content'
host=batch/'Host/Content'
def sha(p):
    with p.open('rb') as stream:
        return hashlib.file_digest(stream,'sha256').hexdigest()
def signature(p):return sha(p) if p.is_file() else None
records=[]
for entry in plan['assets']:
    rel=Path(entry['path'])
    logical='/Game/'+rel.with_suffix('').as_posix()
    produced=next(v for v in authored.values() if v['package']==logical)
    source=host/rel
    with source.open('rb') as f:
        if f.read(4)!=bytes.fromhex('C1832A9E'):raise RuntimeError('Missing saved Unreal package: '+str(source))
    for suffix in ['.uexp','.ubulk','.uptnl','.uasset']:
        p=source.with_suffix(suffix);target=(root/rel).with_suffix(suffix)
        before=entry['before'] if suffix=='.uasset' else None
        if not p.exists():
            if target.exists():raise RuntimeError('Unexpected sidecar '+str(target))
            continue
        after=sha(p)
        if signature(target) not in (before,after):raise RuntimeError('Active asset changed: '+str(target))
        record={'file':target.relative_to(root).as_posix(),'bytes':p.stat().st_size,'before':before,'after':after,'release':produced['commit']}
        if suffix=='.uasset' and 'historical_sha256' in produced:
            record['matches_historical_sha256']=after==produced['historical_sha256']
        records.append(record)
staged={};installed=[]
try:
    for row in records:
        rel=row['file'];target=root/rel
        target.parent.mkdir(parents=True,exist_ok=True)
        if signature(target)==row['after']:continue
        with tempfile.NamedTemporaryFile(dir=target.parent,prefix='.recover_',suffix='.tmp',delete=False) as out:
            staged[rel]=Path(out.name)
            with (host/rel).open('rb') as src:shutil.copyfileobj(src,out,1024*1024)
    for row in records:
        rel=row['file'];target=root/rel
        if rel not in staged:continue
        if signature(target)!=row['before']:raise RuntimeError('Concurrent change to '+str(target))
        if row['before'] is None:os.rename(staged[rel],target)
        else:
            if sha(batch/'Before'/rel)!=row['before']:raise RuntimeError('Backup mismatch: '+rel)
            os.replace(staged[rel],target)
        installed.append(row)
    output=dict(project=plan['project'],physical_content=str(root.resolve()),method='reconstructed from the published authoring recipes',assets=authored,files=records,gameplay_tested=False,authoring_notes=['The static mesh builder reported degenerate/near-zero tangent bases on the belt pickup. The published geometry, UVs and build recipe were retained.'])
    receipt=batch/'installed.json'
    draft=receipt.with_suffix('.tmp')
    draft.write_text(json.dumps(output,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    os.replace(draft,receipt)
except BaseException:
    for row in reversed(installed):
        rel=row['file'];target=root/rel
        if signature(target)!=row['after']:continue
        undo=batch/'Interrupted'/rel
        undo.parent.mkdir(parents=True,exist_ok=True)
        os.replace(target,undo)
        if row['before'] is not None:shutil.copy2(batch/'Before'/rel,target)
    raise
finally:
    for tmp in staged.values():
        if tmp.exists():tmp.unlink()
print('Installed:',len(records),'files')
for row in records:print(row['file'],row['bytes'],row['after'])
