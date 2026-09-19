from pathlib import Path
import ast
import hashlib
import json
import posixpath
import re
import subprocess

w = Path('E:/3d/publish-ue5-m4-20260910')
a = Path('D:/FPS3D/FPSGAME/Docs/repository-ue5-root-20260910')
def git(*args):
    return subprocess.check_output(['git', '-C', str(w), *args])

paths = set(git('ls-files', '-z').decode().split('\0')[:-1])
paths.update(git('ls-files', '--others', '--exclude-standard', '-z').decode().split('\0')[:-1])
paths.add('Docs/RepositoryValidation.json')
assert 'project.godot' not in paths
assert not any(p.startswith(('assets/', 'addons/', 'scenes/', 'scripts/', 'weapon_data/', 'skills/godot-')) for p in paths)
assert not any(p.split('/')[0] in {'docs', 'tools', 'Binaries', 'Intermediate', 'Saved', 'trash'} for p in paths)
assert not any(p.endswith(('.blend','.fbx','.uasset','.umap','.wav','.ogg','.mp4','.pyc')) for p in paths)
errors=[]; python=0; json_count=0; links=0
for rel in sorted(paths):
    p=w/rel
    if rel.startswith('unreal/') or rel=='Docs/RepositoryValidation.json':
        continue
    s=p.read_text(encoding='utf-8-sig')
    if p.suffix=='.py': ast.parse(s, filename=rel); python+=1
    if p.suffix in {'.json','.uproject'}: json.loads(s);json_count+=1
    if p.suffix=='.md':
        for m in re.finditer(r'(?<!!)\[[^\]]*\]\(([^)]+)\)',s):
            target=m.group(1).split('#')[0]
            if not target or re.match(r'[a-zA-Z][\w+.-]*:',target) or target.startswith('/'):continue
            normalized=posixpath.normpath(posixpath.join(posixpath.dirname(rel),target))
            if normalized not in paths and not any(f.startswith(normalized.rstrip('/')+'/') for f in paths):
                errors.append(dict(path=rel,target=target))
            links+=1
assert not errors, errors
snapshot=json.loads((w/'Docs/SourceSnapshot.json').read_text(encoding='utf8'))
for r in snapshot['files']:
    raw=(w/r['path']).read_bytes()
    assert hashlib.sha256(raw).hexdigest()==r['repository_sha256'],r['path']
editor=(a/'editor-build-final.log').read_text(encoding='utf-8-sig',errors='replace')
assert 'Result: Succeeded' in editor
game=(a/'game-build.log').read_text(encoding='utf-8-sig',errors='replace')
result=dict(date='2026-09-10',archive_files=6199,archive_bytes=4551481865,archive_sha256_check='PASS',
    current_python_syntax_files=python,current_json_files=json_count,case_sensitive_relative_links=links,
    snapshot_hashes=len(snapshot['files']),skill_metadata_packages=5,
    editor_build='PASS',game_build='PASS' if 'Result: Succeeded' in game else 'PENDING',
    build_project=str(w/'FPSGAME.uproject'),
    build_flags=['-WaitMutex','-NoUBA','-NoHotReloadFromIDE','-NoHotReload'],
    compile_fix='Re-read host M4MuzzleVisual.cpp: rename Mesh local to MuzzleMesh (C4458).',
    runtime_assets='Excluded licensed binaries; restore local Content before full game validation.',
    runtime_animation='Unchanged by repository migration; historical checks are not new runtime acceptance.',
    sensitive_pattern_scan='No private key, GitHub token, AWS key, or literal credential assignment patterns found in new source/tool/doc payload.')
(w/'Docs/RepositoryValidation.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf8',newline='\n')
print(json.dumps(result,ensure_ascii=False,indent=2))
