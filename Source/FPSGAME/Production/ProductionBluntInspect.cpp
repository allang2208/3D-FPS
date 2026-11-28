#include "ProductionToolComponent.h"
#include "WarhammerInspectWalkCues.h"
#include "../FPSGAMECharacter.h"
#include "../WorldGeneration/VillageOilCarry.h"
#include "Animation/AnimSequence.h"
#include "GameFramework/CharacterMovementComponent.h"

bool UProductionToolComponent::ShouldBreakInspect() const
{
    const auto* Pawn=Character.Get();
    return !Pawn||IsBusy()||Pawn->IsSprinting()||Pawn->bWeaponJumpAirborne||Pawn->IsSliding()||
        Pawn->IsDodging()||Pawn->IsTraversing()||Pawn->IsCastBlockingLeftHandAction();
}

bool UProductionToolComponent::BeginInspect(bool bWalking)
{
    // Cosmetic two-hand inspect: one full turn about the shaft centreline. L
    // plays InspectV1; walking plays only its accelerated turn half (InspectWalkSpeedV3).
    // Walking keeps it; it never occupies IsBusy or the hit clock.
    const FName Clip=bWalking?FName(TEXT("InspectWalk")):FName(TEXT("Inspect"));
    if(!IsWarhammerEquipped()||!CanUse()||!HasReadyPresentation()||!Motions.FindRef(Clip)||ShouldBreakInspect())
        return false;
    InspectAir.Stop();
    InspectClip=Clip;InspectElapsed=0.f;
    ScheduleWalkInspect(true);
    return true;
}

void UProductionToolComponent::ScheduleWalkInspect(bool bAfterInspect)
{
    // Same cadence as the two-handed sword's walking inspect.
    WalkInspectDelay=bAfterInspect?FMath::FRandRange(5.f,8.f):FMath::FRandRange(2.f,3.5f);
}

bool UProductionToolComponent::IsWalkInspectStride() const
{
    const auto* Pawn=Character.Get();
    const auto* Movement=Pawn?Pawn->GetCharacterMovement():nullptr;
    return Movement&&Movement->IsMovingOnGround()&&!Pawn->bWeaponJumpAirborne&&!Pawn->IsSliding()&&
        !Pawn->IsDodging()&&!Pawn->IsTraversing()&&!Pawn->IsSprinting()&&Pawn->GetVelocity().SizeSquared2D()>400.f;
}

void UProductionToolComponent::TickWalkInspect(float Delta)
{
    // Counts down only during an ordinary ground stride, never over an action
    // or the sprint-carry handoff.
    if(InspectElapsed>=0.f||!IsWarhammerEquipped()||!CanUse()||IsBusy()||SprintBlend>.001f||!Character.IsValid()||
        Character->IsCastBlockingLeftHandAction()||UVillageOilCarry::IsBlockingWeaponActions(Character.Get())||
        !Motions.FindRef(TEXT("InspectWalk"))||!IsWalkInspectStride())return;
    WalkInspectDelay-=Delta;
    if(WalkInspectDelay>0.f)return;
    if(!BeginInspect(true))WalkInspectDelay=FMath::FRandRange(1.f,2.f);
}

void UProductionToolComponent::CancelInspect()
{
    InspectElapsed=-1.f;
    InspectAir.Stop();
}

void UProductionToolComponent::PlayInspectCues(float From,float To,float Rate)
{
    namespace Cues=WarhammerInspectCues;
    if(InspectClip==TEXT("InspectWalk"))
    {
        InspectAir.PlayBeat(this,From,To,Cues::WalkTurnPeak,.53f,Rate);
        return;
    }
    InspectAir.PlayBeat(this,From,To,Cues::RockPeak,.29f,Rate);
    InspectAir.PlayBeat(this,From,To,Cues::TurnPeak,.59f,Rate);
}
