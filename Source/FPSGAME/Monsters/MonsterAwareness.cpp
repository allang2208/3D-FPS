#include "MonsterAIController.h"
#include "MonsterCombatComponent.h"
#include "FPSCombatHealthComponent.h"
#include "BlindSupplicantMonster.h"
#include "LurkerM08Monster.h"
#include "HangingBellM09.h"
#include "MantisM27Monster.h"
#include "BellowSacLobber.h"
#include "Perception/AIPerceptionComponent.h"
#include "Perception/AISense.h"
#include "Perception/AISense_Sight.h"
#include "Perception/AISense_Hearing.h"
#include "Perception/AISenseConfig_Sight.h"
#include "Perception/AISenseConfig_Hearing.h"
#include "Engine/World.h"
#include "Engine/OverlapResult.h"
#include "CoreGlobals.h"

namespace
{
bool LivingPlayer(const APawn* Player)
{
    if (!IsValid(Player) || !Player->IsPlayerControlled()) return false;
    const auto* Health = Player->FindComponentByClass<UFPSCombatHealthComponent>();
    return !Health || !Health->IsDead();
}
bool TakeGroupAlertBudget()
{
    static uint64 Frame = MAX_uint64;
    static uint8 Count = 0;
    if (Frame != GFrameCounter) { Frame = GFrameCounter; Count = 0; }
    if (Count >= 2) return false;
    ++Count;
    return true;
}
}

bool AMonsterAIController::CanSeePlayer(APawn* Player, bool RequireFacing) const
{
    const auto* C = Combat();
    if (!GetPawn() || !C || C->AggroRange() <= 0.f || !LivingPlayer(Player)) return false;
    const auto* Sight = Senses->GetSenseConfig<UAISenseConfig_Sight>();
    const float Range = RequireFacing || !Sight ? C->AggroRange() : FMath::Max(C->AggroRange(), Sight->LoseSightRadius);
    const FVector Delta = Player->GetActorLocation() - GetPawn()->GetActorLocation();
    // Actual 3D range prevents a different floor from counting as zero distance.
    if (Delta.SizeSquared() > FMath::Square(Range)) return false;
    if (RequireFacing && Sight && Sight->PeripheralVisionAngleDegrees < 180.f)
    {
        const float Cone = FMath::Cos(FMath::DegreesToRadians(Sight->PeripheralVisionAngleDegrees));
        if (FVector::DotProduct(GetPawn()->GetActorForwardVector().GetSafeNormal2D(), Delta.GetSafeNormal2D()) < Cone) return false;
    }
    if (const auto* M27 = Cast<AMantisM27Monster>(GetPawn())) return M27->HasAttackSight(Player);
    if (const auto* M08 = Cast<ALurkerM08Monster>(GetPawn())) return M08->HasHuntingSight(Player);
    if (const auto* M09 = Cast<AHangingBellM09>(GetPawn())) return M09->HasAttackSight(Player);
    if (const auto* M07 = Cast<ABlindSupplicantMonster>(GetPawn())) return M07->HasMagicSight(Player);
    return LineOfSightTo(Player);
}

void AMonsterAIController::DiscoverPlayer(APawn* Player, bool Broadcast)
{
    const auto* C = Combat();
    if (!HasAuthority() || !bDecisionEnabled || !GetPawn() || !GetPawn()->IsActorTickEnabled()
        || !C || C->IsDead() || C->AggroRange() <= 0.f || !LivingPlayer(Player)) return;
    const bool AlreadyConfirmed = bConfirmedTarget && KnownTarget.Get() == Player;
    KnownTarget = Player; LastKnown = Player->GetNavAgentLocation();
    LastEvidence = GetWorld()->GetTimeSeconds(); EvidenceLifetime = MemorySeconds;
    bConfirmedTarget = true; bReturning = false;
    PendingDamageTarget.Reset(); PassiveDiscoveryAt = -1.f;
    if (!Broadcast) bPendingGroupAlert = false;
    else if (!AlreadyConfirmed) bPendingGroupAlert = true;
    if (!AlreadyConfirmed)
        if (auto* Bellow=Cast<ABellowSacLobber>(GetPawn())) Bellow->NotifyDiscovery(Broadcast);
}

void AMonsterAIController::Perceived(AActor* Actor, FAIStimulus Stimulus)
{
    auto* Player = Cast<APawn>(Actor);
    const auto* C = Combat();
    if (!HasAuthority() || !bDecisionEnabled || !GetPawn() || !GetPawn()->IsActorTickEnabled()
        || !LivingPlayer(Player) || !C || C->IsDead() || C->AggroRange() <= 0.f || !Stimulus.WasSuccessfullySensed()) return;
    // Once engaged, an unrelated stimulus must not oscillate the target.
    if (bConfirmedTarget && KnownTarget.IsValid() && KnownTarget.Get() != Player) return;
    if (Stimulus.Type == UAISense::GetSenseID<UAISense_Sight>())
    {
        // An unaware monster already reacting to a hit must finish that
        // deadline; a cached sight event must not cancel it in the same frame.
        if (!PendingDamageTarget.IsValid() && CanSeePlayer(Player, !bConfirmedTarget)) DiscoverPlayer(Player, true);
    }
    else if (Stimulus.Type == UAISense::GetSenseID<UAISense_Hearing>() && !PendingDamageTarget.IsValid())
    {
        const auto* Bellow = Cast<ABellowSacLobber>(GetPawn());
        const bool Sensitive = Bellow && Bellow->bSoundSensitive;
        const bool Suppressed = Stimulus.Tag == TEXT("GunshotSuppressed");
        const bool Gunshot = Suppressed || Stimulus.Tag == TEXT("Gunshot");
        if (bConfirmedTarget && !(Sensitive && Gunshot)) return;
        const auto* Hearing = Senses->GetSenseConfig<UAISenseConfig_Hearing>();
        const FVector From = GetPawn()->GetPawnViewLocation();
        const float DistanceSq = FVector::DistSquared(From, Stimulus.StimulusLocation);
        // The single gunshot event reaches sensitive ears farther away, while
        // ordinary monsters retain their previous 18 m / suppressed 5 m limits.
        if (Gunshot && DistanceSq > FMath::Square(Sensitive ?
            (Suppressed ? FMath::Min(1000.f, Bellow->HearingRadius) : Bellow->HearingRadius) :
            (Suppressed ? 500.f : 1800.f))) return;
        FCollisionQueryParams Query(SCENE_QUERY_STAT(MonsterNoise), false, GetPawn());
        Query.AddIgnoredActor(Player);
        FHitResult Hit;
        const bool Occluded = GetWorld()->LineTraceSingleByChannel(Hit, From, Stimulus.StimulusLocation, ECC_Visibility, Query);
        if (Occluded && DistanceSq > FMath::Square((Hearing ? Hearing->HearingRange : 1800.f) * (Sensitive ? .65f : .35f))) return;
        // Sensitive gunshot discovery shares the visual/group-warning path.
        // A pending 1-2 second hit-reaction deadline still takes precedence.
        if (Sensitive && Gunshot) DiscoverPlayer(Player, true);
        else
        {
            KnownTarget = Player; LastKnown = Stimulus.StimulusLocation;
            if (Gunshot) LastKnown.Z -= Player->GetActorLocation().Z - Player->GetNavAgentLocation().Z;
            LastEvidence = GetWorld()->GetTimeSeconds(); EvidenceLifetime = 6.f;
        }
    }
    UpdateKnowledge();
}

void AMonsterAIController::RememberDamage(APawn* Player)
{
    const auto* C = Combat();
    if (!HasAuthority() || !bDecisionEnabled || !GetPawn() || !GetPawn()->IsActorTickEnabled()
        || !LivingPlayer(Player) || !C || C->IsDead() || C->AggroRange() <= 0.f) return;
    if (bConfirmedTarget && KnownTarget.IsValid())
    {
        // Further hits during combat do not re-enter the passive reaction phase.
        if (KnownTarget.Get() == Player) { LastEvidence = GetWorld()->GetTimeSeconds(); EvidenceLifetime = MemorySeconds; }
        return;
    }
    if (!PendingDamageTarget.IsValid())
    {
        PendingDamageTarget = Player;
        KnownTarget.Reset(); bReturning = false;
        const float MinDelay = FMath::Max(0.f, PassiveDiscoveryDelayMin);
        const float MaxDelay = FMath::Max(MinDelay, PassiveDiscoveryDelayMax);
        PassiveDiscoveryAt = GetWorld()->GetTimeSeconds() + WanderRandom.FRandRange(MinDelay, MaxDelay);
        UpdateKnowledge();
    }
    // Repeated hits keep the first deadline. Hit/stagger animation and death
    // retain their existing immediate response independently of aggro timing.
}

void AMonsterAIController::ConsumePassiveDiscovery()
{
    if (PassiveDiscoveryAt < 0.f) return;
    if (!LivingPlayer(PendingDamageTarget.Get())) { PendingDamageTarget.Reset(); PassiveDiscoveryAt = -1.f; return; }
    if (GetWorld()->GetTimeSeconds() < PassiveDiscoveryAt) return;
    APawn* Player = PendingDamageTarget.Get();
    PendingDamageTarget.Reset(); PassiveDiscoveryAt = -1.f;
    DiscoverPlayer(Player, true);
}

void AMonsterAIController::BroadcastGroupAlert()
{
    const float Now = GetWorld()->GetTimeSeconds();
    if (!bPendingGroupAlert || !LivingPlayer(KnownTarget.Get()) || Now < NextBroadcast) return;
    if (GroupAlertRadius <= 0.f) { bPendingGroupAlert = false; return; }
    if (!TakeGroupAlertBudget()) return;
    bPendingGroupAlert = false;
    NextBroadcast = Now + FMath::Max(1.f, GroupAlertCooldown);
    const FVector Center = GetPawn()->GetActorLocation();
    APawn* Player = KnownTarget.Get();
    TArray<FOverlapResult> Hits;
    FCollisionQueryParams Query(SCENE_QUERY_STAT(MonsterGroupAlert), false, GetPawn());
    GetWorld()->OverlapMultiByObjectType(Hits, Center, FQuat::Identity, FCollisionObjectQueryParams(ECC_Pawn),
        FCollisionShape::MakeSphere(GroupAlertRadius), Query);
    TSet<AMonsterAIController*> Recipients;
    for (const auto& Hit : Hits)
    {
        const auto* NearbyPawn = Cast<APawn>(Hit.GetActor());
        auto* Ally = NearbyPawn ? Cast<AMonsterAIController>(NearbyPawn->GetController()) : nullptr;
        if (!Ally || Ally == this || Recipients.Contains(Ally)) continue;
        Recipients.Add(Ally);
        if (FVector::DistSquared(Center, NearbyPawn->GetActorLocation()) > FMath::Square(GroupAlertRadius)
            || Ally->EncounterArea != EncounterArea) continue;
        const auto* AllyCombat = Ally->Combat();
        if (!AllyCombat || AllyCombat->IsDead() || !Ally->bDecisionEnabled || !NearbyPawn->IsActorTickEnabled()) continue;
        if (Ally->bConfirmedTarget && LivingPlayer(Ally->KnownTarget.Get())) continue;
        // Exactly one hop from the triggering monster, including upper/lower
        // floors in this sphere. No recursive broadcast, no wall-ray per ally.
        Ally->DiscoverPlayer(Player, false);
        Ally->UpdateKnowledge();
    }
}
