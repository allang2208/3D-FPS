"""Deploy the three imagegen icons unchanged and archive the rejected images."""
from pathlib import Path
import hashlib,json,shutil
O=Path(__file__).parent;P=O.parents[1]
G=Path(r'C:/Users/allan/.codex/generated_images/01a13b04-04c2-7722-a3ed-2f3b70dc30f2')
archive=P/'trash/shotgun-icons-rejected-20261015'
rows=[
 ('shotgun_choke','exec-4ed336cd-312b-461d-88b7-273d7ad0c500.png','Super90Choke20261015','Choke20261015','T_ShotgunChoke_Icon'),
 ('shotgun_birdcage_flash_hider','exec-dd44939e-10e3-4b3c-baf5-38a44c9bcc3a.png','Super90Birdcage20261015','Birdcage20261015','T_ShotgunBirdcage_Icon'),
 ('shotgun_suppressor','exec-477ade79-e51f-4858-a626-88e5750ffe3f.png','Super90Suppressor20261015','Suppressor20261015','T_ShotgunSuppressor_Icon'),
]
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
backups=[]
def backup(path):
    if not path.exists():return
    dest=archive/path.relative_to(P)
    dest.parent.mkdir(parents=True,exist_ok=True)
    if not dest.exists():shutil.copy2(path,dest)
    backups.append({'original':str(path),'archive':str(dest),'sha256':sha(dest)})
(O/'Final').mkdir(exist_ok=True)
manifest=[]
for key,generated,author,family,texture in rows:
    filename='muzzle_'+key+'.png';source=G/generated;final=O/'Final'/filename
    shutil.copy2(source,final)
    targets=[P/'Content/ColdSteelData/AttachmentIcons20260913/FramedFirearms'/filename,
             P/'SourceAssets'/author/filename]
    packages=['/Game/ColdSteelData/AttachmentIcons20260913/FramedFirearms/'+Path(filename).stem,
              '/Game/Weapons/CommonShotgun/'+family+'/UI/'+texture]
    for target in targets:backup(target);shutil.copy2(final,target)
    for package in packages:backup(P/'Content'/(package.removeprefix('/Game/')+'.uasset'))
    author_script=P/'SourceAssets'/author/'author_icon.py';backup(author_script)
    author_script.write_text('''"""Restore the current framed icon; the simplified Blender frame is retired.
When model geometry changes, regenerate through the documented imagegen workflow.
"""
from pathlib import Path
import shutil
O=Path(__file__).parent
source=O.parent/'ShotgunIconsFramed20261015/Final/'''+filename+"'\nshutil.copy2(source,O/'"+filename+"')\nprint('CURRENT_FRAMED_SHOTGUN_ICON_RESTORED')\n",encoding='utf-8')
    manifest.append({'id':key,'generated_source':str(source),'final':str(final),
        'png_targets':[str(t) for t in targets],'packages':packages,'sha256':sha(final),
        'mode':'built-in imagegen reference-guided edit; PNG copied without raster processing'})
(O/'deployment_receipt.json').write_text(json.dumps({'icons':manifest,'backups':backups,'runtime_tested':False},indent=2),encoding='utf-8')
(archive/'manifest.json').write_text(json.dumps(backups,indent=2),encoding='utf-8')
print('SHOTGUN_FRAMED_PNGS_DEPLOYED',len(manifest))
