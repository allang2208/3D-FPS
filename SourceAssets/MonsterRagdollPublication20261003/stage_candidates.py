"""Stage the reviewed exact candidates in a shared index, preserving working files."""
from pathlib import Path
import hashlib
import json
import subprocess

ROOT = Path('D:/FPS3D/FPSGAME')
OUT = ROOT / 'SourceAssets/MonsterRagdollPublication20261003'
def run(*args, data=None):
    return subprocess.check_output(['git', *args],cwd=ROOT,input=data).decode('utf-8').strip()
entries = json.loads((OUT/'candidate-files.json').read_text(encoding='utf-8'))
if run('diff','--cached','--name-only'):
    raise RuntimeError('Preserving the existing staged work; index must be reviewed first')
if run('log','--oneline','origin/main..HEAD'):
    raise RuntimeError('Preserving unpublished history; outgoing commits need review first')
base = run('rev-parse','HEAD')
lines = []
for entry in entries:
    file = ROOT / entry['candidate']
    if hashlib.sha256(file.read_bytes()).hexdigest() != entry['sha256']:
        raise RuntimeError('Candidate changed after preparation: '+entry['path'])
    obj = run('hash-object','-w','--path',entry['path'],str(file))
    mode = run('ls-files','--stage','--',entry['path'])
    mode = mode.split()[0] if mode else '100644'
    lines.append(f"{mode} {obj}\t{entry['path']}\n")
if run('rev-parse','HEAD') != base or run('diff','--cached','--name-only'):
    raise RuntimeError('HEAD or index changed during preparation; preserving current state')
run('update-index','--index-info',data=''.join(lines).encode('utf-8'))
(OUT/'staging.json').write_text(json.dumps(dict(base_head=base,origin_main=run('rev-parse','origin/main'),
    files=[e['path'] for e in entries],working_sources_rewritten=False),ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(dict(staged_files=len(entries),base_head=base),ensure_ascii=False))
