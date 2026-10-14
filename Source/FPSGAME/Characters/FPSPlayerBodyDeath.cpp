#include "FPSPlayerBodyComponent.h"
#include "../FPSGAMECharacter.h"
#include "Camera/CameraComponent.h"
#include "Camera/CameraTypes.h"
#include "Camera/PlayerCameraManager.h"
#include "Components/SkeletalMeshComponent.h"
#include "Dom/JsonObject.h"
#include "Engine/World.h"
#include "GameFramework/PlayerController.h"

void UFPSPlayerBodyComponent::InitializeDeathPresentation()
{
    const TSharedPtr<FJsonObject>* Settings=nullptr;
    if(!Configuration->TryGetObjectField(TEXT("death_presentation"),Settings))return;
    for(int32 Variant=0;Variant<2;++Variant)
    {
        const TArray<TSharedPtr<FJsonValue>>* Keys=nullptr;
        if(!(*Settings)->TryGetArrayField(Variant?TEXT("crouched_camera"):TEXT("standing_camera"),Keys))continue;
        for(const auto& Value:*Keys)
        {
            const auto& Row=Value->AsArray();
            if(Row.Num()!=6)continue;
            auto& Key=DeathCameraTracks[Variant].AddDefaulted_GetRef();
            Key.Eye=FVector(Row[0]->AsNumber(),Row[1]->AsNumber(),Row[2]->AsNumber());
            Key.Rotation=FRotator(Row[3]->AsNumber(),Row[4]->AsNumber(),Row[5]->AsNumber());
        }
    }
}

bool UFPSPlayerBodyComponent::ApplyDeathCameraView(FMinimalViewInfo& View)
{
    if(!Character.IsValid()||!Character->IsLocallyControlled()||!IsDeathViewActive())return false;
    const bool Crouched=DisplayState.ActionVariant==TEXT("Crouched");
    const auto& Keys=DeathCameraTracks[Crouched?1:0];
    if(Keys.Num()<2)return false;
    const float Age=FMath::Max(0.f,ServerClock()-DisplayState.ActionStartedAt);
    if(!bDeathCameraStarted)
    {
        bDeathCameraStarted=true;
        DeathInitialLocation=View.Location;DeathInitialRotation=View.Rotation;DeathInitialFOV=View.FOV;
        if(const auto* PC=Cast<APlayerController>(Character->GetController());PC&&PC->PlayerCameraManager)
        {
            DeathCameraManager=PC->PlayerCameraManager;
            // Cache the last rendered view, including an ADS or third-person
            // camera. No animation evaluation or scene capture is needed here.
            DeathInitialLocation=PC->PlayerCameraManager->GetCameraLocation();
            DeathInitialRotation=PC->PlayerCameraManager->GetCameraRotation();
            PC->PlayerCameraManager->StopAllCameraShakes(true);
        }
        DeathLastCameraLocation=DeathInitialLocation;
        if(const auto* Body=GetBodyMesh())DeathMeshFrame=Body->GetComponentTransform();
        else DeathMeshFrame=FTransform(FRotator(0,Character->GetActorRotation().Yaw-90.f,0),Character->GetActorLocation()-FVector(0,0,88));
        UpdateOwnerVisibility();
    }
    const float Phase=FMath::Clamp(Age/FPSPlayerDeathMotion::FallSeconds(Crouched),0.f,1.f);
    const float Frame=Phase*(Keys.Num()-1);
    const int32 Index=FMath::Min(FMath::FloorToInt(Frame),Keys.Num()-2);
    const float Alpha=Frame-Index;
    const FVector Eye=DeathMeshFrame.TransformPosition(FMath::Lerp(Keys[Index].Eye,Keys[Index+1].Eye,Alpha));
    const FRotator Turn=FMath::Lerp(Keys[Index].Rotation,Keys[Index+1].Rotation,Alpha);
    const float Entry=FMath::SmoothStep(0.f,.22f,Age);
    FVector Desired=Eye;
    if(IsThirdPersonViewEnabled())
    {
        const FVector Back=FRotator(0,DeathInitialRotation.Yaw,0).Vector();
        Desired=Eye-Back*270.f+FVector(0,0,100.f);
        View.Rotation=FMath::Lerp(DeathInitialRotation,(Eye+FVector(0,0,20.f)-Desired).Rotation(),Entry);
    }
    else
    {
        // Position follows the exact authored head path. Rotation is authored
        // separately with bounded roll/pitch, rather than strapping the eye to
        // every head-bone twitch or turning the view upside down on impact.
        View.Rotation=FRotator(FMath::Lerp(DeathInitialRotation.Pitch,Turn.Pitch,Entry),
            DeathInitialRotation.Yaw+Turn.Yaw*Entry,FMath::Lerp(DeathInitialRotation.Roll,Turn.Roll,Entry));
    }
    Desired=FMath::Lerp(DeathInitialLocation,Desired,Entry);
    FCollisionQueryParams Query(SCENE_QUERY_STAT(PlayerDeathCamera),false,GetOwner());
    FHitResult Floor;
    if(GetWorld()->LineTraceSingleByChannel(Floor,Desired+FVector(0,0,35.f),Desired-FVector(0,0,65.f),ECC_Camera,Query)
        &&Floor.ImpactNormal.Z>.3f)
        Desired.Z=FMath::Max(Desired.Z,Floor.ImpactPoint.Z+14.f);
    FHitResult Hit;
    if(GetWorld()->SweepSingleByChannel(Hit,DeathLastCameraLocation,Desired,FQuat::Identity,ECC_Camera,FCollisionShape::MakeSphere(8.f),Query))
        Desired=Hit.bStartPenetrating?DeathLastCameraLocation:Hit.Location+Hit.ImpactNormal*1.f;
    View.Location=DeathLastCameraLocation=Desired;
    View.FOV=FMath::Lerp(DeathInitialFOV,Character->BaseLookHorizontalFOV(),Entry);
    View.bUseFirstPersonParameters=false;
    if(DeathCameraManager.IsValid())DeathCameraManager->SetManualCameraFade(
        FMath::SmoothStep(FPSPlayerDeathMotion::FadeStart,FPSPlayerDeathMotion::FadeEnd,Age),FLinearColor::Black,false);
    return true;
}

void UFPSPlayerBodyComponent::ReleaseDeathCamera()
{
    // The old pawn is destroyed at respawn; the camera manager survives it.
    // Release only the fade owned by this death so the new pawn is not black.
    if(bDeathCameraStarted&&DeathCameraManager.IsValid())
        DeathCameraManager->StartCameraFade(DeathCameraManager->FadeAmount,0.f,.2f,FLinearColor::Black,false,false);
    DeathCameraManager.Reset();bDeathCameraStarted=false;
}
