#include "../FPSGAMECharacter.h"
#include "M24Attachments.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/StaticMesh.h"
#include "Engine/StaticMeshSocket.h"

void AFPSGAMECharacter::SetM24Optic(const FString& Variant)
{
    const FString Key=M24Attachments::OpticPart(Variant);
    auto Remove=[](TObjectPtr<UStaticMeshComponent>& Part)
    {if(Part){Part->DestroyComponent();Part=nullptr;}};
    if(!bInventoryWeaponReady||!M24Attachments::IsOptic(Key))
    {
        Remove(LPVORing);Remove(HolographicOptic);Remove(AKMOpticBridge);
        if(bHolographicOptic)bSightCalibrated=false;
        bHolographicOptic=false;OpticVariant.Reset();return;
    }
    if(!AKMViewmodel||!AKMViewmodel->GetSkeletalMeshAsset())return;
    const FString Moving=M24Attachments::MovingOpticPart(Key);
    auto* Body=LoadObject<UStaticMesh>(nullptr,*M24Attachments::MeshPath(Key));
    auto* Ring=Moving.IsEmpty()?nullptr:LoadObject<UStaticMesh>(nullptr,*M24Attachments::MeshPath(Moving));
    // Resolve the complete assembly before replacing the currently mounted one.
    if(!Body||(!Moving.IsEmpty()&&!Ring))
    {UE_LOG(LogTemp,Error,TEXT("M24 missing fitted optic assembly %s"),*Key);return;}
    const bool Changed=OpticVariant!=Key||!bHolographicOptic||!HolographicOptic||HolographicOptic->GetStaticMesh()!=Body;
    HolographicOptic=M24Attachments::Configure(this,AKMViewmodel,HolographicOptic,Key,true);
    HolographicMount=HolographicOptic->GetRelativeTransform();
    Remove(AKMOpticBridge); // The M24 has its own continuous receiver rail.
    if(Changed)
    {
        LPVOMagnification=DisplayedLPVOMagnification=Key==M24Attachments::Scope?6.f:1.f;
        ThermalZoomIndex=0;bSightCalibrated=false;
    }
    if(Ring)
    {
        const bool Thermal=Key==TEXT("thermal_scope");
        const FName Pivot=Thermal?TEXT("ZoomPivot"):TEXT("ZoomRing");
        if(!LPVORing)
        {
            LPVORing=NewObject<UStaticMeshComponent>(this);
            LPVORing->SetupAttachment(HolographicOptic,Pivot);LPVORing->RegisterComponent();
        }
        else LPVORing->AttachToComponent(HolographicOptic,FAttachmentTransformRules::KeepRelativeTransform,Pivot);
        if(LPVORing->GetStaticMesh()!=Ring)LPVORing->EmptyOverrideMaterials();
        LPVORing->SetStaticMesh(Ring);LPVORing->SetCollisionEnabled(ECollisionEnabled::NoCollision);
        LPVORing->SetCastShadow(false);LPVORing->bReceivesDecals=false;
        LPVORing->SetOnlyOwnerSee(AKMViewmodel->bOnlyOwnerSee);
        LPVORing->SetFirstPersonPrimitiveType(AKMViewmodel->FirstPersonPrimitiveType);
        LPVORing->SetRelativeTransform(Thermal?FTransform(FRotator(-70.f*ThermalZoomIndex,0,0)):
            FTransform(FRotator(0,0,(DisplayedLPVOMagnification-1.f)*24.f)));
        LPVORing->SetVisibility(AKMViewmodel->IsVisible());LPVORing->SetHiddenInGame(AKMViewmodel->bHiddenInGame);
    }
    else Remove(LPVORing);
    bHolographicOptic=true;OpticVariant=Key;
}

FVector AFPSGAMECharacter::M24UpperSightADSOffset() const
{
    if(!HasM24FactoryScope()||!HolographicOptic)return FVector::ZeroVector;
    const UStaticMesh* OpticMesh=HolographicOptic->GetStaticMesh();if(!OpticMesh)return FVector::ZeroVector;
    const auto* Rear=OpticMesh->FindSocket(TEXT("SightRear"));
    const auto* Front=OpticMesh->FindSocket(TEXT("SightFront"));
    const auto* Up=OpticMesh->FindSocket(TEXT("SightUp"));
    const auto* Upper=OpticMesh->FindSocket(TEXT("TopSightRear"));
    if(!Rear||!Front||!Up||!Upper)return FVector::ZeroVector;
    // Both sights share an axis. Express the measured lens separation in the
    // calibrated camera frame; retain the accepted receiver/arm depth.
    const FQuat Frame=FRotationMatrix::MakeFromXZ(Front->RelativeLocation-Rear->RelativeLocation,
        Up->RelativeLocation-Rear->RelativeLocation).ToQuat().Inverse();
    // Component scale includes the skeletal root's imported unit conversion;
    // the mount's relative scale alone omits it.
    FVector Offset=Frame.RotateVector((Upper->RelativeLocation-Rear->RelativeLocation)
        *HolographicOptic->GetComponentScale());
    Offset.X=0.f;
    return -Offset*GetM24UpperSightAlpha();
}

UStaticMeshComponent* AFPSGAMECharacter::GetM24FactoryOptic() const
{
    return HasM24FactoryScope()?HolographicOptic.Get():nullptr;
}

float AFPSGAMECharacter::GetM24LensMagnification() const
{
    // The physical lens and mouse gain share this continuous value. Returning
    // to the upper red dot or leaving ADS smoothly returns it to unity.
    return HasM24FactoryScope()
        ?FMath::Lerp(1.f,GetDisplayedOpticMagnification(),GetScopePresentationAlpha()):1.f;
}

float AFPSGAMECharacter::GetM24UpperSightReticleAlpha() const
{
    if(!HasM24FactoryScope()||!bInventoryWeaponReady||IsTraversing()||IsWeaponBusyForAim())return 0.f;
    return FMath::SmoothStep(.65f,.98f,CameraADSFactor)*FMath::SmoothStep(.82f,.99f,GetM24UpperSightAlpha());
}
