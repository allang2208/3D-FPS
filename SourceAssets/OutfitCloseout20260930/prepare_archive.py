"""Build a scoped retirement manifest; native sources and active recipes stay."""
import hashlib,json
from pathlib import Path
P=Path('D:/FPS3D/FPSGAME').resolve();R=P/'SourceAssets/OutfitCloseout20260930';items={}
TRASH='trash/outfit-closeout-20260930'
if (P/'Docs/Publication/OutfitCloseout20260930/archive-manifest.json').exists():
 raise RuntimeError('This one-time archive is complete; use its manifest for recovery, not a rerun.')
def add(path,reason,replacement):
 path=Path(path).resolve();rel=path.relative_to(P).as_posix()
 if path.is_file():items[rel]=dict(source=rel,target=TRASH+'/'+rel,bytes=path.stat().st_size,sha256=hashlib.sha256(path.read_bytes()).hexdigest(),reason=reason,replacement=replacement)
def tree(path,reason,replacement):
 for p in Path(path).rglob('*'):
  if p.is_file():add(p,reason,replacement)
old=P/'SourceAssets/FieldSweaterCameraRepair20260930'
for p in old.rglob('*'):
 if not p.is_file():continue
 rel=p.relative_to(old).as_posix()
 # The native cache and one historical Traversal template are still inputs.
 if rel.startswith('Before/') and p.name!='shirt.json':continue
 if rel=='Authored/Traversal.json':continue
 add(p,'Superseded field-sweater generic-sleeve output and retired entry point','SourceAssets/FieldSweaterNativeFamily20260930')
charcoal=P/'SourceAssets/CharcoalGarmentRepair20260930'
for name in ['Body','BodyV2','BodyV3','Traversal']:
 tree(charcoal/'Saved'/name,'Superseded charcoal candidate snapshot','SourceAssets/CharcoalGarmentRepair20260930/Saved/'+('TraversalV2' if name=='Traversal' else 'BodyV4'))
registry=json.loads((R/'asset-referencers.json').read_text(encoding='utf-8-sig'))
config=(P/'Content/ColdSteelData/modular_outfits.json').read_text(encoding='utf-8-sig')+(P/'Content/ColdSteelData/items.json').read_text(encoding='utf-8-sig')
for row in registry:
 if row['outside_candidates']:raise RuntimeError('Referenced candidate: '+row['package'])
 if row['package']+'.' in config or '"'+row['package']+'"' in config:raise RuntimeError('Active candidate: '+row['package'])
 path=P/'Content'/(row['package'].removeprefix('/Game/')+'.uasset')
 add(path,'Superseded charcoal candidate; no external asset-registry or active catalog references','Content/Characters/ModularOutfit20260924/CharcoalGarmentRepair20260930/BodyV4, TraversalV2, PickupsV3')
for name in ['ChainmailInventoryIcon20260930','FieldSweaterInventoryIcons20260930']:
 tree(P/'SourceAssets'/name/'Before','Superseded inventory icon backup','Content/ColdSteelData/Icons')
roots=['ChainmailCameraClearance20260929','CharcoalCameraRepair20260930','CharcoalGarmentRepair20260930','FieldSweaterNativeFamily20260930','FieldSweaterSurfaceRepair20260930','FirearmChainmailReview20260930']
for name in roots:
 root=P/'SourceAssets'/name
 for p in root.iterdir():
  if p.is_file() and (p.suffix=='.txt' or p.name.startswith(('install_0','save_batch_','end_play')) or p.name=='save_svd.py'):
   add(p,'Completed transport log or one-time batch wrapper','Current install.py / Tools/ModularOutfit production entry points')
 for p in root.rglob('__pycache__'):tree(p,'Generated Python bytecode cache','Retained Python sources')
 for p in root.rglob('*.blend1'):
  if Path(str(p)[:-1]).is_file():add(p,'Blender automatic backup with retained editable source',str(p.relative_to(P))[:-1])
add(P/'Tools/ModularOutfit/sweater-production-console.txt','Completed production console output','Docs/Characters/field-sweater-knit-short-sleeve-20260929.md')
add(P/'SourceAssets/ApprenticeStaff20260927/CastElbowRepair20260930/compile-livecoding.json','Completed one-time build trigger','SourceAssets/ApprenticeStaff20260927/CastElbowRepair20260930/build-receipt.json')
data=dict(task='outfit-closeout-20260930',items=list(items.values()))
(R/'archive-plan.json').write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('ARCHIVE_PLAN',len(items),'files',round(sum(x['bytes'] for x in items.values())/1048576,2),'MiB')
