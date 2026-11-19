"""Publish the two NPC modules and owned shading assets, leaving other owners' NPC packages alone."""
import json,shutil
from pathlib import Path
P=Path('D:/FPS3D/FPSGAME');O=P/'SourceAssets/VillageBlacksmithNPC20261118/BodyOutfit';folder=Path('Characters/VillageBlacksmithNPC20261118')
source=O/'Host/Content'/folder;target=P/'Content'/folder
info=json.loads((O/'saved.json').read_text())
rels=[q.relative_to(source) for q in (source/'BodyOutfit').rglob('*') if q.is_file()]+[Path(n+'.uasset') for n in ('SK_Smith_Body','SK_Smith_Outfit')]
for rel in rels:
    src=source/rel;dst=target/rel
    if dst.exists() and src.read_bytes()!=dst.read_bytes():raise RuntimeError('An existing destination differs from the authored package '+str(dst))
for rel in rels:
    dst=target/rel
    if not dst.exists():
        dst.parent.mkdir(parents=True,exist_ok=True)
        tmp=dst.with_suffix(dst.suffix+'.smith-body-tmp');shutil.copy2(source/rel,tmp)
        tmp.replace(dst)
info['installed_packages']=[str(p).replace(chr(92),'/') for p in rels]
(O/'installed.json').write_text(json.dumps(info,indent=2))
print('SMITH_BODY_OUTFIT_INSTALLED',len(rels),str(target))
