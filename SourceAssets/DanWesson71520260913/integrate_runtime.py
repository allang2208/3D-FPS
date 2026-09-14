"""Install narrowly targeted 715 branches while preserving the current shared files."""
from pathlib import Path
import json
ROOT=Path(__file__).resolve().parents[2]
def edit(file,changes):
    p=ROOT/file;text=p.read_text(encoding='utf-8-sig')
    for old,new in changes:
        if old not in text:raise RuntimeError('Missing insertion in '+file+': '+old[:100])
        text=text.replace(old,new)
    p.write_text(text,encoding='utf-8')
edit('Source/FPSGAME/FPSGAMECharacter.h',[
 ('bool bUseM1911 = false;', 'bool bUseM1911 = false;\n    UPROPERTY(EditDefaultsOnly, Category = "Weapon|Model") bool bUseDanWesson715 = false;\n    bool IsPistolWeapon() const { return bUseM1911 || bUseDanWesson715; }')])
edit('Source/FPSGAME/FPSGAMECharacter.cpp',[
 ('#include "Weapons/M1911WeaponAssets.h"','#include "Weapons/M1911WeaponAssets.h"\n#include "Weapons/DanWesson715WeaponAssets.h"'),
 ('    bUsingReplacement = ViewmodelMesh != nullptr;', '''    if (bUseDanWesson715)
    {
        ViewmodelMesh = LoadObject<USkeletalMesh>(nullptr, DanWesson715WeaponAssets::MeshPath);
        bUsingM4Infima = ViewmodelMesh != nullptr;
        HipViewmodelLocation = FVector(0.f, 6.f, -5.f);
        ADSRearEyeDistance = 38.f;
        bPistolShotPending = false;
    }
    bUsingReplacement = ViewmodelMesh != nullptr;'''),
 ('AKMViewmodel->SetBoundsScale(bUseM1911 ? M1911WeaponAssets::ViewmodelBoundsScale : 1.f);','AKMViewmodel->SetBoundsScale(bUseDanWesson715 ? DanWesson715WeaponAssets::ViewmodelBoundsScale : bUseM1911 ? M1911WeaponAssets::ViewmodelBoundsScale : 1.f);\n        AKMViewmodel->EmptyOverrideMaterials();'),
 ('InspectAnimation = bUsingM4Infima || bUseM1911 ? nullptr : LoadAKMAnimation(TEXT("A_AKM_inspect"));','InspectAnimation = bUseDanWesson715 ? LoadAKMAnimation(TEXT("A_AKM_inspect")) : bUsingM4Infima || bUseM1911 ? nullptr : LoadAKMAnimation(TEXT("A_AKM_inspect"));'),
 ('bUsingM4Infima && !bUseQBZ191 && !bUseM1911','bUsingM4Infima && !bUseQBZ191 && !IsPistolWeapon()'),
 ('if (!bUseM1911)\n    {\n        InitializeForegripAnimations();','if (!IsPistolWeapon())\n    {\n        InitializeForegripAnimations();'),
 ('if (bUseM1911) { DrumReloadAnimation = nullptr; DrumReloadEmptyAnimation = nullptr; }','if (IsPistolWeapon()) { DrumReloadAnimation = nullptr; DrumReloadEmptyAnimation = nullptr; }'),
 ('bUsingM4Infima && !bUseM1911','bUsingM4Infima && !IsPistolWeapon()'),
 ('if (bUseM1911 && !bFireHeld)','if (IsPistolWeapon() && !bFireHeld)'),
 ('if (bUseM1911 && Animation)','if (IsPistolWeapon() && Animation)'),
 ('Gunsmith->Weapon(TEXT("ue_m1911"))','Gunsmith->Weapon(bUseDanWesson715 ? DanWesson715WeaponAssets::Definition : TEXT("ue_m1911"))'),
 ('        if (bUseQBZ191)\n        {\n            // QBZ uses', '''        if (bUseDanWesson715)
        {
            const float CueScale = bPendingEmptyReload ? DanWesson715WeaponAssets::EmptyReload / DanWesson715WeaponAssets::NormalReload : 1.f;
            MechanicalCueTimes = {DanWesson715WeaponAssets::Open * CueScale, DanWesson715WeaponAssets::Eject * CueScale,
                DanWesson715WeaponAssets::Insert * CueScale, DanWesson715WeaponAssets::Seat * CueScale, DanWesson715WeaponAssets::Close * CueScale};
            MechanicalCueSounds = {MagOutSound, ChargePullSound, MagInsertSound, MagSeatSound, ChargeReleaseSound};
        }
        if (bUseQBZ191)
        {
            // QBZ uses'''),
 ('return bUseM1911 ? FRotator(0.f, -90.f, 0.f) : ViewmodelRotation;','return IsPistolWeapon() ? FRotator(0.f, -90.f, 0.f) : ViewmodelRotation;'),
 ('(bUseM1911 ? BaseRotation : ADSViewmodelRotation)','(IsPistolWeapon() ? BaseRotation : ADSViewmodelRotation)'),
 ('(bUseM1911 && !bPistolShotPending)','(IsPistolWeapon() && !bPistolShotPending)'),
 ('if (bUseM1911) break;','if (IsPistolWeapon()) break;'),
 ('if (bUseM1911) bPistolShotPending = false;','if (IsPistolWeapon()) bPistolShotPending = false;'),
 ('bUseM1911 ? 1.5f : 1.0f','IsPistolWeapon() ? 1.5f : 1.0f'),
 ('if (bUseM1911) NextAllowedShotTime = WeaponActionStartedAt;','if (IsPistolWeapon()) NextAllowedShotTime = WeaponActionStartedAt;'),
 ('else if (bUseM1911)\n    {\n        // Original P9','else if (IsPistolWeapon())\n    {\n        // Original P9'),
 ('if (!bUseM1911 || !bInventoryWeaponReady','if (!IsPistolWeapon() || !bInventoryWeaponReady'),
 ('if (bUseM1911)\n    {\n        ActiveActionAnimation = nullptr;','if (IsPistolWeapon())\n    {\n        ActiveActionAnimation = nullptr;'),
 ('UAnimSequence* AFPSGAMECharacter::LoadAKMAnimation(const TCHAR* AssetName)\n{','''UAnimSequence* AFPSGAMECharacter::LoadAKMAnimation(const TCHAR* AssetName)
{
    if (bUseDanWesson715)
    {
        FString Clip(AssetName); Clip.RemoveFromStart(TEXT("A_AKM_"));
        if (Clip == TEXT("equip") || Clip == TEXT("equip_charge_empty")) Clip = TEXT("equip_charge");
        return LoadObject<UAnimSequence>(nullptr, *DanWesson715WeaponAssets::AnimationPath(*Clip));
    }'''),
 ('USoundBase* AFPSGAMECharacter::LoadAKMSound(const TCHAR* AssetName)\n{','''USoundBase* AFPSGAMECharacter::LoadAKMSound(const TCHAR* AssetName)
{
    if (bUseDanWesson715)
    {
        FString Cue(AssetName); Cue.RemoveFromStart(TEXT("S_AKM_"));
        return LoadObject<USoundBase>(nullptr, *DanWesson715WeaponAssets::SoundPath(Cue));
    }'''),
 ('if (bUseM1911 && !bHolographicOptic)','if (IsPistolWeapon() && !bHolographicOptic)'),
 ('if(bHolographicOptic || bUseM1911)','if(bHolographicOptic || IsPistolWeapon())'),
 ('if (bUseM1911 && GetGameInstance())','if (IsPistolWeapon() && GetGameInstance())'),
 ('((bUseQBZ191 || bUseM1911) && WeaponState','((bUseQBZ191 || IsPistolWeapon()) && WeaponState'),
 ('(bUseM1911 && IsReloading() ?','(IsPistolWeapon() && IsReloading() ?'),
 ('    if (bPistolWorkbench) GunplayAnimation->ActionAlpha = 0.0f;', '''    if (bPistolWorkbench) GunplayAnimation->ActionAlpha = 0.0f;
    GunplayAnimation->bRevolver = bUseDanWesson715;
    GunplayAnimation->RevolverLiveRounds = bPistolWorkbench ? 6 : MagazineAmmo;
    GunplayAnimation->RevolverCartridges = 6;
    if (bUseDanWesson715 && IsReloading() && !bPistolWorkbench)
    {
        const float SourceSeconds = ReloadSourceTime(WeaponStateElapsed) * (bPendingEmptyReload ? 3.2f / 3.45f : 1.f);
        if (SourceSeconds >= 1.20f)
        {
            const int32 Loaded = HasInfiniteReserveAmmo() ? 6 : FMath::Min(6, MagazineAmmo + ReserveAmmo);
            GunplayAnimation->RevolverLiveRounds = Loaded;
            GunplayAnimation->RevolverCartridges = Loaded;
        }
    }''')])
# The same readiness, item instance and posed-weapon pathways own every UI and
# drop representation. Only extend existing supported-definition predicates.
files=['Source/FPSGAME/FPSGAMECharacterProfile.cpp','Source/FPSGAME/UI/ColdSteelInventoryPopup.cpp','Source/FPSGAME/UI/ColdSteelInventoryPresentation.cpp','Source/FPSGAME/UI/ColdSteelInventoryWidget.cpp','Source/FPSGAME/UI/ColdSteelPickupStudio.cpp','Source/FPSGAME/UI/ColdSteelPickupWeapon.cpp','Source/FPSGAME/UI/ColdSteelWeaponIcons.cpp','Source/FPSGAME/UI/M4StandalonePreview.cpp']
for file in files:
    p=ROOT/file;t=p.read_text(encoding='utf-8-sig')
    for obj in ['I->','Selection->','Item.','I.']:
        eq=obj+'Definition==TEXT("ue_m1911")'
        ne=obj+'Definition!=TEXT("ue_m1911")'
        # Assignments are dealt with separately, so the M1911 flag stays exact.
        t=t.replace(eq, '('+eq+'||'+obj+'Definition==TEXT("ue_dan_wesson715"))')
        t=t.replace(ne, ne+'&&'+obj+'Definition!=TEXT("ue_dan_wesson715")')
    for prefix,obj in [('', 'I->'),('Rig->','Item.'),('Rig->','I.')]:
        old=prefix+'bUseM1911=('+obj+'Definition==TEXT("ue_m1911")||'+obj+'Definition==TEXT("ue_dan_wesson715"));'
        new=prefix+'bUseM1911='+obj+'Definition==TEXT("ue_m1911");'+prefix+'bUseDanWesson715='+obj+'Definition==TEXT("ue_dan_wesson715");'
        t=t.replace(old,new)
    p.write_text(t,encoding='utf-8')
edit('Source/FPSGAME/UI/ColdSteelWarehouseModel.cpp',[
 ('TEXT("ue_m1911"), TEXT("ue_rune_sword")','TEXT("ue_m1911"), TEXT("ue_dan_wesson715"), TEXT("ue_rune_sword")'),
 ('?7:30;', '?7:FString(Definition)==TEXT("ue_dan_wesson715")?6:30;'),
 ('        State.ArmoryReceived.Add(Definition);Changed=true;', '''        if(FString(Definition)==TEXT("ue_dan_wesson715"))
        {
            auto Ammo=CreateItem(TEXT("ammo_357"),60);
            if(Ammo.Data.IsEmpty()||!ColdSteelWarehouse::Insert(State.Items,Ammo,WarehouseCapacity()))return false;
        }
        State.ArmoryReceived.Add(Definition);Changed=true;''')])
edit('Source/FPSGAME/Weapons/GunsmithSystem.cpp',[
 ('#include "M1911WeaponAssets.h"','#include "M1911WeaponAssets.h"\n#include "DanWesson715WeaponAssets.h"'),
 ('        const auto B=O->GetObjectField(TEXT("base"));','        const auto B=O->GetObjectField(TEXT("base"));'),
 ('        if(W.Id==TEXT("ue_m1911"))','''        if(W.Id==DanWesson715WeaponAssets::Definition)
        {
            if(auto* Clip=LoadObject<UAnimSequence>(nullptr,*DanWesson715WeaponAssets::AnimationPath(TEXT("reload"))))W.Base.Reload=Clip->GetPlayLength();
            if(auto* Clip=LoadObject<UAnimSequence>(nullptr,*DanWesson715WeaponAssets::AnimationPath(TEXT("reload_empty"))))W.Base.EmptyReload=Clip->GetPlayLength();
        }
        if(W.Id==TEXT("ue_m1911"))''')])
for file,marker in [
 ('Source/FPSGAME/Weapons/M4GunsmithVisual.cpp','    if (bUseM1911) { SetM1911Optic(Variant); return; }'),
 ('Source/FPSGAME/Weapons/M4MuzzleVisual.cpp','    if (bUseM1911) { SetM1911Muzzle(Variant); return; }')]:
    edit(file,[(marker,'    if (bUseDanWesson715) return;\n'+marker)])
for file in ['Source/FPSGAME/Weapons/M4DrumVisual.cpp','Source/FPSGAME/Weapons/SkeletonStockVisual.cpp']:
    edit(file,[('if (bUseM1911) return;','if (IsPistolWeapon()) return;')])
edit('Source/FPSGAME/Weapons/M4MuzzleVisual.cpp',[('if(bUseM1911)return (AKMViewmodel','if(IsPistolWeapon())return (AKMViewmodel')])
edit('Source/FPSGAME/Weapons/FPSWeaponFXComponent.cpp',[
 ('    SpawnCasing();','    if (const auto* OwnerCharacter = Cast<AFPSGAMECharacter>(GetOwner()); !OwnerCharacter || !OwnerCharacter->bUseDanWesson715) SpawnCasing();'),
 ('Character && !Character->bUseM1911','Character && !Character->IsPistolWeapon()')])
edit('Source/FPSGAME/UI/ColdSteelAmmoReadout.cpp',[('Definition==TEXT("ammo_45acp")?TEXT(".45 ACP"):TEXT("")','Definition==TEXT("ammo_45acp")?TEXT(".45 ACP"):Definition==TEXT("ammo_357")?TEXT(".357 MAG"):TEXT("")')])
edit('Source/FPSGAME/UI/M4GunsmithLayout.cpp',[('W&&W->Ammo==TEXT("ammo_45acp")?', 'W&&W->Ammo==TEXT("ammo_357")?TEXT("   /   .357 Magnum"):W&&W->Ammo==TEXT("ammo_45acp")?')])
p=ROOT/'Config/DefaultGame.ini'
with p.open('a',encoding='utf-8') as f:f.write('\n+DirectoriesToAlwaysCook=(Path="/Game/Weapons/DanWesson715")\n')

p=ROOT/'Content/ColdSteelData/items.json';items=json.loads(p.read_text(encoding='utf-8-sig'))
items['ue_dan_wesson715']={'id':'ue_dan_wesson715','name':'Dan-Wesson 715','icon':'Icons/ue_dan_wesson715.png','ue_icon':'Icons/ue_dan_wesson715.png','icon_fallback':'715','category':'weapon','weaponType':'pistol','rangedType':'pistol','weaponTypeTag':'左轮手枪','equipSlot':'weapon','isTwoHanded':True,'rarity':'common','stack_max':1,'grid_w':3,'grid_h':2,'type':'武器','gunsmith_base_mag':6,'desc':'Dan-Wesson 715 六发左轮手枪，使用 .357 Magnum 弹药。按次点射，弹壳保留至开巢换弹。','stats':[{'name':'物理攻击','value':'68'},{'name':'弹巢容量','value':'6'}]}
items['ammo_357']={'id':'ammo_357','name':'.357 Magnum 左轮弹','category':'material','type':'弹药','rarity':'common','stack_max':999,'icon':'Icons/ammo_556.png','ue_icon':'Icons/ammo_556.png','icon_fallback':'▥','desc':'供 Dan-Wesson 715 使用的 .357 Magnum 弹药。'}
p.write_text(json.dumps(items,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
p=ROOT/'Content/ColdSteelData/gunsmith.json';catalog=json.loads(p.read_text(encoding='utf-8-sig'))
catalog['weapons'].append({'id':'ue_dan_wesson715','model':'Dan-Wesson715','name':'Dan-Wesson 715','allowed':['trigger','barrel'],'options':{'trigger':[{'id':'false','name':'原厂双动扳机','description':'按次扣动，一次一发。','effects':[],'stats':{}},{'id':'dw715_lightweight_fast','name':'轻型快速扳机','description':'最短点射间隔减少20%，仍须松开扳机再开火。','effects':[{'text':'射击间隔减少20%','benefit':1}],'stats':{'fire_interval_mult':.8}}]},'base':{'ammo_item_id':'ammo_357','mag_size':6,'ads_smooth':13.616964,'recoil':155,'camera_shake':125,'fire_interval':.32,'reload_time':3.2,'empty_reload_time':3.45,'damage':68,'bullet_speed':420,'effective_range':65}})
p.write_text(json.dumps(catalog,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('DW715_RUNTIME_INTEGRATED')
