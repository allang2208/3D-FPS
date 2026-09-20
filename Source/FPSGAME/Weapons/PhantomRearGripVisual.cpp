#include "../FPSGAMECharacter.h"
#include "M16Attachments.h"
#include "AKMSovietCalibration.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/StaticMesh.h"
#include "Rendering/SkeletalMeshRenderData.h"

namespace
{
bool IsFactoryRearGrip(const FName& Slot)
{
    const FString Name=Slot.ToString();
    return Name.Contains(TEXT("Grip_Default"))||Name.Contains(TEXT("FactoryRearGrip"))||Name==TEXT("M_M16_PistolGrip");
}
}

void AFPSGAMECharacter::SetGunsmithRearGrip(const FString& Variant)
{
    auto* Rifle=AKMViewmodel.Get();auto* Asset=Rifle?Rifle->GetSkeletalMeshAsset():nullptr;
    if(!Asset)return;
    const bool StableGrip=Variant==TEXT("stable_antislip_reargrip");
    const bool BalancedGrip=Variant==TEXT("balanced_reargrip");
    bool Enabled=bInventoryWeaponReady&&(Variant==TEXT("phantom_reargrip")||StableGrip||BalancedGrip);
    bool HasFactory=false;
    for(const auto& Material:Asset->GetMaterials())HasFactory|=IsFactoryRearGrip(Material.MaterialSlotName);
    if(Enabled&&HasFactory)
    {
        const TCHAR* Family=bUseQBZ191?TEXT("QBZ191"):AKMSoviet::Matches(Rifle)?TEXT("AKM"):TEXT("M4");
        const FString Path=bUseM16?M16Attachments::MeshPath(Variant):StableGrip
            ?FString::Printf(TEXT("/Game/Weapons/StableAntiSlipRearGrip/Selected91727/%s/SM_StableAntiSlipRearGrip.SM_StableAntiSlipRearGrip"),Family)
            :BalancedGrip
                ?(FCString::Strcmp(Family,TEXT("M4"))==0
                    ?FString(TEXT("/Game/Weapons/RearGripFinish20260913/M4/balanced/Seam20260914/SM_BalancedRearGrip.SM_BalancedRearGrip"))
                    :FString::Printf(TEXT("/Game/Weapons/RearGripFinish20260913/%s/balanced/SM_BalancedRearGrip.SM_BalancedRearGrip"),Family))
                :FString::Printf(TEXT("/Game/Weapons/RearGripFinish20260913/%s/phantom/SM_PhantomRearGrip.SM_PhantomRearGrip"),Family);
        if(auto* GripMesh=LoadObject<UStaticMesh>(nullptr,*Path))
        {
            if(!RearGripAttachment)
            {
                RearGripAttachment=NewObject<UStaticMeshComponent>(this,TEXT("PhantomRearGrip"));
                RearGripAttachment->SetCollisionEnabled(ECollisionEnabled::NoCollision);
                RearGripAttachment->SetCastShadow(false);RearGripAttachment->bReceivesDecals=false;
                RearGripAttachment->SetupAttachment(Rifle,TEXT("WPN_root"));RearGripAttachment->RegisterComponent();
            }
            RearGripAttachment->SetStaticMesh(GripMesh);
            // Each fitted FBX is authored in its rifle's root frame. Bone scale is 100x.
            RearGripAttachment->SetRelativeTransform(FTransform(FQuat::Identity,FVector::ZeroVector,FVector(.01f)));
        }
        else Enabled=false;
    }
    else Enabled=false;
    if(RearGripAttachment)RearGripAttachment->SetVisibility(Enabled);
    if(const auto* Render=Asset->GetResourceForRendering())
        for(int32 L=0;L<Render->LODRenderData.Num();++L)
            for(int32 S=0;S<Render->LODRenderData[L].RenderSections.Num();++S)
            {
                const int32 M=Render->LODRenderData[L].RenderSections[S].MaterialIndex;
                if(Asset->GetMaterials().IsValidIndex(M)&&IsFactoryRearGrip(Asset->GetMaterials()[M].MaterialSlotName))
                    Rifle->ShowMaterialSection(M,S,!Enabled,L);
            }
}
