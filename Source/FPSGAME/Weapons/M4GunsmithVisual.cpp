#include "../FPSGAMECharacter.h"
#include "AKMAttachmentVisual.h"
#include "QBZ191Attachments.h"
#include "Components/StaticMeshComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Engine/StaticMesh.h"
#include "Engine/SkeletalMesh.h"
#include "Camera/CameraComponent.h"
#include "GameFramework/PlayerController.h"

void AFPSGAMECharacter::SetGunsmithOptic(bool bHolographic)
{
    SetGunsmithOpticVariant(bHolographic?TEXT("holographic"):TEXT("false"));
}
void AFPSGAMECharacter::SetGunsmithOpticVariant(const FString& Variant)
{
    const bool LPVO=Variant==TEXT("lpvo_1_6x");
    const bool Panoramic=Variant==TEXT("panoramic_red_dot");
    const bool Scope2X=Variant==TEXT("prism_scope_2x");
    bool bHolographic=Variant==TEXT("holographic")||Panoramic||Scope2X||LPVO;
    if(LPVORing&&!LPVO)LPVORing->SetVisibility(false);
    if(AKMSoviet::Matches(AKMViewmodel)){
        bHolographic=bHolographic&&bInventoryWeaponReady;
        const bool Modern=bHolographic&&(Panoramic||Scope2X||LPVO);
        if(Modern){
            const TCHAR* Path=LPVO?TEXT("/Game/Weapons/AKMIntegration/SovietFab/OpticSteel/SM_LPVO1to6X"):Scope2X?TEXT("/Game/Weapons/AKMIntegration/SovietFab/OpticSteel/SM_PrismScope2X"):TEXT("/Game/Weapons/AKMIntegration/SovietFab/OpticSteel/SM_PanoramicRedDot");
            auto* AKMOpticMesh=LoadObject<UStaticMesh>(nullptr,Path);
            auto* Bridge=LoadObject<UStaticMesh>(nullptr,*(TEXT("/Game/Weapons/AKMIntegration/SovietFab/Optics/SM_AKM_Mount_")+Variant));
            if(!AKMOpticMesh||!Bridge){UE_LOG(LogTemp,Error,TEXT("AKM_OPTIC missing model or bridge for %s"),*Variant);return;}
            auto MakePart=[&](UStaticMeshComponent* Part){if(!Part){Part=NewObject<UStaticMeshComponent>(this);Part->SetupAttachment(AKMViewmodel,TEXT("WPN_root"));Part->SetCollisionEnabled(ECollisionEnabled::NoCollision);Part->SetCastShadow(false);Part->bReceivesDecals=false;Part->RegisterComponent();}return Part;};
            HolographicOptic=MakePart(HolographicOptic);HolographicOptic->SetStaticMesh(AKMOpticMesh);
            HolographicMount=FTransform(FQuat(FVector::UpVector,PI*.5f),FVector(.0008f,LPVO?.16f:Scope2X?.105f:.06f,.113f),FVector(.01f));
            HolographicOptic->SetRelativeTransform(HolographicMount);
            AKMOpticBridge=MakePart(AKMOpticBridge);AKMOpticBridge->SetStaticMesh(Bridge);AKMOpticBridge->SetRelativeTransform(FTransform(FQuat::Identity,FVector::ZeroVector,FVector(.01f)));
        }else{
            HolographicOptic=AKMAttachment::Configure(this,AKMViewmodel,HolographicOptic,TEXT("optic"),bHolographic);
            HolographicMount=FTransform(FQuat::Identity,FVector::ZeroVector,FVector(.01f));
        }
        if(AKMOpticBridge)AKMOpticBridge->SetVisibility(Modern);
        if(bHolographicOptic!=bHolographic||OpticVariant!=Variant)bSightCalibrated=false;
        if(OpticVariant!=Variant)LPVOMagnification=1.f;
        bHolographicOptic=bHolographic;OpticVariant=bHolographic?Variant:FString();
        if(LPVO&&bHolographic&&!LPVORing){
            auto* RingMesh=LoadObject<UStaticMesh>(nullptr,TEXT("/Game/Weapons/AKMIntegration/SovietFab/OpticSteel/SM_LPVORing"));
            if(RingMesh){LPVORing=NewObject<UStaticMeshComponent>(this);LPVORing->SetStaticMesh(RingMesh);LPVORing->SetCollisionEnabled(ECollisionEnabled::NoCollision);LPVORing->SetCastShadow(false);LPVORing->SetupAttachment(HolographicOptic);LPVORing->RegisterComponent();LPVORing->SetRelativeLocation(FVector(-7.1f,0,4.f));}
        }
        if(LPVORing){LPVORing->SetVisibility(LPVO&&bHolographic);LPVORing->SetRelativeRotation(FRotator(0,0,(LPVOMagnification-1.f)*24.f));}
        if(HolographicOptic)HolographicOptic->SetVisibility(bHolographic);
        return;
    }
    bHolographic = bHolographic && bUsingM4Infima && bInventoryWeaponReady;
    if(bHolographic && (!HolographicOptic || OpticVariant!=Variant))
    {
        const TCHAR* MeshPath=LPVO?TEXT("/Game/Weapons/AttachmentFinish20260913/M4/Meshes/SM_LPVO1to6X"):Scope2X?TEXT("/Game/Weapons/AttachmentFinish20260913/M4/Meshes/SM_PrismScope2X"):(Panoramic?TEXT("/Game/Weapons/AttachmentFinish20260913/M4/Meshes/SM_PanoramicRedDot"):TEXT("/Game/Weapons/AttachmentFinish20260913/M4/Meshes/SM_M4_Holographic"));
        auto* OpticMesh=LoadObject<UStaticMesh>(nullptr,bUseQBZ191?*QBZ191Attachments::MeshPath(Variant):MeshPath);
        if(!OpticMesh){UE_LOG(LogTemp,Error,TEXT("M4_HOLO: missing optic mesh"));return;}
        if(!HolographicOptic){
        HolographicOptic=NewObject<UStaticMeshComponent>(this,TEXT("M4HolographicOptic"));
        HolographicOptic->SetCollisionEnabled(ECollisionEnabled::NoCollision);
        HolographicOptic->SetCastShadow(false);HolographicOptic->bReceivesDecals=false;
        HolographicOptic->SetupAttachment(AKMViewmodel,TEXT("WPN_root"));
        HolographicOptic->RegisterComponent();
        }
        HolographicOptic->SetStaticMesh(OpticMesh);
        const auto& Ref=AKMViewmodel->GetSkeletalMeshAsset()->GetRefSkeleton();
        auto Bone=[&](const TCHAR* Name){FTransform T=FTransform::Identity;for(int32 I=Ref.FindBoneIndex(Name);I!=INDEX_NONE;I=Ref.GetParentIndex(I))T=T*Ref.GetRefBonePose()[I];return T;};
        const auto Root=Bone(TEXT("WPN_root"));const auto Rear=Bone(TEXT("WPN_RearSight"));const auto Front=Bone(TEXT("WPN_FrontSight"));
        const FVector Axis=(Front.GetLocation()-Rear.GetLocation()).GetSafeNormal();
        // The source weapon is canted in the bind pose. Its authored sight frame,
        // not component/world Z, defines the rail normal for a rigid attachment.
        const FVector RailUp=Rear.GetRotation().RotateVector(FVector::UpVector);
        const FQuat Rotation=FRotationMatrix::MakeFromXZ(Axis,RailUp).ToQuat();
        const FTransform Mount(Rotation,Rear.GetLocation()+Axis*8.f-RailUp*3.2f,FVector::OneVector);
        HolographicMount=bUseQBZ191?QBZ191Attachments::OpticMount(Variant):Mount.GetRelativeTransform(Root);
        HolographicOptic->SetRelativeTransform(HolographicMount);
    }
    if(bHolographicOptic!=bHolographic || OpticVariant!=Variant)bSightCalibrated=false;
    bHolographicOptic=bHolographic;
    if(OpticVariant!=Variant)LPVOMagnification=1.f;
    OpticVariant=bHolographic?Variant:FString();
    UpdateFoldingSights(0.f);
    if(LPVO&&bHolographic&&!LPVORing){
        auto* RingMesh=LoadObject<UStaticMesh>(nullptr,bUseQBZ191?*QBZ191Attachments::MeshPath(TEXT("lpvo_ring")):TEXT("/Game/Weapons/AttachmentFinish20260913/M4/Meshes/SM_LPVORing"));
        if(RingMesh){LPVORing=NewObject<UStaticMeshComponent>(this,TEXT("LPVOMagnificationRing"));LPVORing->SetStaticMesh(RingMesh);LPVORing->SetCollisionEnabled(ECollisionEnabled::NoCollision);LPVORing->SetCastShadow(false);LPVORing->SetupAttachment(HolographicOptic);LPVORing->RegisterComponent();LPVORing->SetRelativeLocation(FVector(-7.1f,0,4.f));}
    }
    if(LPVORing){LPVORing->SetVisibility(LPVO&&bHolographic);LPVORing->SetRelativeRotation(FRotator(0,0,(LPVOMagnification-1.f)*24.f));}
    if(HolographicOptic)HolographicOptic->SetVisibility(bHolographic);
    for(auto Head:FoldingSightHeads)Head->SetVisibility(bUsingM4Infima&&bInventoryWeaponReady);
}
FVector AFPSGAMECharacter::HolographicAimPoint() const
{
    return HolographicOptic?HolographicOptic->GetComponentTransform().TransformPosition(OpticLocalAimPoint()):FVector::ZeroVector;
}
FVector AFPSGAMECharacter::OpticLocalAimPoint() const
{
    if(AKMSoviet::Matches(AKMViewmodel)&&OpticVariant==TEXT("holographic"))return AKMAttachment::HoloPointCM;
    if(OpticVariant==TEXT("lpvo_1_6x"))return FVector(-12.15f,0,4.f);
    if(OpticVariant==TEXT("prism_scope_2x"))return FVector(-6.15f,0,4.f);
    return OpticVariant==TEXT("panoramic_red_dot")?FVector(2.125f,0,3.25f):FVector(-.653782f,0,5.175324f);
}
float AFPSGAMECharacter::EffectiveADSVerticalFOV() const
{
    return FMath::RadiansToDegrees(2.f*FMath::Atan(FMath::Tan(FMath::DegreesToRadians(ADSVerticalFieldOfView)*.5f)/GetOpticMagnification()));
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
    if(GetScopePresentationAlpha()>.5f)return bHolographicOptic&&WeaponADSFactor>.98f&&FVector::DotProduct(ComputeShotDirection(),FirstPersonCamera->GetForwardVector())>.99999f;
    return bHolographicOptic&&WeaponADSFactor>.98f&&FVector::DotProduct(ComputeShotDirection(),(HolographicAimPoint()-FirstPersonCamera->GetComponentLocation()).GetSafeNormal())>.99999f;
}
bool AFPSGAMECharacter::MeasureHolographicOrientation(float& ScreenRollDegrees,float& RailErrorDegrees) const
{
    ScreenRollDegrees=RailErrorDegrees=180.f;
    if(!bHolographicOptic||!HolographicOptic)return false;
    const FVector OpticUp=HolographicOptic->GetUpVector();
    const FVector RailUp=AKMViewmodel->GetSocketTransform(AKMSoviet::Matches(AKMViewmodel)?TEXT("WPN_root"):TEXT("WPN_RearSight")).GetRotation().RotateVector(FVector::UpVector);
    RailErrorDegrees=FMath::RadiansToDegrees(FMath::Acos(FMath::Clamp(FVector::DotProduct(OpticUp,RailUp),-1.0,1.0)));
    const auto* PC=Cast<APlayerController>(GetController());if(!PC)return false;
    FVector2D Center,Top;
    if(!PC->ProjectWorldLocationToScreen(HolographicAimPoint(),Center)||!PC->ProjectWorldLocationToScreen(HolographicAimPoint()+OpticUp*2.f,Top))return false;
    const FVector2D Delta=Top-Center;
    ScreenRollDegrees=FMath::RadiansToDegrees(FMath::Atan2(Delta.X,-Delta.Y));
    return true;
}

void AFPSGAMECharacter::SetLPVOMagnification(float Value)
{
    if(OpticVariant!=TEXT("lpvo_1_6x"))return;
    LPVOMagnification=FMath::Clamp(Value,1.f,6.f);
    if(LPVORing)LPVORing->SetRelativeRotation(FRotator(0,0,(LPVOMagnification-1.f)*24.f));
}
bool AFPSGAMECharacter::AdjustOpticMagnification(float Delta)
{
    if(OpticVariant!=TEXT("lpvo_1_6x")||!IsAiming())return false;
    SetLPVOMagnification(LPVOMagnification+Delta);return true;
}

float AFPSGAMECharacter::GetScopePresentationAlpha() const
{
    if(OpticVariant!=TEXT("lpvo_1_6x")||!bInventoryWeaponReady||IsTraversing()||IsWeaponBusy())return 0.f;
    return FMath::SmoothStep(.65f,.98f,CameraADSFactor);
}

void AFPSGAMECharacter::UpdateScopePresentation()
{
    // Owner-only hiding preserves attachment visibility and other world views.
    if(GetScopePresentationAlpha()>.5f){
        TArray<USceneComponent*> Parts;AKMViewmodel->GetChildrenComponents(true,Parts);Parts.Add(AKMViewmodel);
        for(auto* Part:Parts)if(auto* Primitive=Cast<UPrimitiveComponent>(Part);Primitive&&!Primitive->bOwnerNoSee){
            ScopeHiddenParts.Add(Primitive);Primitive->SetOwnerNoSee(true);
        }
    }else{
        for(const auto& Part:ScopeHiddenParts)if(Part.IsValid())Part->SetOwnerNoSee(false);
        ScopeHiddenParts.Reset();
    }
}
