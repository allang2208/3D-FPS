"""Lossless diagnostic crops at original pixel size; no authored texture edits."""
import json
from pathlib import Path
from PIL import Image
ROOT=Path(__file__).resolve().parents[1]
source=json.loads((ROOT.parent/'DungeonWallDamage20260923/Sources/provenance.json').read_text())
for entry in source['source_textures']:
    path=Path(entry['file'])
    if '_BaseColor_' not in path.name:continue
    udim=path.stem.rsplit('.',1)[1]
    with Image.open(path) as im:
        rect=tuple(int(v*im.size[i%2]) for i,v in enumerate(entry['crop']))
        im.crop(rect).save(ROOT/'Images'/('fab_original_crop_'+udim+'.png'))
    print('SOURCE_CROP',udim,rect)
