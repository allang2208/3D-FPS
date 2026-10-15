#include "ProductionToolComponent.h"
#include "WarhammerInspectWalkCues.h"
#include "../FPSGAMECharacter.h"
#include "Animation/AnimSequence.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "Kismet/GameplayStatics.h"
#include "Sound/SoundBase.h"

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
        Character->IsCastBlockingLeftHandAction()||!Motions.FindRef(TEXT("InspectWalk"))||!IsWalkInspectStride())return;
    WalkInspectDelay-=Delta;
    if(WalkInspectDelay>0.f)return;
    if(!BeginInspect(true))WalkInspectDelay=FMath::FRandRange(1.f,2.f);
}

void UProductionToolComponent::PlayInspectCues(float From,float To) const
{
    // Walking inspect only: air whoosh plus steel ring/strike on the clip
    // clock. An interrupted inspect simply stops reaching later cues.
    if(InspectClip!=TEXT("InspectWalk"))return;
    for(const auto& Cue:WarhammerInspectWalkCues::Cues)
        if(From<Cue.Seconds&&Cue.Seconds<=To)
            if(auto* Sound=Cast<USoundBase>(FSoftObjectPath(Cue.Sound).ResolveObject()))
                UGameplayStatics::PlaySound2D(this,Sound,Cue.Volume,Cue.Pitch);
}
