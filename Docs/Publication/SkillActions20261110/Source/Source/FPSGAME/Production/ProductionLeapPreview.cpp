#include "ProductionToolComponent.h"
#include "../Skills/LeapStrikeMotion.h"
#include "../FPSGAMECharacter.h"
#include "../FPSGAMEPlayerController.h"
#include "../Multiplayer/ColdSteelAuthorityContext.h"
#include "../UI/ColdSteelStatusModel.h"
#include "../Monsters/MonsterCombatComponent.h"
#include "Components/CapsuleComponent.h"
#include "Components/DecalComponent.h"
#include "Engine/World.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/PhysicsVolume.h"
#include "Materials/MaterialInstanceDynamic.h"

bool UProductionToolComponent::LeapPreviewInputAvailable() const
{
    const auto* Pawn=Character.Get();
    const auto* PC=Pawn?Cast<APlayerController>(Pawn->GetController()):nullptr;
    return Pawn&&Pawn->IsLocallyControlled()&&PC&&!PC->bShowMouseCursor&&
        !AFPSGAMEPlayerController::BlocksOngoingActions(PC)&&IsEquipped()&&CanUse()&&
        !Pawn->bIsCrouched&&Pawn->GetCharacterMovement()->IsMovingOnGround()&&
        !IsBusy()&&!Pawn->IsWeaponBusy(true);
}

void UProductionToolComponent::SetLeapAimPreview(bool Active)
{
    if(!Active)
    {
        bLeapAimPreview=bLeapPreviewValid=bLeapPreviewPathClear=false;
        if(LeapAimDecal)LeapAimDecal->SetHiddenInGame(true);
        return;
    }
    if(bLeapAimPreview||!LeapStrikeStatusText(false).IsEmpty()||!LeapPreviewInputAvailable())return;
    bLeapAimPreview=true;LeapPreviewPathAge=LeapStrike::PreviewPathInterval;LeapNoticeUntil=0.;
    RefreshLeapAimPreview(0.f);
}

FVector UProductionToolComponent::LeapImpactForFloor(const FVector& Floor,const FVector& Direction,FVector& Normal) const
{
    const FVector Point=Floor+Direction.GetSafeNormal2D()*WarhammerHeavy::LandingForward;
    FCollisionQueryParams Query(SCENE_QUERY_STAT(LeapPreviewImpact),false,Character.Get());
    for(int32 Pass=0;Pass<12;++Pass)
    {
        FHitResult Hit;
        if(!GetWorld()->LineTraceSingleByChannel(Hit,Point+FVector(0,0,80),Point-FVector(0,0,100),ECC_Visibility,Query))break;
        auto* Actor=Hit.GetActor();
        if(Actor&&(Actor->IsA<APawn>()||Actor->FindComponentByClass<UMonsterCombatComponent>()))
        {Query.AddIgnoredActor(Actor);continue;}
        const auto* Pawn=Character.Get();
        if(!Pawn||!Pawn->GetCharacterMovement()->IsWalkable(Hit))break;
        // The hammer's forward offset cannot put the impact through a wall or
        // onto a remote lower storey. Keep the contact on the reachable floor.
        const auto* Capsule=Pawn->GetCapsuleComponent();
        const float Half=Capsule->GetScaledCapsuleHalfHeight(),Radius=Capsule->GetScaledCapsuleRadius();
        const auto Shape=FCollisionShape::MakeCapsule(FMath::Max(1.f,Radius-1.f),FMath::Max(Radius,Half-1.f));
        FCollisionResponseParams Responses(Capsule->GetCollisionResponseToChannels());
        Responses.CollisionResponse.SetResponse(ECC_Pawn,ECR_Ignore);
        FHitResult Barrier;
        if(FMath::Abs(Hit.ImpactPoint.Z-Floor.Z)>WarhammerHeavy::LandingForward||
            GetWorld()->SweepSingleByChannel(Barrier,
                Floor+FVector(0,0,LeapStrike::StandingHeight(Half,Radius,Normal)),
                Hit.ImpactPoint+FVector(0,0,LeapStrike::StandingHeight(Half,Radius,Hit.ImpactNormal)),
                FQuat::Identity,Capsule->GetCollisionObjectType(),Shape,Query,Responses))break;
        Normal=Hit.ImpactNormal;return Hit.ImpactPoint;
    }
    return Floor;
}

bool UProductionToolComponent::IsLeapPathClear(const FVector& Target) const
{
    const auto* Pawn=Character.Get();if(!Pawn||Target.ContainsNaN())return false;
    const auto* Capsule=Pawn->GetCapsuleComponent();
    const auto* Move=Pawn->GetCharacterMovement();
    LeapStrike::FTrajectory Path;
    if(!LeapStrike::SolveTrajectory(Pawn->GetActorLocation(),Target,Move->GetGravityZ(),Move->GetPhysicsVolume()->TerminalVelocity,Path))return false;
    const float Half=Capsule->GetScaledCapsuleHalfHeight(),Radius=Capsule->GetScaledCapsuleRadius();
    const auto Shape=FCollisionShape::MakeCapsule(FMath::Max(1.f,Radius-1.f),FMath::Max(Radius,Half-1.f));
    FCollisionQueryParams Query(SCENE_QUERY_STAT(LeapPreviewArc),false,Pawn);
    FCollisionResponseParams Responses(Capsule->GetCollisionResponseToChannels());
    Responses.CollisionResponse.SetResponse(ECC_Pawn,ECR_Ignore);
    if(GetWorld()->OverlapBlockingTestByChannel(Target,FQuat::Identity,Capsule->GetCollisionObjectType(),Shape,Query,Responses))return false;
    const FVector Start=Pawn->GetActorLocation();FVector Previous=Start;
    // Longer falls get bounded extra samples; the high-drop preview runs at a
    // lower cadence below. Preview never advances movement or seeks a new target.
    const int32 Steps=FMath::Clamp(FMath::CeilToInt(Path.Duration/.025f),48,256);
    for(int32 I=1;I<=Steps;++I)
    {
        const FVector Next=Path.Position(Start,Path.Duration*float(I)/Steps);FHitResult Hit;
        if(GetWorld()->SweepSingleByChannel(Hit,Previous,Next,FQuat::Identity,Capsule->GetCollisionObjectType(),Shape,Query,Responses))return false;
        Previous=Next;
    }
    return true;
}

bool UProductionToolComponent::ValidateLeapLanding(const FVector& Requested,FVector& Target,FVector& Floor,FVector& Normal) const
{
    const auto* Pawn=Character.Get();if(!Pawn||Requested.ContainsNaN())return false;
    const auto* Model=ColdSteelAuthority::ForPawn(Pawn);if(!Model)return false;
    const FVector Start=Pawn->GetActorLocation();const auto* Capsule=Pawn->GetCapsuleComponent();
    const float Half=Capsule->GetScaledCapsuleHalfHeight(),Radius=Capsule->GetScaledCapsuleRadius();
    // Centimetre RPC quantization can move an endpoint slightly; never re-aim or shorten it.
    if(FVector::DistSquared2D(Start,Requested)>FMath::Square(Model->LeapStrikeBaseStats().ReachCM+2.f)||
        FVector::DistSquared2D(Start,Requested)<FMath::Square(78.f))return false;
    FCollisionQueryParams Query(SCENE_QUERY_STAT(LeapCommittedGround),false,Pawn);
    const FVector Feet=Requested-FVector(0,0,Half+LeapStrike::FloorClearance);
    for(int32 Pass=0;Pass<12;++Pass)
    {
        FHitResult Hit;
        if(!GetWorld()->LineTraceSingleByChannel(Hit,Feet+FVector(0,0,6),Feet-FVector(0,0,Radius+6.f),ECC_Visibility,Query))return false;
        auto* Actor=Hit.GetActor();
        if(Actor&&(Actor->IsA<APawn>()||Actor->FindComponentByClass<UMonsterCombatComponent>()))
        {Query.AddIgnoredActor(Actor);continue;}
        if(!Pawn->GetCharacterMovement()->IsWalkable(Hit))return false;
        Floor=Hit.ImpactPoint;Normal=Hit.ImpactNormal;
        if(!IsLeapFloorHeightAllowed(float(Floor.Z)))return false;
        Target=Floor+FVector(0,0,LeapStrike::StandingHeight(Half,Radius,Normal));
        if(FVector::DistSquared(Target,Requested)>FMath::Square(4.f))return false;
        return IsLeapPathClear(Target);
    }
    return false;
}

void UProductionToolComponent::RefreshLeapAimPreview(float Delta)
{
    if(!bLeapAimPreview)return;
    if(!LeapPreviewInputAvailable()){SetLeapAimPreview(false);return;}
    LeapPreviewPathAge+=Delta;
    LeapPreviewDirection=Character->GetMeleeAimTransform().GetUnitAxis(EAxis::X);
    FVector Floor,Normal;
    const bool Ground=SolveLeapTarget(LeapPreviewDirection,LeapPreviewTarget,Floor,Normal,false,false);
    const float PathInterval=Ground&&FMath::Abs(LeapPreviewTarget.Z-Character->GetActorLocation().Z)>500.f?.15f:LeapStrike::PreviewPathInterval;
    // The visual follows the camera every frame; long flight queries run at
    // most 6.7 Hz with one candidate and no catch-up loop.
    if(Ground&&LeapPreviewPathAge>=PathInterval)
    {LeapPreviewPathAge=0.f;bLeapPreviewPathClear=IsLeapPathClear(LeapPreviewTarget);}
    bLeapPreviewValid=Ground&&bLeapPreviewPathClear&&LeapAimMaterial;
    if(!bLeapPreviewValid){if(LeapAimDecal)LeapAimDecal->SetHiddenInGame(true);return;}
    const auto* Model=ColdSteelAuthority::ForPawn(Character.Get());if(!Model)return;
    const float Radius=Model->LeapStrikeBaseStats().RadiusCM;
    if(!LeapAimDecal)
    {
        LeapAimDecal=NewObject<UDecalComponent>(GetOwner(),TEXT("LeapStrikeAimCircle"));
        GetOwner()->AddInstanceComponent(LeapAimDecal);
        LeapAimDecal->SetDecalMaterial(LeapAimMaterial);
        LeapAimDecal->RegisterComponent();LeapAimDecal->SetFadeScreenSize(0.f);
        LeapAimMID=LeapAimDecal->CreateDynamicMaterialInstance();
        if(LeapAimMID)
        {
            LeapAimMID->SetScalarParameterValue(TEXT("FieldRadius"),0.f);
        }
    }
    if(!FMath::IsNearlyEqual(LeapPreviewRadius,Radius))
    {
        LeapPreviewRadius=Radius;LeapAimDecal->DecalSize=FVector(104,Radius+16,Radius+16);
        if(LeapAimMID)LeapAimMID->SetScalarParameterValue(TEXT("ImpactRadius"),Radius);
    }
    const FVector Point=LeapImpactForFloor(Floor,LeapPreviewDirection,Normal);
    const FVector Location=Point+Normal*4.f;const FRotator Rotation=FRotationMatrix::MakeFromX(-Normal).Rotator();
    if(!LeapAimDecal->GetComponentLocation().Equals(Location,.001f)||!LeapAimDecal->GetComponentRotation().Equals(Rotation,.001f))
    {
        LeapAimDecal->SetWorldLocationAndRotation(Location,Rotation);
        if(LeapAimMID)
        {
            LeapAimMID->SetVectorParameterValue(TEXT("Center"),FLinearColor(Point));
            LeapAimMID->SetVectorParameterValue(TEXT("SurfaceNormal"),FLinearColor(Normal));
        }
    }
    if(LeapAimDecal->bHiddenInGame)LeapAimDecal->SetHiddenInGame(false);
}

void UProductionToolComponent::ReleaseLeapAimPreview()
{
    if(!bLeapAimPreview)return;
    const bool Ready=bLeapPreviewValid&&LeapPreviewInputAvailable();
    const FVector Requested=LeapPreviewTarget,Direction=LeapPreviewDirection;
    SetLeapAimPreview(false);
    if(!Ready)return;
    FVector Target,Floor,Normal;
    // Recheck the last displayed landing. Do not trace the new cursor position
    // on key release or silently choose another endpoint behind an obstacle.
    if(!LeapStrikeStatusText(false).IsEmpty())return;
    if(!ValidateLeapLanding(Requested,Target,Floor,Normal)){LeapNoticeUntil=GetWorld()->GetTimeSeconds()+2.;return;}
    CommitLeapStrike(Target,Floor,Normal,Direction);
}

bool UProductionToolComponent::ClampLeapStrikeView(FRotator& View)
{
    if(!bLeapAirborne)return false;
    // A blocked leap can finish its attack and switch to ordinary falling.
    // The view lock belongs to that airborne interval, not to the attack flag.
    if(!IsLeapControlImmune())
    {SetLeapAirborne(false);return false;}
    View.Yaw=LeapLookCenter.Yaw+FMath::Clamp(FMath::FindDeltaAngleDegrees(LeapLookCenter.Yaw,View.Yaw),-double(LeapStrike::AimYawLimit),double(LeapStrike::AimYawLimit));
    View.Pitch=FMath::Clamp(LeapLookCenter.Pitch+FMath::Clamp(FMath::FindDeltaAngleDegrees(LeapLookCenter.Pitch,View.Pitch),
        -double(LeapStrike::AimPitchLimit),double(LeapStrike::AimPitchLimit)),-85.,85.);
    return true;
}
