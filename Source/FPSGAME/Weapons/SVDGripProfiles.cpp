#include "../FPSGAMECharacter.h"
#include "WeaponGripProfile.h"
#include "SVDWeaponAssets.h"
#include "RSH12WeaponAssets.h"
#include "LMG201WeaponAssets.h"
#include "Animation/AnimSequence.h"

bool AFPSGAMECharacter::InitializeWeaponGripFamily(FName Family,TMap<TObjectPtr<UAnimSequence>,TObjectPtr<UAnimSequence>>& Map)
{
    const bool bSVD=SVDWeaponAssets::Matches(AKMViewmodel);
    if(bSVD&&Family==TEXT("drum"))return false;
    // 裸角色（未装备武器）时定义为空：拼出的包路径含双斜杠会触发 UObjectGlobals Fatal（闪退）。
    if(!bSVD&&ActiveInventoryWeaponDefinition.IsEmpty())return false;
    const FString Path=bSVD?TEXT("/Game/Weapons/SVDDragunov20260922/GripProfiles20261001/DA_SVD_Grip_")+Family.ToString()
        :IsRSH12Weapon()&&Family==TEXT("base")?FString(RSH12WeaponAssets::ProfilePath)
        :TEXT("/Game/Weapons/AnimationProfiles20261001/")+ActiveInventoryWeaponDefinition+TEXT("/DA_")+Family.ToString();
    UWeaponGripProfile* Profile=LoadObject<UWeaponGripProfile>(nullptr,*Path,nullptr,LOAD_NoWarn);
    if(!Profile||Profile->Family!=Family||Profile->Clips.IsEmpty())return false;
    WeaponGripProfiles.Add(Family,Profile);
    for(const FWeaponGripClip& Layer:Profile->Clips)if(Layer.Base)Map.Add(Layer.Base,Layer.Playback());
    return true;
}

UWeaponGripProfile* AFPSGAMECharacter::WeaponGripProfileFor(EM4SprintGrip Grip) const
{
    const FName Family=Grip==EM4SprintGrip::Angled?TEXT("angled"):Grip==EM4SprintGrip::Vertical?TEXT("vertical")
        :Grip==EM4SprintGrip::Canted?TEXT("canted"):Grip==EM4SprintGrip::Prism?TEXT("prism")
        :Grip==EM4SprintGrip::Drum?TEXT("drum"):TEXT("base");
    const auto* Found=WeaponGripProfiles.Find(Family);
    // The 201 drum changes its feed, while an unmodified handguard keeps the
    // same underside support grasp. Attachment families use their own layers.
    if(!Found&&Grip==EM4SprintGrip::Drum&&LMG201WeaponAssets::Matches(AKMViewmodel))
        Found=WeaponGripProfiles.Find(TEXT("base"));
    return Found?Found->Get():nullptr;
}
