#include "Saiga12KAttachments.h"
#include "../FPSGAMECharacter.h"
#include "WeaponGripProfile.h"
#include "SVDWeaponAssets.h"
#include "M24WeaponAssets.h"
#include "M24Attachments.h"
#include "M249Attachments.h"
#include "SniperSkeletonStock.h"
#include "SVCHWeaponAssets.h"
#include "SVCHForegripAssets.h"
#include "RSH12WeaponAssets.h"
#include "RSH12ForegripAssets.h"
#include "Super90ForegripAssets.h"
#include "M870FurnitureAssets.h"
#include "LMG201WeaponAssets.h"
#include "G18WeaponAssets.h"
#include "Animation/AnimSequence.h"
#include "Components/StaticMeshComponent.h"

bool AFPSGAMECharacter::InitializeWeaponGripFamily(FName Family,TMap<TObjectPtr<UAnimSequence>,TObjectPtr<UAnimSequence>>& Map)
{
    const bool bSVD=SVDWeaponAssets::Matches(AKMViewmodel);
    if(bSVD&&Family==TEXT("drum"))return false;
    // 裸角色（未装备武器）时定义为空：拼出的包路径含双斜杠会触发 UObjectGlobals Fatal（闪退）。
    if(!bSVD&&ActiveInventoryWeaponDefinition.IsEmpty())return false;
    const FString Path=Family==TEXT("stability")&&LMGStabilityGrip::Supports(ActiveInventoryWeaponDefinition)?LMGStabilityGrip::ProfilePath(ActiveInventoryWeaponDefinition)
        :bSVD?TEXT("/Game/Weapons/SVDDragunov20260922/GripProfiles20261001/DA_SVD_Grip_")+Family.ToString()
        :M249WeaponAssets::Matches(AKMViewmodel)?M249Attachments::ProfilePath(Family)
        :IsM24Weapon()&&Family==TEXT("base")?FString(M24WeaponAssets::SupportGripProfile)
        :IsM24Weapon()&&Family==TEXT("mag10")?FString(M24WeaponAssets::ExtendedMagazineProfile)
        :IsM24Weapon()&&Family.ToString().StartsWith(TEXT("skeleton_"))?SniperSkeletonStock::M24ProfilePath(Family)
        :SVCHWeaponAssets::Matches(AKMViewmodel)?SVCHForegripAssets::ProfilePath(Family)
        :IsRSH12Weapon()&&Family==TEXT("base")?FString(RSH12WeaponAssets::ProfilePath)
        :IsRSH12Weapon()&&Family!=TEXT("drum")?RSH12ForegripAssets::ProfilePath(Family)
        :IsG18Weapon()&&Family==TEXT("drum")?FString(G18WeaponAssets::Drum50ReloadProfile)
        :IsSuper90Weapon()&&Family!=TEXT("base")&&Family!=TEXT("drum")?Super90ForegripAssets::ProfilePath(Family)
        :IsSaiga12KWeapon()?Saiga12KAttachments::ProfilePath(Family)
        :IsM870Weapon()&&Family!=TEXT("base")&&Family!=TEXT("drum")?M870FurnitureAssets::ProfilePath(Family)
        :TEXT("/Game/Weapons/AnimationProfiles20261001/")+ActiveInventoryWeaponDefinition+TEXT("/DA_")+Family.ToString();
    UWeaponGripProfile* Profile=LoadObject<UWeaponGripProfile>(nullptr,*Path,nullptr,LOAD_NoWarn);
    if(!Profile||Profile->Family!=Family||Profile->Clips.IsEmpty())return false;
    WeaponGripProfiles.Add(Family,Profile);
    for(const FWeaponGripClip& Layer:Profile->Clips)if(Layer.Base)Map.Add(Layer.Base,Layer.Playback());
    return true;
}

UWeaponGripProfile* AFPSGAMECharacter::WeaponGripProfileFor(EM4SprintGrip Grip) const
{
    if(!M249WeaponAssets::Matches(AKMViewmodel)&&LMGStabilityGrip::Supports(ActiveInventoryWeaponDefinition)
        &&HasVerticalForegrip()&&VerticalForegrip->ComponentHasTag(TEXT("LMGStabilityGrip")))
    {
        const auto* Found=WeaponGripProfiles.Find(TEXT("stability"));
        return Found?Found->Get():nullptr;
    }
    if(M249WeaponAssets::Matches(AKMViewmodel))
    {
        const bool Stable=HasVerticalForegrip()&&VerticalForegrip->ComponentHasTag(TEXT("LMGStabilityGrip"));
        const bool Bare=Grip==EM4SprintGrip::Base||Grip==EM4SprintGrip::Drum;
        if(Stable||Bare)
        {
            const auto* Found=WeaponGripProfiles.Find(Stable?TEXT("base"):TEXT("handguard"));
            return Found?Found->Get():nullptr;
        }
    }
    if(IsM24Weapon())
    {
        // Both magazines share the anatomical support grasp. The extended
        // profile adds only its existing reload contact on separate arm bones.
        const bool Independent=SniperSkeletonStock::UsesM24DirectStock(StockAttachment);
        const bool Extended=MagazineAttachmentId==M24Attachments::ExtendedMagazine;
        const FName Family=Independent?SniperSkeletonStock::M24GripFamily(RearGripAttachment,Extended):(Extended?TEXT("mag10"):TEXT("base"));
        const auto* Profile=WeaponGripProfiles.Find(Family);
        return Profile?Profile->Get():nullptr;
    }
    // G18 uses a sparse reload-only support grasp. Keep the pistol's existing
    // mechanical clock and magazine trajectory, without rifle drum state.
    if(IsG18Weapon()&&MagazineAttachmentId==G18WeaponAssets::Drum50Id)
        if(const auto* Drum=WeaponGripProfiles.Find(TEXT("drum")))return Drum->Get();
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
