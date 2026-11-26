"""Install the isolated asset and change only the two modern glove rig entries."""
import hashlib
import json
import os
import shutil
import sys
import tempfile
from pathlib import Path

from native_glove_profile import P,R,BASE,RIG,GUNS,SOURCE_FILE
sys.path.insert(0,str(P/'Tools/BrownLeatherSet'))
from json_entries import replace

def sha(path):
    with path.open('rb') as f:
        return hashlib.file_digest(f,'sha256').hexdigest()

def install():
    receipt = json.loads((R/'saved.json').read_text())
    old = json.loads((R/'Read/R4.json').read_text())['source']
    new = receipt['asset']
    if receipt['source_sha256']!=sha(SOURCE_FILE) or len(receipt['triangles'])!=3 or min(receipt['triangles'])<1:
        raise RuntimeError('Authored source and saved render LODs must agree')
    package = Path(new.split('.')[0][6:]+'.uasset')
    staged = BASE/'Stage/Content'/package
    dest = P/'Content'/package
    dest.parent.mkdir(parents=True,exist_ok=True)
    stage_hash=sha(staged)
    if not dest.exists():
        fd,tmp=tempfile.mkstemp(dir=dest.parent,suffix='.tmp')
        os.close(fd)
        try:
            shutil.copyfile(staged,tmp)
            os.rename(tmp,dest)  # Windows rename does not overwrite an existing file.
        finally:
            Path(tmp).unlink(missing_ok=True)
    if sha(dest)!=stage_hash:
        raise RuntimeError('The target package already contains a different revision')
    config = P/'Content/ColdSteelData/modular_outfits.json'
    field = ['ue_modern_tactical_gloves','rig_meshes',RIG]
    for _ in range(4):
        before=config.read_bytes()
        text=before.decode('utf-8-sig')
        for prefix in (['items'],['body_variants','kaitlin','items']):
            keys=prefix+field
            value=json.loads(text)
            for key in keys:
                value=value[key]
            if value not in (old,new):
                raise RuntimeError('Concurrent edit to the shotgun glove route '+str(keys))
            text=replace(text,keys,new)
        fd,tmp=tempfile.mkstemp(dir=config.parent,suffix='.tmp')
        try:
            with os.fdopen(fd,'wb') as out:
                out.write((b'\xef\xbb\xbf' if before.startswith(b'\xef\xbb\xbf') else b'') + text.encode('utf8'))
            if config.read_bytes()!=before:
                continue
            os.replace(tmp,config)
            break
        finally:
            Path(tmp).unlink(missing_ok=True)
    else:
        raise RuntimeError('Outfit catalog continuously changing')
    (R/'published.json').write_text(json.dumps(dict(asset=new,sha256=stage_hash,
        routes=['Jason/'+RIG,'Kaitlin/'+RIG],weapon_aliases=GUNS),indent=2))
    print('INSTALLED_NATIVE_SHOTGUN_GLOVES',dest)

if __name__=='__main__':
    install()
