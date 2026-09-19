"""Narrow source edits; preserve all pre-existing parallel work and record our baseline."""
from pathlib import Path
import json,hashlib
P=Path(__file__).parent;R=P.parents[1];B=P/'Before';B.mkdir(exist_ok=True)
manifest=[]
def edit(rel,fn):
 p=R/rel;before=p.read_bytes();text=before.decode('utf-8-sig');out=fn(text)
 if out==text:return
 target=B/rel;target.parent.mkdir(parents=True,exist_ok=True)
 if not target.exists():target.write_bytes(before)
 assert p.read_bytes()==before
 p.write_bytes(out.encode('utf-8'));manifest.append({'path':rel,'before_sha256':hashlib.sha256(before).hexdigest(),'after_sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
def insert(s,needle,extra):
 assert s.count(needle)==1,(needle,s.count(needle));return s.replace(needle,needle+extra)
edit('Source/FPSGAME/FPSGAMECharacter.h',lambda s:insert(s,'    void SetGunsmithHandstop(const FString& Variant);','\r\n    void SetGunsmithStock(const FString& Variant);\r\n    bool HasSkeletonStock() const;\r\n    bool ValidateStockAttachment() const;\r\n    void RunStockAudit();\r\n    UPROPERTY(Transient) TObjectPtr<class UStaticMeshComponent> StockAttachment;\r\n    FTransform StockMount;\r\n    bool bSkeletonStock=false;\r\n    int32 StockAuditStage=0, StockAuditChecks=0, StockAuditFailures=0;\r\n    float StockAuditNextTime=0.f;'))
def character(s):
 s=insert(s,'void AFPSGAMECharacter::InitializeWeaponVisuals()\r\n{','\r\n    if(StockAttachment)StockAttachment->DestroyComponent();\r\n    StockAttachment=nullptr;bSkeletonStock=false;')
 needle='    USkeletalMesh* ViewmodelMesh = LoadObject<USkeletalMesh>(nullptr, TEXT("/Game/Weapons/AKMIntegration/SovietFab/Attachments/SK_AKM_MannyNative.SK_AKM_MannyNative"), nullptr, LOAD_NoWarn);'
 assert needle in s
 s=s.replace(needle,'    USkeletalMesh* ViewmodelMesh = LoadObject<USkeletalMesh>(nullptr, TEXT("/Game/Weapons/AKMIntegration/SovietFab/Stock/SK_AKM_MannyNative.SK_AKM_MannyNative"), nullptr, LOAD_NoWarn);\r\n'+needle.replace('USkeletalMesh* ViewmodelMesh =','if (!ViewmodelMesh) ViewmodelMesh ='))
 return insert(s,'    if (bRunDrumGripAudit) RunDrumGripAudit();','\r\n    if (FParse::Param(FCommandLine::Get(), TEXT("SkeletonStockAudit"))) RunStockAudit();')
edit('Source/FPSGAME/FPSGAMECharacter.cpp',character)
edit('Source/FPSGAME/FPSGAMECharacterProfile.cpp',lambda s:insert(s,'        SetGunsmithHandstop(VisualParts.FindRef(TEXT("underbarrel")));','\r\n        SetGunsmithStock(VisualParts.FindRef(TEXT("stock")));'))
for rel in ['Source/FPSGAME/UI/ColdSteelWeaponIcons.cpp','Source/FPSGAME/UI/M4StandalonePreview.cpp','Source/FPSGAME/UI/ColdSteelPickupWeapon.cpp']:
 edit(rel,lambda s:insert(s,'Rig->SetGunsmithMuzzle(Parts.FindRef(TEXT("muzzle")));','Rig->SetGunsmithStock(Parts.FindRef(TEXT("stock")));'))
edit('Source/FPSGAME/UI/M4GunsmithWidget.cpp',lambda s:s.replace('C->SetGunsmithHandstop(Model()->Draft().FindRef(TEXT("underbarrel")));','C->SetGunsmithHandstop(Model()->Draft().FindRef(TEXT("underbarrel")));\n            C->SetGunsmithStock(Model()->Draft().FindRef(TEXT("stock")));'))
def catalog(s):
 d=json.loads(s)
 for w in d['weapons']:
  if w['id'] not in ['ue_m4a1','ue_akm']:continue
  if 'stock' not in w['allowed']:w['allowed'].append('stock')
  w['options']['stock']=[{'id':'false','name':'原厂枪托','description':'恢复当前枪械的原厂枪托。','effects':[],'stats':{}},{'id':'skeleton','name':'三角镂空枪托','description':'轻质骨架、低位贴腮板与橡胶抵肩垫，使用对应枪型的安装接口。','effects':[{'text':'ADS瞄准耗时减少20%','benefit':1},{'text':'后坐力增加10%','benefit':-1},{'text':'枪械晃动增加10%','benefit':-1}],'stats':{'ads_percent':-.2,'recoil_mult':1.1,'shake_mult':1.1}}]
 return json.dumps(d,ensure_ascii=False,indent=2)+'\n'
edit('Content/ColdSteelData/gunsmith.json',catalog)
edit('Config/DefaultGame.ini',lambda s:s+'\r\n[/Script/UnrealEd.ProjectPackagingSettings]\r\n+DirectoriesToAlwaysCook=(Path="/Game/Weapons/SkeletonStock")\r\n' if '/Game/Weapons/SkeletonStock' not in s else s)
(P/'code_changes.json').write_text(json.dumps(manifest,indent=2));print('STOCK_CODE_INTEGRATED',len(manifest))
