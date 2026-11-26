"""Commit the selected tree while preserving the shared index and work files."""
from pathlib import Path
import os, subprocess, json, hashlib, shutil

root=Path('D:/FPS3D/FPSGAME')
p=Path(__file__).resolve().parent
m=json.loads((p/'prepared.json').read_text())
env=dict(os.environ,GIT_INDEX_FILE=m['index'])
def git(*args,env=None,data=None):
    return subprocess.check_output(['git',*args],cwd=root,env=env,input=data,stderr=subprocess.PIPE)
def entries(env=None,tree=None):
    if tree:
        records=git('ls-tree','-r','-z',tree).split(b'\0')
        return {r.split(b'\t',1)[1].decode():r.split(b'\t',1)[0].split()[::2] for r in records if r}
    records=git('ls-files','--stage','-z',env=env).split(b'\0')
    result={}
    for r in records:
        if not r:continue
        meta,name=r.split(b'\t',1);mode,oid,stage=meta.split()
        assert stage==b'0','Unmerged index; leave untouched'
        result[name.decode()]=[mode,oid]
    return result
def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None
base=m['base_commit'];owned={x['path'] for x in m['files']}
assert git('symbolic-ref','HEAD').decode().strip()=='refs/heads/main'
assert git('rev-parse','HEAD').decode().strip()==base
assert git('rev-parse','origin/main').decode().strip()==base,'Remote advanced; review first'
assert git('remote','get-url','--push','origin').decode().strip()=='https://github.com/allang2208/3D-FPS.git'
git('diff','--cached','--check',env=env)
selected=entries(env=env);tree_entries=entries(tree=base)
for f in m['files']:assert selected[f['path']]==[b'100644',f['blob'].encode()]
before_files={name:digest(root/name) for name in owned}
gitdir=Path(git('rev-parse','--absolute-git-dir').decode().strip())
real=gitdir/'index';lock=gitdir/'index.lock'
aligned=p/'aligned-shared.index'
acquired=False;head_advanced=False
try:
    with lock.open('xb'):
        acquired=True
    before_bytes=real.read_bytes()
    before=entries()
    for name in owned:
        assert before.get(name)==tree_entries.get(name),'Owned path staged elsewhere: '+name
    (p/'real-index-before-commit.bin').write_bytes(before_bytes)
    staged_before=git('diff','--cached','--name-only','-z').decode().split('\0')[:-1]
    (p/'shared-index-before-commit.json').write_text(json.dumps({'head':base,'staged_paths':staged_before,
        'entries':{k:[x.decode() for x in v] for k,v in before.items()}},indent=2)+'\n')
    aligned.write_bytes(before_bytes)
    align_env=dict(os.environ,GIT_INDEX_FILE=str(aligned))
    lines=b''.join(b' '.join(selected[name])+b'\t'+name.encode()+b'\0' for name in sorted(owned))
    git('update-index','-z','--index-info',env=align_env,data=lines)
    after=entries(env=align_env)
    assert {k:v for k,v in before.items() if k not in owned}=={k:v for k,v in after.items() if k not in owned}
    tree=git('write-tree',env=env).decode().strip()
    message=('Publish third-person hatchet repairs and replication audit recipes\n\n'
        'Publish ten Jason/Kaitlin body routes, observer trail readiness, executor clock\n'
        'presentation, authoring recipes and historical audit evidence. Archive retired\n'
        'first-person candidates locally and document animation/replication lessons.\n\n'
        'Shared runtime host changes remain explicit integration patches/excerpts.\n'
        'Binary assets remain local; this text-only batch is not a standalone runtime\n'
        'release. No build or gameplay tests rerun for publication.\n')
    (p/'commit-message.txt').write_text(message,encoding='utf-8',newline='\n')
    commit=git('commit-tree',tree,'-p',base,'-F',str(p/'commit-message.txt')).decode().strip()
    shutil.copyfile(aligned,lock)
    assert real.read_bytes()==before_bytes,'Shared index changed while locked'
    git('update-ref','-m','publish scoped third-person hatchet work','refs/heads/main',commit,base)
    head_advanced=True
    os.replace(lock,real);acquired=False
    assert entries()==after,'Index changed after commit; inspect receipt'
    assert {name:digest(root/name) for name in owned}==before_files,'Working files changed during commit'
    record={'commit':commit,'base_commit':base,'tree':tree,'files':len(owned),
        'unrelated_staged_paths_preserved':len(staged_before),'unrelated_index_entries_preserved':True,
        'working_files_untouched':True,'push_status':'not attempted'}
    (p/'commit-receipt.json').write_text(json.dumps(record,indent=2)+'\n')
    print(json.dumps(record))
finally:
    if acquired:
        if head_advanced:
            # The prepared index contains only the owned updates and original unrelated entries.
            os.replace(lock,real)
        else:
            lock.unlink()
