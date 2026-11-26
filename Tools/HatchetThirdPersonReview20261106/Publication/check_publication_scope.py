"""Check only the authorized publication artifacts; does not run gameplay."""
from pathlib import Path
import json, os, subprocess, re

root=Path('D:/FPS3D/FPSGAME')
p=Path(__file__).resolve().parent
doc=root/'Docs/Publication/HatchetThirdPerson20261106'
m=json.loads((p/'prepared.json').read_text())
env=dict(os.environ,GIT_INDEX_FILE=m['index'])
def git(*args):
    return subprocess.check_output(['git',*args],cwd=root,env=env,stderr=subprocess.PIPE)
assert git('rev-parse','HEAD').decode().strip()==m['base_commit'], 'HEAD advanced; rebuild subset'
check=subprocess.run(['git','diff','--cached','--check'],cwd=root,env=env,capture_output=True)
assert check.returncode==0,check.stdout.decode()
diff=git('diff','--cached','--no-ext-diff')
(p/'final-selected.diff').write_bytes(diff)
num=git('diff','--cached','--numstat').decode()
assert not any(line.startswith('-\t-\t') for line in num.splitlines()), 'Binary diff'
names=git('diff','--cached','--name-only','-z').decode().split('\0')[:-1]
assert set(names)=={x['path'] for x in m['files']}, 'Index contains unexpected files'
assert not any(x.startswith('trash/') or Path(x).suffix.lower() in {'.uasset','.umap','.dll','.exe','.npz','.blend','.fbx','.glb','.mp4','.png'} for x in names)
patterns=[rb'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----',rb'gh[pousr]_[A-Za-z0-9]{30,}',rb'github_pat_[A-Za-z0-9_]{40,}',rb'AKIA[A-Z0-9]{16}',rb'sk-(?:proj-)?[A-Za-z0-9_-]{40,}']
added=b'\n'.join(line[1:] for line in diff.splitlines() if line.startswith(b'+') and not line.startswith(b'+++'))
assert not any(re.search(pattern,added) for pattern in patterns), 'Potential credential; inspect privately'
cfgpath='Content/ColdSteelData/player_body.json'
cfg=json.loads(git('show',':'+cfgpath))
base=json.loads(git('show',m['base_commit']+':'+cfgpath))
live=json.loads((root/cfgpath).read_text(encoding='utf-8-sig'))
routes=json.loads((doc/'body-routes-manifest.json').read_text())
count=0
for owner in ['clips','kaitlin']:
    def clips(d):return d['clips'] if owner=='clips' else d['body_variants']['kaitlin']['clips']
    expected=routes['roles'] if owner=='clips' else routes['body_variants']['kaitlin']['clips']
    for role,value in expected.items():
        assert clips(cfg)[role]==value==clips(live)[role]
        clips(base)[role]=value
        count+=1
assert count==10 and cfg==base, 'Config changed outside ten owned routes'
patches=json.loads((p/'patch-applicability.json').read_text())
assert len(patches)==4 and all(x['exit_code']==0 and x['matches_current_normalized_source'] and not x['message'] for x in patches)
assert '/Game/Weapons/TacticalHatchet20261101' in git('show',':Config/DefaultGame.ini').decode()
retired=[]
for path in names:
    if path.startswith(('Source/','SourceAssets/')):
        if b'HatchetHeavyChopRhythm' in git('show',':'+path):retired.append(path)
assert not retired,retired
records={'base_commit':m['base_commit'],'scope':'Publication content only; existing mixed-workspace audit evidence is historical.',
    'whitespace_errors':0,'binary_files':0,'high_confidence_credential_matches':0,
    'owned_body_routes':count,'unrelated_config_changes':0,'exact_integration_patches':patches,
    'required_cook_directory_present':True,'retired_generator_references':retired,
    'build_rerun':False,'gameplay_rerun':False,'standalone_main_runtime_complete':False}
(doc/'publication-checks.json').write_text(json.dumps(records,indent=2)+'\n',encoding='utf-8',newline='\n')
entries=[x for x in m['files'] if x['path'] not in {str((doc/f).relative_to(root).as_posix()) for f in ['source-manifest.json','publication-checks.json']}]
(doc/'source-manifest.json').write_text(json.dumps({'base_commit':m['base_commit'],'files':entries,
    'record_files_without_self_hashes':['source-manifest.json','publication-checks.json'],
    'binary_assets':'local only; see asset-dependencies.json',
    'integration_scope':'Integration excerpts and patches are not applied runtime hosts; see integration-prerequisites.json'},indent=2)+'\n',encoding='utf-8',newline='\n')
print(json.dumps({'publication_files':len(names),'routes':count,'patches':len(patches),'whitespace_errors':0,'binary_files':0,'credential_matches':0,'gameplay_rerun':False}))
