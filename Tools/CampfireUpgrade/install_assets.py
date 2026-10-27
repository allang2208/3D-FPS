"""Publish only this batch's saved new packages and production icons."""
from pathlib import Path
import json, shutil, hashlib
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'SourceAssets/CampfireUpgrade20261026'
receipt=json.loads((OUT/'ue-authoring.json').read_text(encoding='utf-8'))
published=[]
def publish(source,dest):
    if not source.is_file():raise RuntimeError('Missing saved asset '+str(source))
    if dest.exists() and source.read_bytes()!=dest.read_bytes():raise RuntimeError('Destination already contains different asset: '+str(dest))
    dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,dest)
    published.append({'path':str(dest.relative_to(ROOT)),'sha256':hashlib.sha256(dest.read_bytes()).hexdigest()})
for object_path in receipt['saved_assets']:
    package=object_path.split('.')[0]
    if not package.startswith('/Game/Items/Consumables/WildGame20261026/'):raise RuntimeError('Unexpected package '+package)
    relative=Path(package.removeprefix('/Game/')+'.uasset')
    publish(OUT/'AssetHost/Content'/relative,ROOT/'Content'/relative)
for row in json.loads((OUT/'foods.json').read_text(encoding='utf-8')):
    for key in ('raw','cooked'):
        name=row[key]+'.png';publish(OUT/'Icons'/name,ROOT/'Content/ColdSteelData/Icons'/name)
(OUT/'assets-published.json').write_text(json.dumps({'files':published,'gameplay_test':False},ensure_ascii=False,indent=2),encoding='utf-8')
print('Published',len(published),'campfire files')
