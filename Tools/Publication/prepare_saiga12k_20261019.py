"""Read-only publication inventory; no UE launch or staging."""
import json, os, stat, subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'Saved/Saiga12KPublication20261019'
OUT.mkdir(parents=True, exist_ok=True)

def git(*args):
    return subprocess.check_output(['git', '-c', 'core.safecrlf=false', *args], cwd=ROOT).decode('utf-8')

def walk(base):
    for folder, dirs, files in os.walk(base, followlinks=False):
        dirs[:] = [d for d in dirs if not (Path(folder)/d).lstat().st_file_attributes & stat.FILE_ATTRIBUTE_REPARSE_POINT and d != '__pycache__']
        for name in files:
            path = Path(folder)/name
            if not path.is_symlink():
                yield path

rows=[]
for parent in ('Tools','SourceAssets'):
    for base in (ROOT/parent).iterdir():
        if base.is_dir() and base.name.startswith(('Saiga12K','S12KStock')):
            for path in walk(base):
                rows.append({'path':path.relative_to(ROOT).as_posix(),'bytes':path.stat().st_size})
(OUT/'inventory.json').write_text(json.dumps(rows,indent=2),encoding='utf-8')
matches=[]
for parent in ('Source/FPSGAME','Content/ColdSteelData'):
    for path in walk(ROOT/parent):
        if path.suffix not in ('.cpp','.h','.inl','.json'):continue
        text=path.read_text(encoding='utf-8-sig',errors='replace')
        if any(x in text.lower() for x in ('saiga12k','s12k')):
            matches.append(path.relative_to(ROOT).as_posix())
matches.append('Source/FPSGAME/Characters/FPSPlayerBodyActions.cpp')
(OUT/'source-paths.json').write_text(json.dumps(matches,indent=2),encoding='utf-8')
diffdir=OUT/'Diffs';diffdir.mkdir(exist_ok=True)
for path in matches:
    diff=git('diff','--',path)
    (diffdir/(path.replace('/','__')+'.diff')).write_text(diff,encoding='utf-8')
print(json.dumps({'files':len(rows),'sources':len(matches),'output':str(OUT)}))
