#include "../FPSGAMECharacter.h"
#include "Saiga12KAttachments.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/StaticMesh.h"
void AFPSGAMECharacter::SetSaiga12KOptic(const FString& Variant)
{
    auto Remove=[](TObjectPtr<UStaticMeshComponent>& Part)
    { if(Part){Part->DestroyComponent();Part=nullptr;} };
    if(!bInventoryWeaponReady || !Saiga12KAttachments::SupportsOptic(Variant))
    {
        Remove(LPVORing);Remove(HolographicOptic);Remove(AKMOpticBridge);
        if(bHolographicOptic)bSightCalibrated=false;
        bHolographicOptic=false;OpticVariant.Reset();return;
    }
    if(!AKMViewmodel || !AKMViewmodel->GetSkeletalMeshAsset())return;
    const bool IsLPVO=Variant==TEXT("lpvo_1_6x");
    const bool IsThermal=Variant==TEXT("thermal_scope");
    const bool NeedsRing=IsLPVO||IsThermal;
    if(bHolographicOptic && OpticVariant==Variant && HolographicOptic && AKMOpticBridge && (!NeedsRing||LPVORing))
    {
        HolographicOptic->SetVisibility(true);AKMOpticBridge->SetVisibility(true);
        if(LPVORing)LPVORing->SetVisibility(NeedsRing);
        return;
    }
    auto* Body=LoadObject<UStaticMesh>(nullptr,*Saiga12KAttachments::MeshPath(Variant));
    auto* Seat=LoadObject<UStaticMesh>(nullptr,*Saiga12KAttachments::MeshPath(TEXT("OpticSeat_")+Variant));
    auto* Ring=NeedsRing?LoadObject<UStaticMesh>(nullptr,*Saiga12KAttachments::MeshPath(IsThermal?TEXT("thermal_selector"):TEXT("lpvo_ring"))):nullptr;
    if(!Body || !Seat || (NeedsRing&&!Ring))
    { UE_LOG(LogTemp,Error,TEXT("Saiga12K missing fitted optic assembly %s"),*Variant);return; }
    auto Configure=[&](TObjectPtr<UStaticMeshComponent>& Part,UStaticMesh* PartMesh,USceneComponent* Parent,FName Socket,const FTransform& Local)
    {
        if(!Part)Part=NewObject<UStaticMeshComponent>(this);
        Part->EmptyOverrideMaterials();Part->SetStaticMesh(PartMesh);
        Part->SetCollisionEnabled(ECollisionEnabled::NoCollision);Part->SetCastShadow(false);Part->bReceivesDecals=false;
        Part->SetOnlyOwnerSee(AKMViewmodel->bOnlyOwnerSee);Part->SetFirstPersonPrimitiveType(AKMViewmodel->FirstPersonPrimitiveType);
        if(!Part->IsRegistered()){Part->SetupAttachment(Parent,Socket);Part->RegisterComponent();}
        else Part->AttachToComponent(Parent,FAttachmentTransformRules::KeepRelativeTransform,Socket);
        Part->SetRelativeTransform(Local);Part->SetVisibility(true);
    };
    HolographicMount=Saiga12KAttachments::OpticMount(Variant);
    Configure(AKMOpticBridge,Seat,AKMViewmodel,TEXT("WPN_root"),Saiga12KAttachments::RailMount());
    Configure(HolographicOptic,Body,AKMViewmodel,TEXT("WPN_root"),HolographicMount);
    if(OpticVariant!=Variant)
    {
        LPVOMagnification=DisplayedLPVOMagnification=1.f;
        if(IsThermal)ThermalZoomIndex=0;
    }
    if(NeedsRing)
        Configure(LPVORing,Ring,HolographicOptic,IsThermal?TEXT("ZoomPivot"):TEXT("ZoomRing"),
            IsThermal?FTransform::Identity:FTransform(FRotator(0,0,(DisplayedLPVOMagnification-1.f)*24.f)));
    else Remove(LPVORing);
    // Fixed factory sights remain below the raised optical axis.
    OpticVariant=Variant;bHolographicOptic=true;bSightCalibrated=false;
}
