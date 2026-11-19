"""Stage read-only supplier packages and their project texture dependencies."""
import json
import re
import shutil
import sys
from pathlib import Path

root,stage=map(Path,sys.argv[1:])
content=root/'Content'
inputs=json.loads(Path(__file__).with_name('surfaces.json').read_text())
pending=list(inputs.values())
seen=set()
while pending:
    package=pending.pop()
    if package in seen:
        continue
    seen.add(package)
    rel=Path(package.removeprefix('/Game/')+'.uasset')
    src=content/rel
    dest=stage/'Content'/rel
    dest.parent.mkdir(parents=True,exist_ok=True)
    data=src.read_bytes()
    shutil.copy2(src,dest)
    for ext in ('.ubulk','.uexp','.uptnl'):
        payload=src.with_suffix(ext)
        if payload.exists():
            shutil.copy2(payload,dest.with_suffix(ext))
    for imported in set(re.findall(rb'/Game/[a-zA-Z0-9_/-]+',data)):
        ref=imported.decode('ascii')
        if ref not in seen and (content/(ref[6:]+'.uasset')).is_file():
            pending.append(ref)
