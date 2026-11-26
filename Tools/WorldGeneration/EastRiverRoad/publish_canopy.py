"""Publish the isolated R2 asset folder as one directory on the official Content volume."""
from pathlib import Path
import json
import shutil
import sys
import tempfile
from publish_assets import digest

def publish(stage,project):
    rel=Path('WorldGeneration/TemperateHills/EastRiverRoad/CanopyR2')
    src=stage/'Host/Content'/rel
    dest=project/'Content'/rel
    files=sorted(p for p in src.rglob('*') if p.is_file())
    required={'SK_RoadHornbeam_04.uasset','SK_RoadHornbeam_05.uasset','PAL_RoadHornbeam.uasset','SKEL_RoadHornbeam.uasset'}
    if not required.issubset(f.name for f in files) or not (src/'Wind').is_dir():
        raise ValueError('Incomplete canopy packages')
    rows=[{'path':p.relative_to(src).as_posix(),'bytes':p.stat().st_size,'sha256':digest(p)} for p in files]
    if dest.exists():
        if any(not (dest/r['path']).exists() or digest(dest/r['path'])!=r['sha256'] for r in rows):
            raise FileExistsError(dest)
    else:
        with tempfile.TemporaryDirectory(dir=stage) as tmp:
            bundle=Path(tmp)/'CanopyR2'
            shutil.copytree(src,bundle)
            bundle.rename(dest)
    (stage/'published.json').write_text(json.dumps({'version':'EastRiverRoad-R2','root':str(rel),'packages':rows},indent=2))
if __name__=='__main__':publish(*(Path(s) for s in sys.argv[1:]))
