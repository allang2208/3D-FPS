"""Install the two M249 PNG keys, retaining the previous production files."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import tempfile
import zipfile

here=Path(__file__).resolve().parent
project=here.parents[2]
icons=project/'Content/ColdSteelData/AttachmentIcons20260913/FramedFirearms'
master=here/'M249_Bipod_Framed.png'
keys=('ue_m249_bipod_false','ue_m249_category_bipod')
def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

if __name__=='__main__':
    target=digest(master)
    archive=project/'trash/M249BipodIcon42/before.zip'
    archive.parent.mkdir(parents=True,exist_ok=True)
    manifest=here/'deployment.json'
    if not manifest.exists():
        old={p.name:digest(p) for key in keys for p in (icons/(key+'.png'),icons/(key+'.uasset'))}
        with zipfile.ZipFile(archive,'x',zipfile.ZIP_DEFLATED) as back:
            for name in old: back.write(icons/name,(icons/name).relative_to(project))
        manifest.write_text(json.dumps(dict(before=old, pngs=list(keys), master=master.name,
            master_sha256=target, archive=str(archive.relative_to(project)),
            frame='SourceAssets/KukriRefinement20261027/StandardEmptyFrame.png',
            frame_reference='SourceAssets/FirearmFramedIcons20260930/muzzle_brake_framed_v2.png',
            meshes=['/Game/Weapons/M249/Bipod/SM_M249_Bipod_'+key for key in ('Base','LegA','LegB')],
            pose='Authored open pose, orthographic camera, muzzle facing left',
            removal='Retained shared silver minus, matching bipod_false.png'),indent=2))
    record=json.loads(manifest.read_text())
    if record['master_sha256']!=target: raise RuntimeError('Icon master changed during installation')
    for key in keys:
        dest=icons/(key+'.png')
        if digest(dest)==target: continue
        if digest(dest)!=record['before'][dest.name]: raise RuntimeError('Production PNG changed: '+key)
        with tempfile.NamedTemporaryFile(dir=icons,delete=False) as f: temp=Path(f.name)
        try:
            shutil.copyfile(master,temp)
            os.replace(temp,dest)
        finally:
            temp.unlink(missing_ok=True)
    print('M249_BIPOD_PNG_PUBLISHED',len(keys),target)
