"""Publish this revision's new packages from an isolated editor host. Preserve existing work."""
from pathlib import Path
import hashlib
import json
import os
import shutil
import sys
import tempfile

def digest(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for part in iter(lambda:f.read(1048576),b''):h.update(part)
    return h.hexdigest()
def publish(stage, project):
    rel=Path('WorldGeneration/TemperateHills/EastRiverRoad')
    source=stage/'Host'/'Content'/rel
    output=project/'Content'/rel
    files=sorted(p for p in source.iterdir() if p.suffix in {'.uasset','.ubulk','.uexp'})
    required={'MI_EastRiverRoad','M_EastRoad_Sensei','PAL_EastRiverRoad','M_EastRoad_MossPatch','M_EastRoad_SoilPatch',
              'SM_CommonHazel_Forest_01','SM_CommonHazel_Forest_02'}
    if not required.issubset(p.stem for p in files):raise RuntimeError('Incomplete authoring output')
    output.mkdir(parents=True,exist_ok=True)
    entries=[]
    for p in files:
        target=output/p.name
        sha=digest(p)
        if target.exists() and digest(target)!=sha:raise FileExistsError(target)
        entries.append({'package':str(rel/p.name),'sha256':sha,'bytes':p.stat().st_size})
    for item,p in zip(entries,files):
        target=output/p.name
        if target.exists():continue
        with tempfile.NamedTemporaryFile(dir=output,suffix='.tmp',delete=False) as f:
            tmp=Path(f.name)
        try:
            shutil.copyfile(p,tmp)
            os.link(tmp,target)
        finally:tmp.unlink(missing_ok=True)
    (stage/'published.json').write_text(json.dumps(entries,indent=2))
if __name__=='__main__':publish(*(Path(arg) for arg in sys.argv[1:]))

