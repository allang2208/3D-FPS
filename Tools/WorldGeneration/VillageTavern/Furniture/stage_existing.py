"""Copy the existing owned packages and any extra project overrides into the private mount."""
import hashlib
import json
import re
import shutil
import sys
from pathlib import Path


root, stage = map(Path,sys.argv[1:3])
content = root/'Content'
private = stage/'Content'
directory = Path('WorldGeneration/VillageTavern/Furniture')
names = ['SM_Tavern'+s for s in ('Table','Stool','Counter','Backbar','BrokenTable','BrokenStool','BrokenCounter')]
names.append('M_TavernOiledOak')
if 'dining-finish' in sys.argv[3:]:
    names = ['SM_TavernTable','M_TavernOiledOak','M_TavernDiningOak','T_TavernTableWear']
original = {}
payloads = {}
pending = []
for name in names:
    rel = directory/(name+'.uasset')
    path = content/rel
    original[name] = hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else None
    for extension in ('.ubulk','.uexp','.uptnl'):
        payload=path.with_suffix(extension)
        payloads[payload.name]=hashlib.sha256(payload.read_bytes()).hexdigest() if payload.is_file() else None
    if path.exists():
        pending.append(rel)

while pending:
    rel = pending.pop()
    dest = private/rel
    if dest.exists():
        continue
    source = content/rel
    dest.parent.mkdir(parents=True,exist_ok=True)
    shutil.copy2(source,dest)
    for ext in ('.ubulk','.uexp','.uptnl'):
        other = source.with_suffix(ext)
        if other.is_file():
            shutil.copy2(other,dest.with_suffix(ext))
    data = dest.read_bytes()
    # The package name map carries /Game imports, also for material instances
    # assigned by hand. Existing donor packages already staged are left alone.
    imports = {s.decode('ascii') for s in re.findall(rb'/Game/[A-Za-z0-9_/-]+',data)}
    for match in re.finditer('/Game/'.encode('utf-16le'),data):
        start=match.start()
        # Package FNames are null-terminated UTF-16 for non-ASCII filenames.
        text=data[start:start+4096].decode('utf-16le',errors='ignore').split('\x00',1)[0]
        key=re.match(r'/Game/[\w/-]+',text)
        if key:
            imports.add(key.group())
    for package in imports:
        candidate = Path(package[6:]+'.uasset')
        if (content/candidate).is_file() and not (private/candidate).is_file():
            pending.append(candidate)
(stage/'original.json').write_text(json.dumps(original,indent=2),encoding='utf-8')
(stage/'original-payloads.json').write_text(json.dumps(payloads,indent=2),encoding='utf-8')
