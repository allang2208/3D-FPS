#include "../FPSGAMECharacter.h"
#include "M870OpticAssets.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/StaticMesh.h"

FTransform M870OpticAssets::RailMount(const USkeletalMeshComponent* Host)
{
    const auto& Ref=Host->GetSkeletalMeshAsset()->GetRefSkeleton();
    FTransform Root=FTransform::Identity;
    for(int32 I=Ref.FindBoneIndex(TEXT("WPN_root"));I!=INDEX_NONE;I=Ref.GetParentIndex(I))
        Root=Root*Ref.GetRefBonePose()[I];
    // Native receiver rail, measured after M870 source-to-author conversion.
    // The reference frame includes the imported bone's scale and orientation.
    const FTransform Seat(FRotationMatrix::MakeFromXZ(FVector(0,-1,0),FVector::UpVector).ToQuat(),
        FVector(0,1.88748126f,-70.752369f));
    return Seat.GetRelativeTransform(Root);
}

FTransform M870OpticAssets::OpticMount(const USkeletalMeshComponent* Host,const FString& Variant)
{
    // Same centimetre offsets as M870CommonOptics20261016/authoring.json.
    // Each saddle fits the existing optic foot; keep the optical body full size.
    FVector Offset(0,0,.15f);
    if(Variant==TEXT("holographic"))Offset.X=1.386495f;
    else if(Variant==TEXT("eoth_holographic"))Offset=FVector(-.315245f,0,.55f);
    else if(Variant==TEXT("lpvo_1_6x"))Offset.X=1.4f;
    else if(Variant==TEXT("thermal_scope"))Offset.Z=.35f;
    return FTransform(Offset)*RailMount(Host);
}

void AFPSGAMECharacter::SetM870Optic(const FString& Variant)
{
    auto Remove=[](TObjectPtr<UStaticMeshComponent>& Part)
    { if(Part){Part->DestroyComponent();Part=nullptr;} };
    if(!bInventoryWeaponReady || !M870OpticAssets::Supports(Variant))
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
    auto* Body=LoadObject<UStaticMesh>(nullptr,*M870OpticAssets::MeshPath(Variant));
    auto* Seat=LoadObject<UStaticMesh>(nullptr,*M870OpticAssets::SeatPath(Variant));
    auto* Ring=NeedsRing?LoadObject<UStaticMesh>(nullptr,*M870OpticAssets::MeshPath(IsThermal?TEXT("thermal_selector"):TEXT("lpvo_ring"))):nullptr;
    if(!Body || !Seat || (NeedsRing&&!Ring))
    { UE_LOG(LogTemp,Error,TEXT("M870 missing fitted optic assembly %s"),*Variant);return; }
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
    HolographicMount=M870OpticAssets::OpticMount(AKMViewmodel,Variant);
    Configure(AKMOpticBridge,Seat,AKMViewmodel,TEXT("WPN_root"),M870OpticAssets::RailMount(AKMViewmodel));
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
    // The factory ring remains behind the adapter, below the optical axis.
    OpticVariant=Variant;bHolographicOptic=true;bSightCalibrated=false;
}
