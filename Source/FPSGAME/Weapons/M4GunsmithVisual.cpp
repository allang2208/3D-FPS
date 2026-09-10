#include "../FPSGAMECharacter.h"
#include "Components/StaticMeshComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Engine/StaticMesh.h"
#include "Engine/SkeletalMesh.h"
#include "Camera/CameraComponent.h"
#include "GameFramework/PlayerController.h"

void AFPSGAMECharacter::SetGunsmithOptic(bool bHolographic)
{
    bHolographic = bHolographic && bUsingM4Infima && bInventoryWeaponReady;
    if(bHolographic && !HolographicOptic)
    {
        auto* OpticMesh=LoadObject<UStaticMesh>(nullptr,TEXT("/Game/Weapons/M4Holographic/SM_M4_Holographic.SM_M4_Holographic"));
        if(!OpticMesh){UE_LOG(LogTemp,Error,TEXT("M4_HOLO: missing optic mesh"));return;}
        HolographicOptic=NewObject<UStaticMeshComponent>(this,TEXT("M4HolographicOptic"));
        HolographicOptic->SetStaticMesh(OpticMesh);
        HolographicOptic->SetCollisionEnabled(ECollisionEnabled::NoCollision);
        HolographicOptic->SetCastShadow(false);HolographicOptic->bReceivesDecals=false;
        HolographicOptic->SetupAttachment(AKMViewmodel,TEXT("WPN_root"));
        HolographicOptic->RegisterComponent();
        const auto& Ref=AKMViewmodel->GetSkeletalMeshAsset()->GetRefSkeleton();
        auto Bone=[&](const TCHAR* Name){FTransform T=FTransform::Identity;for(int32 I=Ref.FindBoneIndex(Name);I!=INDEX_NONE;I=Ref.GetParentIndex(I))T=T*Ref.GetRefBonePose()[I];return T;};
        const auto Root=Bone(TEXT("WPN_root"));const auto Rear=Bone(TEXT("WPN_RearSight"));const auto Front=Bone(TEXT("WPN_FrontSight"));
        const FVector Axis=(Front.GetLocation()-Rear.GetLocation()).GetSafeNormal();
        // The source weapon is canted in the bind pose. Its authored sight frame,
        // not component/world Z, defines the rail normal for a rigid attachment.
        const FVector RailUp=Rear.GetRotation().RotateVector(FVector::UpVector);
        const FQuat Rotation=FRotationMatrix::MakeFromXZ(Axis,RailUp).ToQuat();
        const FTransform Mount(Rotation,Rear.GetLocation()+Axis*8.f-RailUp*3.2f,FVector::OneVector);
        HolographicMount=Mount.GetRelativeTransform(Root);
        HolographicOptic->SetRelativeTransform(HolographicMount);
    }
    if(bHolographicOptic!=bHolographic)bSightCalibrated=false;
    bHolographicOptic=bHolographic;
    if(HolographicOptic)HolographicOptic->SetVisibility(bHolographic);
    for(auto Head:FoldingSightHeads)Head->SetVisibility(bUsingM4Infima&&bInventoryWeaponReady);
}
FVector AFPSGAMECharacter::HolographicAimPoint() const
{
    return HolographicOptic?HolographicOptic->GetComponentTransform().TransformPosition(FVector(-.653782f,0,5.175324f)):FVector::ZeroVector;
}
bool AFPSGAMECharacter::ValidateGunsmithSight(float& PixelError) const
{
    PixelError=MAX_flt;if(!HolographicOptic||!HolographicOptic->IsVisible())return false;
    const auto* PC=Cast<APlayerController>(GetController());if(!PC)return false;
    FVector2D Point;int32 W,H;PC->GetViewportSize(W,H);
    if(!PC->ProjectWorldLocationToScreen(HolographicAimPoint(),Point))return false;
    PixelError=FVector2D::Distance(Point,FVector2D(W*.5,H*.5));
    return PixelError<2.f;
}
bool AFPSGAMECharacter::ValidateHolographicShot() const
{
    return bHolographicOptic&&WeaponADSFactor>.98f&&FVector::DotProduct(ComputeShotDirection(),(HolographicAimPoint()-FirstPersonCamera->GetComponentLocation()).GetSafeNormal())>.99999f;
}
bool AFPSGAMECharacter::MeasureHolographicOrientation(float& ScreenRollDegrees,float& RailErrorDegrees) const
{
    ScreenRollDegrees=RailErrorDegrees=180.f;
    if(!bHolographicOptic||!HolographicOptic)return false;
    const FVector OpticUp=HolographicOptic->GetUpVector();
    const FVector RailUp=AKMViewmodel->GetSocketTransform(TEXT("WPN_RearSight")).GetRotation().RotateVector(FVector::UpVector);
    RailErrorDegrees=FMath::RadiansToDegrees(FMath::Acos(FMath::Clamp(FVector::DotProduct(OpticUp,RailUp),-1.0,1.0)));
    const auto* PC=Cast<APlayerController>(GetController());if(!PC)return false;
    FVector2D Center,Top;
    if(!PC->ProjectWorldLocationToScreen(HolographicAimPoint(),Center)||!PC->ProjectWorldLocationToScreen(HolographicAimPoint()+OpticUp*2.f,Top))return false;
    const FVector2D Delta=Top-Center;
    ScreenRollDegrees=FMath::RadiansToDegrees(FMath::Atan2(Delta.X,-Delta.Y));
    return true;
}
