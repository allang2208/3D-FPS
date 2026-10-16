"""Install newly authored packages only; preserve any unrelated or already installed destination."""
from pathlib import Path
import json,shutil,hashlib,subprocess
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parents[2]
SOURCE=ROOT.parent/'IntegrationV1/UEImportHost/Content/Building/PotionWorkbench20261015/RuntimeV2'
DEST=PROJECT/'Content/Building/PotionWorkbench20261015/RuntimeV2'
manifest=json.loads((ROOT/'Receipts/import-runtime.json').read_text('utf8'))
audio=json.loads((ROOT/'Receipts/import-audio.json').read_text('utf8'))
if manifest['stage']!='assets_saved':raise RuntimeError('Import incomplete')
paths=manifest['meshes']+manifest['materials']+audio['saved'];records=[]
receipt=ROOT/'Receipts/install-runtime.json'
previous={p['path']:p['sha256'] for p in json.loads(receipt.read_text('utf8'))['packages']} if receipt.exists() else {}
processes=subprocess.check_output(['tasklist','/FI','IMAGENAME eq UnrealEditor.exe','/FO','CSV','/NH'],text=True,errors='replace')
if 'UnrealEditor.exe' in processes:raise RuntimeError('Editor is running: retain staged packages for the existing asset bridge')
for package in paths:
    relative=Path(package.split('/RuntimeV2/',1)[1].split('.',1)[0]+'.uasset')
    src=SOURCE/relative;dest=DEST/relative
    if not src.is_file():raise RuntimeError('Saved package missing '+str(src))
    digest=hashlib.sha256(src.read_bytes()).hexdigest()
    if dest.exists() and hashlib.sha256(dest.read_bytes()).hexdigest() not in (digest,previous.get(str(dest))):raise RuntimeError('Preserve changed destination '+str(dest))
    records.append((src,dest,digest))
for src,dest,digest in records:
    dest.parent.mkdir(parents=True,exist_ok=True)
    if not dest.exists() or hashlib.sha256(dest.read_bytes()).hexdigest()!=digest:shutil.copy2(src,dest)
(ROOT/'Receipts/install-runtime.json').write_text(json.dumps({'stage':'installed','packages':[{'path':str(dest),'sha256':digest} for src,dest,digest in records],'runtime_tested':False,'auditioned':False},indent=2),'utf8')
print('ALCHEMY_PACKAGES_INSTALLED',len(records),DEST)
