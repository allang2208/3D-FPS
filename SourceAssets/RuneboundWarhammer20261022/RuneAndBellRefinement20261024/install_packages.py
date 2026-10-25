"""Install only newly saved packages and the runtime PNGs, then publish visuals."""
from pathlib import Path
import hashlib,json,shutil,runpy
P=Path(__file__).resolve().parent;ROOT=P.parents[2]
receipt=json.loads((P/'import_receipt.json').read_text('utf-8'))
if not receipt.get('complete') or receipt.get('rune_masks')!=2:raise RuntimeError('Complete isolated authoring first')
files=[]
for asset in receipt['assets']:
    relative=Path(asset.removeprefix('/Game/').split('.')[0])
    source=P/'AuthorHost/Content'/relative
    for path in source.parent.glob(source.name+'.*'):
        target=ROOT/'Content'/relative.parent/path.name
        data=path.read_bytes();target.parent.mkdir(parents=True,exist_ok=True)
        if target.exists():
            if target.read_bytes()!=data:raise RuntimeError('Preserve existing package '+str(target))
        else:
            with target.open('xb') as output:output.write(data)
        files.append({'path':str(target.relative_to(ROOT)),'sha256':hashlib.sha256(data).hexdigest()})
for source in (P/'Icons').glob('*.png'):
    target=ROOT/'Content/ColdSteelData/AttachmentIcons20260913'/source.name
    backup=P/'Before'/source.name
    if target.exists() and not backup.exists():shutil.copy2(target,backup)
    shutil.copy2(source,target)
receipt.update(installed_to_main_project=True,installed_files=files,icons_storage='Runtime PNG + new saved Texture2D in RuneIconsV3; old root Texture2D retained as inactive source')
(P/'import_receipt.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf-8')
runpy.run_path(str(P/'publish.py'))['publish']()
print('Installed '+str(len(files))+' new package files; active PNGs replaced')
