"""Prepare an isolated visual revision, keeping original authored inputs intact."""
from pathlib import Path
import json,hashlib
ROOT=Path(__file__).resolve().parents[1];BASE=ROOT.parent;PROJECT=ROOT.parents[2]
for d in ('Authored','Export','Textures','Icons','Receipts','Before','UEImportHost/Config'):(ROOT/d).mkdir(parents=True,exist_ok=True)
for name in ('geometry.py','author_models.py','import_assets.py','import_staged.ps1','render_icons.py'):
    t=(BASE/'Scripts'/name).read_text('utf-8-sig').replace('PROJECT=ROOT.parents[1]','PROJECT=ROOT.parents[2]')
    if name=='import_assets.py':
        t=t.replace("DEST='/Game/Items/IncinerationCollectibles20261015/V1'", "DEST='/Game/Items/IncinerationCollectibles20261015/V2'")
        t=t.replace("mesh=imp(spec['fbx'],spec['mesh'],DEST+'/Meshes',options)", "mesh=imp(spec['fbx'],spec['mesh'],'/Game/Items/IncinerationCollectibles20261015/V1/Meshes',options)")
    if name=='render_icons.py':
        t=t.replace("OUT=ROOT/'IconLayoutV2';ICONS=OUT", "OUT=ROOT/'Icons';ICONS=OUT")
        t=t.replace("def record():(ROOT/'icon-layout-v2.json')", "def record():(ROOT/'presentation.json')")
        t=t.replace("light(scene,'Soft fill',(4,-1.5,4),450,3.5)", "light(scene,'Soft fill',(4,-1.5,4),280,3.5)")
        t=t.replace("light(scene,'Underside softbox',(-1,1,-5),280,3)", "light(scene,'Underside softbox',(-1,1,-5),100,3)")
        t=t.replace("'requested_preview':False", "'requested_preview':True")
    (ROOT/'Scripts'/name).write_text(t,encoding='utf-8-sig' if name.endswith('.ps1') else 'utf-8')
host=BASE/'UEImportHost'
for rel in ('IncinerationCollectiblesImport.uproject','Config/DefaultEngine.ini'):
    (ROOT/'UEImportHost'/rel).write_text((host/rel).read_text('utf-8-sig'),encoding='utf-8')
snapshot={}
for p in sorted((PROJECT/'Content/Items/IncinerationCollectibles20261015/V1/Meshes').glob('*.uasset')):
    snapshot[str(p.relative_to(PROJECT))]=hashlib.sha256(p.read_bytes()).hexdigest()
out=ROOT/'Before/original-mesh-hashes.json'
if not out.exists():out.write_text(json.dumps(snapshot,indent=2),encoding='utf-8')
print('DETAIL_REVISION_PREPARED')
