"""Replace only the oath modification icon; retain the superseded icon in trash."""
from pathlib import Path
import hashlib,json,shutil
P=Path(__file__).resolve().parent
ROOT=P.parents[2]
KEY='ue_highland_claymore_blade_2_highland_oath_rune'
SOURCE=Path('C:/Users/allan/.codex/generated_images/01a1a6e8-d97c-7b30-b4ff-9174f8b522f1/exec-9f84e9bf-71f9-4724-a84a-c0c1109bed2c.png')
MASTER=P/'OathRune_Framed_V2.png'
DEST=ROOT/'Content/ColdSteelData/AttachmentIcons20260913'
CANONICAL=P.parent/'Icons'/(KEY+'.png')
ARCHIVE=ROOT/'trash/HighlandOathRuneIconV1_20261106'
ARCHIVE.mkdir(parents=True,exist_ok=True)
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
records=[]
for source,name in [(CANONICAL,'source-icon-v1.png'),(DEST/(KEY+'.png'),'runtime-icon-v1.png'),(DEST/(KEY+'.uasset'),'runtime-texture-v1.uasset')]:
    if not source.exists():continue
    target=ARCHIVE/name
    if not target.exists():shutil.copy2(source,target)
    records.append({'original':str(source),'archive':str(target),'bytes':target.stat().st_size,'sha256':sha(target)})
(ARCHIVE/'manifest.json').write_text(json.dumps({'reason':'Superseded by the approved-standard frame and inset rune composition','retained_master':str(MASTER),'files':records},indent=2),encoding='utf-8')
shutil.copy2(SOURCE,MASTER)
shutil.copy2(MASTER,CANONICAL)
shutil.copy2(MASTER,DEST/(KEY+'.png'))
(P/'publication.json').write_text(json.dumps({'generated_source':str(SOURCE),'master':str(MASTER),'frame_reference':str(ROOT/'SourceAssets/FirearmFramedIcons20260930/muzzle_brake_framed_v2.png'),'deployed_png':str(DEST/(KEY+'.png')),'texture':'/Game/ColdSteelData/AttachmentIcons20260913/'+KEY,'sha256':sha(MASTER),'gameplay_tested':False},indent=2),encoding='utf-8')
print('Oath V2 master and active PNG deployed; old icon copies retained in trash.')
