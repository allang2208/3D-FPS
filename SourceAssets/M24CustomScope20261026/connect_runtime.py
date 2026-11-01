"""Apply the M24's narrow integration points to the current shared files."""
from pathlib import Path
P=Path('D:/FPS3D/FPSGAME/Source/FPSGAME')
changed=[]
def edit(file, pairs):
    p=P/file; text=p.read_text(encoding='utf-8-sig')
    for old,new in pairs:
        if new in text:continue
        if old not in text:raise RuntimeError('Integration anchor changed: '+file+' '+old[:80])
        text=text.replace(old,new)
    p.write_text(text,encoding='utf-8');changed.append(file)

edit('FPSGAMECharacter.h',[
('    bool IsM870Weapon() const', '''    bool IsM24Weapon() const { return ActiveInventoryWeaponDefinition==TEXT("ue_m24"); }
    float M24CyclePlayRate() const;
    void UpdateM24CycleAudio();
    void PreserveInterruptedM24Cycle();
    uint8 M24CycleCueMask=0;
    TSet<FString> M24PendingCasingWeapons;
    bool IsM870Weapon() const'''),
('return MuzzleVariant==TEXT("true")','return IsM24Weapon()||MuzzleVariant==TEXT("true")'),
('    bool HasSVDFactoryScope() const','    bool HasM24FactoryScope() const { return IsM24Weapon(); }\n    bool HasSVDFactoryScope() const')])
edit('FPSGAMECharacter.cpp',[
('#include "Weapons/SVCHWeaponAssets.h"','#include "Weapons/SVCHWeaponAssets.h"\n#include "Weapons/M24WeaponAssets.h"'),
('    bUsingReplacement = ViewmodelMesh != nullptr;', '''    if(IsM24Weapon())
    {
        ViewmodelMesh=LoadObject<USkeletalMesh>(nullptr,M24WeaponAssets::MeshPath);
        bUsingM4Infima=ViewmodelMesh!=nullptr;
        bSingleShotTrigger=true;bPistolShotPending=false;
        HipViewmodelLocation=M4HipViewmodelLocation;ADSRearEyeDistance=9.f;
        if(!bPresentationOnly)QuickCombatAnimation=LoadObject<UAnimSequence>(nullptr,*M24WeaponAssets::AnimationPath(TEXT("quick_melee")));
    }
    bUsingReplacement = ViewmodelMesh != nullptr;'''),
('UAnimSequence* AFPSGAMECharacter::LoadAKMAnimation(const TCHAR* AssetName)\n{','''UAnimSequence* AFPSGAMECharacter::LoadAKMAnimation(const TCHAR* AssetName)
{
    if(IsM24Weapon())
    {
        FString Clip(AssetName);Clip.RemoveFromStart(TEXT("A_AKM_"));
        if(Clip==TEXT("aim")||Clip==TEXT("walk")||Clip==TEXT("run"))Clip=TEXT("idle");
        else if(Clip==TEXT("aim_fire")||Clip==TEXT("fire_last"))Clip=TEXT("fire");
        else if(Clip.StartsWith(TEXT("equip")))Clip=TEXT("equip");
        return LoadObject<UAnimSequence>(nullptr,*M24WeaponAssets::AnimationPath(*Clip));
    }'''),
('(IsTubeShotgunWeapon()||SVDWeaponAssets::Matches(AKMViewmodel)||SVCHWeaponAssets::Matches(AKMViewmodel))?nullptr',
 '(IsM24Weapon()||IsTubeShotgunWeapon()||SVDWeaponAssets::Matches(AKMViewmodel)||SVCHWeaponAssets::Matches(AKMViewmodel))?nullptr'),
('InspectAnimation = IsTubeShotgunWeapon()','InspectAnimation = IsM24Weapon() || IsTubeShotgunWeapon()'),
('if (!bSharedDrum && bUsingM4Infima && !IsTubeShotgunWeapon()', 'if (!bSharedDrum && bUsingM4Infima && !IsM24Weapon() && !IsTubeShotgunWeapon()'),
('Sprint->Configure(IsPistolWeapon() ?', 'Sprint->Configure((IsPistolWeapon()||IsM24Weapon()) ?'),
('if (!bUseASH12 && !bUseM16 && !SVDWeaponAssets::Matches(AKMViewmodel)', 'if (!IsM24Weapon() && !bUseASH12 && !bUseM16 && !SVDWeaponAssets::Matches(AKMViewmodel)'),
('    UpdateM870PumpAudio();','    UpdateM870PumpAudio();\n    UpdateM24CycleAudio();'),
('        if (PKMLowpolyWeaponAssets::Matches(AKMViewmodel))\n        {\n            // Dedicated reference cuts', '''        if(IsM24Weapon())
        {
            MechanicalCueTimes={M24WeaponAssets::MagazineOut,M24WeaponAssets::MagazineInsert,M24WeaponAssets::MagazineSeat};
            MechanicalCueSounds={MagOutSound,MagInsertSound,MagSeatSound};
            if(bPendingEmptyReload)
            {MechanicalCueTimes.Append({M24WeaponAssets::ChargePull,M24WeaponAssets::ChargeRelease});MechanicalCueSounds.Append({ChargePullSound,ChargeReleaseSound});}
        }
        else if (PKMLowpolyWeaponAssets::Matches(AKMViewmodel))
        {
            // Dedicated reference cuts'''),
('    PlayWeaponAnimation(Animation, false, ShotAnimationRate);', '''    if(Animation&&IsM24Weapon())ShotAnimationRate=M24CyclePlayRate();
    PlayWeaponAnimation(Animation, false, ShotAnimationRate);
    if(IsM24Weapon()){M24CycleCueMask=0;M24PendingCasingWeapons.Remove(ActiveInventoryWeapon);NextAllowedShotTime=Now+FMath::Max(ShotInterval,double(ActionDuration));}'''),
('return (bUseDanWesson715 || IsTubeShotgunWeapon()) && ActiveActionAnimation', 'return (IsM24Weapon() || bUseDanWesson715 || IsTubeShotgunWeapon()) && ActiveActionAnimation'),
('(!bUseDanWesson715&&!IsTubeShotgunWeapon())', '(!IsM24Weapon()&&!bUseDanWesson715&&!IsTubeShotgunWeapon())'),
('const bool bPumpBusy=IsM870Weapon()&&IsRevolverFireActionPlaying();','const bool bPumpBusy=(IsM24Weapon()||IsM870Weapon())&&IsRevolverFireActionPlaying();'),
('if ((bUseDanWesson715 || bPKMWeapon || IsPitViperWeapon()', 'if ((IsM24Weapon() || bUseDanWesson715 || bPKMWeapon || IsPitViperWeapon()'),
('if(bHolographicOptic || IsShotgunWeapon() || IsPistolWeapon()', 'if(IsM24Weapon() || bHolographicOptic || IsShotgunWeapon() || IsPistolWeapon()'),
('WeaponStateDuration = bUsingM4Infima && !IsPistolWeapon()', 'WeaponStateDuration = bUsingM4Infima && !IsM24Weapon() && !IsPistolWeapon()'),
('USoundBase* AFPSGAMECharacter::LoadAKMSound(const TCHAR* AssetName)\n{', '''USoundBase* AFPSGAMECharacter::LoadAKMSound(const TCHAR* AssetName)
{
    if(IsM24Weapon())
    {
        FString Cue(AssetName);Cue.RemoveFromStart(TEXT("S_AKM_"));
        if(Cue==TEXT("Fire"))return LoadObject<USoundBase>(nullptr,*SVDWeaponAssets::FireSoundPath(1));
        if(Cue.StartsWith(TEXT("Mag"))||Cue.StartsWith(TEXT("Charge")))
            return LoadObject<USoundBase>(nullptr,*SVDWeaponAssets::MechanicalSoundPath(*Cue));
    }''')])
edit('FPSGAMECharacterProfile.cpp', [('I->Definition==TEXT("ue_svch")','(I->Definition==TEXT("ue_svch")||I->Definition==TEXT("ue_m24"))')])
edit('FPSGAMECharacterActionPriority.cpp',[('        PreserveInterruptedM870Pump();','        PreserveInterruptedM870Pump();\n        PreserveInterruptedM24Cycle();')])
edit('UI/ColdSteelStatusModel.h',[('    void MarkM870PumpInterrupted(const FString& WeaponId);','    void MarkM870PumpInterrupted(const FString& WeaponId);\n    void MarkM24CycleInterrupted(const FString& WeaponId);')])
edit('UI/ColdSteelAmmoRuntime.cpp',[('void UColdSteelStatusModel::MarkM870PumpInterrupted', '''void UColdSteelStatusModel::MarkM24CycleInterrupted(const FString& WeaponId)
{
    // The outgoing instance can differ from the newly published equipment.
    auto State=Snapshot();
    auto* Gun=State.Items.FindByPredicate([&](const auto& I){return I.InstanceId==WeaponId&&I.Definition==TEXT("ue_m24");});
    if(!Gun||WeaponReloadStages::NeedsCycle(*Gun)||!WeaponReloadStages::SetNeedsCycle(*Gun,1))return;
    if(!PersistState(State,false))Publish(State);
}

void UColdSteelStatusModel::MarkM870PumpInterrupted''')])
edit('Weapons/WeaponReloadStages.cpp',[
('#include "SVCHWeaponAssets.h"','#include "SVCHWeaponAssets.h"\n#include "M24WeaponAssets.h"'),
('    if (Definition == SVDWeaponAssets::Definition)','    if (Definition == M24WeaponAssets::Definition)\n        return {M24WeaponAssets::MagazineInsert,M24WeaponAssets::ChargeStart,Empty?M24WeaponAssets::ChargeRelease:M24WeaponAssets::MagazineInsert};\n    if (Definition == SVDWeaponAssets::Definition)')])
edit('Weapons/M4GunsmithVisual.cpp',[
('!HasThermalScope()&&!HasPSO1Scope()','!HasM24FactoryScope()&&!HasThermalScope()&&!HasPSO1Scope()'),
('||IsTraversing()||IsWeaponBusy())return 0.f;','||IsTraversing()||(IsM24Weapon()?IsWeaponBusyForAim():IsWeaponBusy()))return 0.f;')])
edit('Weapons/ScopeOpticalPresentation.cpp',[('    if(Bow && Bow->IsEquipped())return Bow->ScopeMagnification();','    if(IsM24Weapon())return 6.f;\n    if(Bow && Bow->IsEquipped())return Bow->ScopeMagnification();')])
edit('Weapons/M4MuzzleVisual.cpp',[('else if(IsPistolWeapon()||IsTubeShotgunWeapon())Forward=', 'else if(IsM24Weapon()||IsPistolWeapon()||IsTubeShotgunWeapon())Forward=')])
edit('Weapons/RifleHipFraming.cpp',[
('|| Definition == TEXT("ue_svch") ||','|| Definition == TEXT("ue_svch") || Definition == TEXT("ue_m24") ||'),
('else if (Definition == TEXT("ue_svch")) Forward = 10.f;','else if (Definition == TEXT("ue_svch") || Definition == TEXT("ue_m24")) Forward = 10.f;')])
edit('Weapons/FPSWeaponFXComponent.cpp',[
('#include "Saiga12KWeaponAssets.h"','#include "Saiga12KWeaponAssets.h"\n#include "M24WeaponAssets.h"'),
('const float Delay=M870WeaponAssets::PumpEject/FMath::Max(.01f,Rate)', '''const bool M24=bWorldGun?WorldGunDefinition==FName(M24WeaponAssets::Definition):
        WeaponMesh&&WeaponMesh->GetSkeletalMeshAsset()&&WeaponMesh->GetSkeletalMeshAsset()->GetPathName()==M24WeaponAssets::MeshPath;
    const float Delay=(M24?M24WeaponAssets::BoltEject:M870WeaponAssets::PumpEject)/FMath::Max(.01f,Rate)'''),
('const bool Pump=bWorldGun?WorldGunDefinition==FName(M870WeaponAssets::Definition):OwnerCharacter&&OwnerCharacter->IsM870Weapon();',
 'const bool Pump=bWorldGun?(WorldGunDefinition==FName(M870WeaponAssets::Definition)||WorldGunDefinition==FName(M24WeaponAssets::Definition)):OwnerCharacter&&(OwnerCharacter->IsM870Weapon()||OwnerCharacter->IsM24Weapon());'),
('AcceptedPumpRate:OwnerCharacter?OwnerCharacter->M870PumpPlayRate():1.f;', 'AcceptedPumpRate:OwnerCharacter?(OwnerCharacter->IsM24Weapon()?OwnerCharacter->M24CyclePlayRate():OwnerCharacter->M870PumpPlayRate()):1.f;')])
edit('Weapons/CasingPortCalibration.h',[('inline const FPort Ports[] =\n{', 'inline const FPort Ports[] =\n{\n    {TEXT("/Weapons/M24/Gameplay20261026/"), FVector::ZeroVector, TEXT("WPN_Eject"), 1.f},')])
edit('UI/ColdSteelIconResources.cpp',[
('#include "../Weapons/SVCHWeaponAssets.h"','#include "../Weapons/SVCHWeaponAssets.h"\n#include "../Weapons/M24WeaponAssets.h"'),
('        else if(D==TEXT("ue_svch"))','        else if(D==TEXT("ue_m24")){Add(M24WeaponAssets::MeshPath,true);Add(M24WeaponAssets::AnimationPath(TEXT("idle")),true);}\n        else if(D==TEXT("ue_svch"))')])
for file in ['UI/ColdSteelPickupStudio.cpp','UI/ColdSteelPickupWeapon.cpp']:
    edit(file,[('Item.Definition!=TEXT("ue_svch")','Item.Definition!=TEXT("ue_svch")&&Item.Definition!=TEXT("ue_m24")')])
edit('UI/ColdSteelWarehouseModel.cpp',[('TEXT("ue_svch"),','TEXT("ue_svch"), TEXT("ue_m24"),')])
edit('Characters/FPSBodyRifleHold.cpp',[
('if(!StockRoot||!Weapon.DoesSocketExist','if((!StockRoot&&!Weapon.DoesSocketExist(TEXT("WPN_StockContact")))||!Weapon.DoesSocketExist'),
('FVector Stock=Root.TransformPosition(*StockRoot);','FVector Stock=Weapon.DoesSocketExist(TEXT("WPN_StockContact"))?Weapon.GetSocketTransform(TEXT("WPN_StockContact"),RTS_Component).GetLocation():Root.TransformPosition(*StockRoot);')])
print('M24_RUNTIME_CONNECTED',len(changed),'files')
