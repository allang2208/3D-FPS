"""Keep this task's delta separate from other uncommitted weapon development."""
import difflib,json
from pathlib import Path
P=Path(__file__).parent;root=P.parent.parent;patch=[]
def add(path,old,new):
 patch.extend(difflib.unified_diff(old.splitlines(True),new.splitlines(True),fromfile='a/'+path,tofile='b/'+path))
path='Source/FPSGAME/Weapons/SkeletonStockVisual.cpp';new=(root/path).read_text(encoding='utf-8');old=new
old=old.replace('    const bool QR=Variant==TEXT("qr_performance");\n','').replace('(Variant==TEXT("skeleton")||QR)','Variant==TEXT("skeleton")')
old=old.replace('    if(Enabled)\n    {\n','    if(Enabled&&!StockAttachment)\n    {\n')
start=old.index('        const TCHAR* StockPath=QR');end=old.index('        auto* StockMesh=',start)
old=old[:start]+'        const TCHAR* StockPath=AKM?TEXT("/Game/Weapons/ReferenceStock5080/AKM/SM_SkeletonStock.SM_SkeletonStock"):TEXT("/Game/Weapons/ReferenceStock5080/SM_SkeletonStock.SM_SkeletonStock");\n'+old[end:]
old=old.replace('        if(!StockAttachment)\n        {\n','').replace('        StockAttachment->SetCollisionEnabled(', '        StockAttachment->SetStaticMesh(StockMesh);\n        StockAttachment->SetCollisionEnabled(')
old=old.replace('        }\n        // Replace the mesh when changing options on an existing workbench/icon rig.\n        StockAttachment->SetStaticMesh(StockMesh);\n','')
add(path,old,new)
path='Content/ColdSteelData/gunsmith.json';new=(root/path).read_text(encoding='utf-8-sig');doc=json.loads(new)
for weapon in doc['weapons']:
 if weapon['id'] in ['ue_m4a1','ue_akm']:
  options=weapon['options'];options['stock']=[v for v in options['stock'] if v['id']!='qr_performance']
old=json.dumps(doc,ensure_ascii=False,indent=2)+'\n';add(path,old,new)
path='Config/DefaultGame.ini';new=(root/path).read_text(encoding='utf-8-sig');old=new.replace('+DirectoriesToAlwaysCook=(Path="/Game/Weapons/QRPerformanceStock")\n','');add(path,old,new)
(P/'qr_integration.patch').write_text(''.join(patch),encoding='utf-8')
