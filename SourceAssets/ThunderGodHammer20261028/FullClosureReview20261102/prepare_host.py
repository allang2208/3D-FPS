"""Snapshot source/config/native plugins; Content is a read-only test dependency."""
from pathlib import Path
import hashlib, json, shutil, subprocess

ROOT=Path('D:/FPS3D/FPSGAME')
HOST=Path('D:/FPS3D/ThunderHammerFullReviewHost20261102')
OUT=Path(__file__).parent
HOST.mkdir(exist_ok=True)
for name in ('Source','Config','Binaries','Build'):
    if (ROOT/name).exists():
        shutil.copytree(ROOT/name,HOST/name,dirs_exist_ok=True,ignore=shutil.ignore_patterns('*.pdb','*.exp','*.ilk'))
shutil.copy2(ROOT/'FPSGAME.uproject',HOST/'FPSGAME.uproject')
for plugin in (ROOT/'Plugins').iterdir():
    if not plugin.is_dir(): continue
    dest=HOST/'Plugins'/plugin.name
    shutil.copytree(plugin,dest,dirs_exist_ok=True,ignore=shutil.ignore_patterns('Intermediate','Saved','.git','Content','*.pdb'))
    if (plugin/'Content').exists() and not (dest/'Content').exists():
        subprocess.run(['powershell','-NoProfile','-Command',f"New-Item -ItemType Junction -Path '{dest/'Content'}' -Target '{plugin/'Content'}' | Out-Null"],check=True)
if not (HOST/'Content').exists():
    subprocess.run(['powershell','-NoProfile','-Command',f"New-Item -ItemType Junction -Path '{HOST/'Content'}' -Target '{ROOT/'Content'}' | Out-Null"],check=True)
rows=[]
for base in ('Source','Config'):
    for p in (HOST/base).rglob('*'):
        if p.is_file(): rows.append({'path':str(p.relative_to(HOST)),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
(OUT/'host-snapshot.json').write_text(json.dumps({'host':str(HOST),'source':str(ROOT),'content_target':str((ROOT/'Content').resolve()),'content_write_allowed':False,'files':rows},indent=2),encoding='utf-8')
print(f'Snapshot ready: {HOST}; {len(rows)} source/config files')
